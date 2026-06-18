#!/usr/bin/env python3
"""
WCdecider Temporal Graph Neural Network (TGN-like) for 1X2 (replicable numpy-only)
=================================================================================

Pure numpy + stdlib (csv, math, datetime, pathlib). No torch/pandas/scipy.

Purpose (AGENT.md aligned):
- Chronological walk over wc_backtest_historical_dataset.csv (N=222, already sorted).
- Per-team embedding vectors (dim hyperparam, default 8).
- For each match in time order:
    * Graph message = time-decayed (exp(-days/180)) * result_strength weighted mean of
      recent opponents' *pre-interaction* embedding snapshots.
    * 1-layer 'graph conv' approx: mean_agg @ W_msg + b , tanh.
    * Temporal GRU-like gated update (numpy sigmoid/tanh) of own emb.
- Variations: temporal_only=True (no opponent messages, minimal self-gating) vs full_graph.
- After full sequential pass (using *pre*-match embs for features), train small 3-layer
  FF head (input(2d+1) -> h1 relu -> h2 relu -> 3 logits -> softmax) with manual GD.
- Head input: (embA - embB, |embA-embB|, elo_diff_proxy= (elo_a-elo_b)/400 ).
- Deterministic: seed=42 everywhere, np.random.default_rng(42).
- Train returns brier/acc on chrono splits (70/15/15).
- predict_proba returns renormalized (pA, pD, pB) using frozen post-history embs + head.
- Save/Load: np.savez to training/tgnn_{variant}.npz  (variant = d{dim}_{t|fg}).

Replicability notes (per AGENT.md §14 Rule 25, FUTURE_UPDATE_PROTOCOL, wc_replicable_pipeline.py):
- All processing is a single forward chronological pass (no future leakage into pre-match features).
- Pre-match embeddings used for every historical label (transductive graph memory style).
- Fixed seed + pure numpy ops => bit-identical runs given same CSV.
- Head GD is *not* backprop-through-time on temporal params; gate/W_msg are seeded fixed
  during the walk (temporal/graph acts as deterministic featurizer). Only FF head is GD-trained.
- Can be used as an additional weak learner in wc_replicable_pipeline.py ensemble
  (weights per Rule 24/27 discipline: trap count must stay 0).
- Intended as experimental degree-6/7 component; production still anchored on
  v4.1 elo + market stack (see wc_model_v4_1_ensemble.py, wc_replicable_pipeline.py).

Usage (standalone replicable):
    python3 wc_temporal_graph_nn.py

Integration for p_win (callable style matching other wc_*_1x2):
    from wc_temporal_graph_nn import TemporalGraphNN, tgnn_predict_1x2
    tgnn = TemporalGraphNN(emb_dim=8, temporal_only=False, seed=42)
    # one-time (or load pre-saved):
    # metrics = tgnn.train()
    tgnn.load("training/tgnn_d8_fg.npz")
    pA, pD, pB = tgnn_predict_1x2("BRA", "ARG", elo_a=2050.0, elo_b=1980.0, model=tgnn)
    # then e.g. blend in replicable stack (respect Rule 27 for any weight change):
    # p_ens = (0.8 * p_v4, ...) renormalize

Train script snippet (for backtest harness integration):
    from wc_temporal_graph_nn import TemporalGraphNN
    from wc_backtest_framework import get_all_matches, brier_score_1x2
    model = TemporalGraphNN(emb_dim=8)
    mets = model.train()  # builds embs + trains head on full CSV
    print(mets)
    # For per-row in backtest:
    # p_tgnn = model.predict_proba(m.team_a, m.team_b, m.elo_a, m.elo_b)
    # bs = brier_score_1x2(p_tgnn, m.outcome)
    model.save()  # training/tgnn_d8_fg.npz
"""

from __future__ import annotations

import csv
import math
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np


def _parse_date(d: str) -> datetime:
    """AGENT-reproducible date parser (matches wc_backtest_historical_loader.py)."""
    return datetime.strptime(d, "%d/%m/%Y")


def _outcome_to_strength(outcome: str, is_a: bool) -> float:
    """Result strength scalar for graph messages / updates."""
    if outcome == "D":
        return 0.5
    if (outcome == "A" and is_a) or (outcome == "B" and not is_a):
        return 1.0
    return 0.0


class TemporalGraphNN:
    """
    Temporal graph NN featurizer + small supervised head (numpy only).

    Follows AGENT.md protocol: chronological, pre-match state only for labels,
    explicit variations, deterministic, saveable weights, brier metrics.
    """

    def __init__(
        self,
        emb_dim: int = 8,
        seed: int = 42,
        temporal_only: bool = False,
        msg_scale: float = 0.1,
    ) -> None:
        """Initialize with fixed RNG for full replicability (AGENT Rule 25)."""
        self.emb_dim: int = int(emb_dim)
        self.seed: int = int(seed)
        self.temporal_only: bool = bool(temporal_only)
        self.msg_scale: float = float(msg_scale)
        self.rng = np.random.default_rng(self.seed)

        # Per-team state (populated chronologically)
        self.team_embs: Dict[str, np.ndarray] = {}
        self.team_hist: Dict[str, List[Dict[str, Any]]] = {}  # list of {'dt', 'opp', 'strength', 'opp_emb_snap'}

        # Graph + temporal gate params (seeded once, *fixed* during sequential walk).
        # These act as a deterministic (non-learned-in-GD) feature extractor.
        d = self.emb_dim
        self.W_msg = self.rng.normal(0.0, 0.05, (d, d)).astype(np.float32)
        self.b_msg = np.zeros(d, dtype=np.float32)

        # GRU-style gates: concat(h, x) -> gates
        self.Wz = self.rng.normal(0.0, 0.05, (d, 2 * d)).astype(np.float32)
        self.bz = np.zeros(d, dtype=np.float32)
        self.Wr = self.rng.normal(0.0, 0.05, (d, 2 * d)).astype(np.float32)
        self.br = np.zeros(d, dtype=np.float32)
        self.Wh = self.rng.normal(0.0, 0.05, (d, 2 * d)).astype(np.float32)
        self.bh = np.zeros(d, dtype=np.float32)

        # FF head (trained in train(); 2 hidden layers + output)
        self.head_W1: Optional[np.ndarray] = None
        self.head_b1: Optional[np.ndarray] = None
        self.head_W2: Optional[np.ndarray] = None
        self.head_b2: Optional[np.ndarray] = None
        self.head_W3: Optional[np.ndarray] = None
        self.head_b3: Optional[np.ndarray] = None

        self.is_trained: bool = False
        self._input_dim: Optional[int] = None

    # ------------------------------------------------------------------
    # Internal deterministic helpers (no side effects on rng after init)
    # ------------------------------------------------------------------
    def _get_emb(self, team: str) -> np.ndarray:
        if team not in self.team_embs:
            # Small init (reproducible via self.rng state at first encounter order)
            self.team_embs[team] = self.rng.normal(0.0, 0.02, self.emb_dim).astype(np.float32)
            self.team_hist[team] = []
        return self.team_embs[team].copy()

    def _sigmoid(self, x: np.ndarray) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-np.clip(x, -30.0, 30.0)))

    def _relu(self, x: np.ndarray) -> np.ndarray:
        return np.maximum(0.0, x)

    def _softmax(self, logits: np.ndarray) -> np.ndarray:
        # numerically stable along batch axis
        m = np.max(logits, axis=1, keepdims=True)
        ex = np.exp(logits - m)
        return ex / np.sum(ex, axis=1, keepdims=True)

    def _gru_update(self, h: np.ndarray, x: np.ndarray) -> np.ndarray:
        """GRU-like gate in pure numpy. x = message vector."""
        concat = np.concatenate([h, x]).astype(np.float32)
        z = self._sigmoid(self.Wz @ concat + self.bz)
        r = self._sigmoid(self.Wr @ concat + self.br)
        h_cand = np.tanh(self.Wh @ np.concatenate([r * h, x]) + self.bh)
        return ((1.0 - z) * h + z * h_cand).astype(np.float32)

    def _compute_message(self, team: str, cur_dt: datetime) -> np.ndarray:
        """Time-decayed opponent message + 1-layer linear conv approx."""
        if self.temporal_only:
            return np.zeros(self.emb_dim, dtype=np.float32)

        hist = self.team_hist.get(team, [])
        if not hist:
            return np.zeros(self.emb_dim, dtype=np.float32)

        agg = np.zeros(self.emb_dim, dtype=np.float32)
        wsum = 0.0
        for entry in hist:
            dt = entry["dt"]
            delta_days = (cur_dt - dt).days
            if delta_days <= 0:
                continue
            w_time = math.exp(-delta_days / 180.0)
            w = w_time * float(entry["strength"])
            if w > 1e-8:
                agg += w * entry["opp_emb_snap"]
                wsum += w

        if wsum < 1e-8:
            return np.zeros(self.emb_dim, dtype=np.float32)

        mean_agg = (agg / wsum).astype(np.float32)

        # 1-2 layer graph conv approx (here: single linear + tanh)
        msg = (self.W_msg @ mean_agg) + self.b_msg
        msg = np.tanh(msg) * self.msg_scale
        return msg.astype(np.float32)

    def _forward_head(self, X: np.ndarray) -> np.ndarray:
        """FF head forward (used both in GD and inference)."""
        assert self.head_W1 is not None
        h1 = self._relu(X @ self.head_W1 + self.head_b1)
        h2 = self._relu(h1 @ self.head_W2 + self.head_b2)
        logits = h2 @ self.head_W3 + self.head_b3
        return logits.astype(np.float32)

    # ------------------------------------------------------------------
    # Core chronological processing (AGENT.md Step C + temporal graph walk)
    # ------------------------------------------------------------------
    def process_match(
        self,
        team_a: str,
        team_b: str,
        dt: datetime,
        outcome: str,
        elo_a: float = 1500.0,
        elo_b: float = 1500.0,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Return *pre*-match embeddings (for feature extraction / head labels).
        Then apply graph message + temporal GRU-like update using result.
        Snapshots of *pre* opponent embs are stored to avoid future leakage.
        """
        emb_a = self._get_emb(team_a)
        emb_b = self._get_emb(team_b)
        pre_a = emb_a.copy()
        pre_b = emb_b.copy()

        # Messages from history *before* this match
        msg_a = self._compute_message(team_a, dt)
        msg_b = self._compute_message(team_b, dt)

        if not self.temporal_only:
            emb_a = self._gru_update(emb_a, msg_a)
            emb_b = self._gru_update(emb_b, msg_b)
        else:
            # Pure temporal: very light self-gating (no graph neighbors)
            # Equivalent to slow EWMA-style forgetting of prior state.
            emb_a = (0.97 * emb_a + 0.03 * np.zeros_like(emb_a)).astype(np.float32)
            emb_b = (0.97 * emb_b + 0.03 * np.zeros_like(emb_b)).astype(np.float32)

        # Strengths for the *current* result (for future opponents' messages)
        str_a = _outcome_to_strength(outcome, is_a=True)
        str_b = _outcome_to_strength(outcome, is_a=False)

        # Record pre-match snapshot of opponent for the *other* team's future messages
        self.team_hist[team_a].append(
            {"dt": dt, "opp": team_b, "strength": str_a, "opp_emb_snap": pre_b}
        )
        self.team_hist[team_b].append(
            {"dt": dt, "opp": team_a, "strength": str_b, "opp_emb_snap": pre_a}
        )

        self.team_embs[team_a] = emb_a
        self.team_embs[team_b] = emb_b

        return pre_a, pre_b

    # ------------------------------------------------------------------
    # Train: sequential walk + supervised head GD (chrono splits)
    # ------------------------------------------------------------------
    def _load_csv_rows(self, csv_path: Path) -> List[Dict[str, str]]:
        """Load exactly the historical dataset (replicable loader contract)."""
        if not csv_path.exists():
            raise FileNotFoundError(
                f"{csv_path} not found. Run wc_backtest_historical_loader.py first "
                "(per AGENT.md Rule 25 + FUTURE_UPDATE_PROTOCOL)."
            )
        rows: List[Dict[str, str]] = []
        with open(csv_path, newline="") as f:
            for row in csv.DictReader(f):
                rows.append(row)
        return rows

    def train(
        self,
        csv_path: str | Path = "wc_backtest_historical_dataset.csv",
        lr: float = 0.04,
        epochs: int = 280,
        verbose: bool = False,
    ) -> Dict[str, float]:
        """
        1. Full chronological pass over dataset (builds contextual embs).
        2. Collect pre-match features + labels.
        3. Chrono 70/15/15 splits.
        4. Train FF head with manual GD (CE loss).
        5. Return brier + acc on splits.
        """
        csv_p = Path(csv_path)
        rows = self._load_csv_rows(csv_p)

        # Ensure chronological (dataset is already sorted, but enforce)
        rows = sorted(rows, key=lambda r: _parse_date(r["date"]))

        # Fresh state for reproducible walk
        self.team_embs = {}
        self.team_hist = {}

        feats: List[np.ndarray] = []
        ys: List[int] = []

        for row in rows:
            dt = _parse_date(row["date"])
            ta = row["team_a"]
            tb = row["team_b"]
            outcome = row["outcome"]
            ea = float(row.get("elo_a_pre", 1500.0))
            eb = float(row.get("elo_b_pre", 1500.0))

            pre_a, pre_b = self.process_match(ta, tb, dt, outcome, ea, eb)

            diff = pre_a - pre_b
            abs_diff = np.abs(diff)
            elo_proxy = (ea - eb) / 400.0
            feat = np.concatenate([diff, abs_diff, [elo_proxy]]).astype(np.float32)

            feats.append(feat)
            ys.append({"A": 0, "D": 1, "B": 2}[outcome])

        X = np.stack(feats)  # (N, 2d+1)
        y = np.asarray(ys, dtype=np.int64)
        self._input_dim = X.shape[1]

        # Chronological splits (time-series discipline, AGENT.md replicability)
        n = len(y)
        i_train = int(n * 0.70)
        i_val = int(n * 0.85)
        X_tr, y_tr = X[:i_train], y[:i_train]
        X_va, y_va = X[i_train:i_val], y[i_train:i_val]
        X_te, y_te = X[i_val:], y[i_val:]

        # Head architecture (small, 2 hidden)
        d_in = X.shape[1]
        d_h1 = max(4, 2 * self.emb_dim)
        d_h2 = max(3, self.emb_dim)

        # Re-init head with same seed logic for full determinism
        rng_head = np.random.default_rng(self.seed + 1)  # separate but deterministic
        self.head_W1 = rng_head.normal(0.0, 0.08, (d_in, d_h1)).astype(np.float32)
        self.head_b1 = np.zeros(d_h1, dtype=np.float32)
        self.head_W2 = rng_head.normal(0.0, 0.08, (d_h1, d_h2)).astype(np.float32)
        self.head_b2 = np.zeros(d_h2, dtype=np.float32)
        self.head_W3 = rng_head.normal(0.0, 0.08, (d_h2, 3)).astype(np.float32)
        self.head_b3 = np.zeros(3, dtype=np.float32)

        # Manual GD loop (pure numpy, no autograd)
        onehot_tr = np.eye(3, dtype=np.float32)[y_tr]
        eps = 1e-8

        for ep in range(epochs):
            # forward
            z1 = X_tr @ self.head_W1 + self.head_b1
            h1 = self._relu(z1)
            z2 = h1 @ self.head_W2 + self.head_b2
            h2 = self._relu(z2)
            logits = h2 @ self.head_W3 + self.head_b3
            probs = self._softmax(logits)

            # cross-entropy grad w.r.t logits
            dlogits = (probs - onehot_tr) / max(1, len(y_tr))

            # layer 3
            dW3 = h2.T @ dlogits
            db3 = dlogits.sum(axis=0)

            dh2 = dlogits @ self.head_W3.T
            dz2 = dh2 * (z2 > 0).astype(np.float32)

            # layer 2
            dW2 = h1.T @ dz2
            db2 = dz2.sum(axis=0)

            dh1 = dz2 @ self.head_W2.T
            dz1 = dh1 * (z1 > 0).astype(np.float32)

            # layer 1
            dW1 = X_tr.T @ dz1
            db1 = dz1.sum(axis=0)

            # GD step
            self.head_W3 -= lr * dW3
            self.head_b3 -= lr * db3
            self.head_W2 -= lr * dW2
            self.head_b2 -= lr * db2
            self.head_W1 -= lr * dW1
            self.head_b1 -= lr * db1

            if verbose and (ep % 70 == 0 or ep == epochs - 1):
                p_tr = self._softmax(self._forward_head(X_tr))
                ce = -np.mean(np.sum(onehot_tr * np.log(np.clip(p_tr, eps, 1 - eps)), axis=1))
                print(f"  epoch {ep:3d}  train_ce={ce:.5f}")

        # Metrics
        def _compute_metrics(Xs: np.ndarray, ys: np.ndarray) -> Tuple[float, float]:
            ps = self._softmax(self._forward_head(Xs))
            onehot = np.eye(3, dtype=np.float32)[ys]
            brier = float(np.mean(np.sum((ps - onehot) ** 2, axis=1)))
            acc = float(np.mean(np.argmax(ps, axis=1) == ys))
            return brier, acc

        b_tr, a_tr = _compute_metrics(X_tr, y_tr)
        b_va, a_va = _compute_metrics(X_va, y_va)
        b_te, a_te = _compute_metrics(X_te, y_te)

        metrics: Dict[str, float] = {
            "brier_train": b_tr,
            "acc_train": a_tr,
            "brier_val": b_va,
            "acc_val": a_va,
            "brier_test": b_te,
            "acc_test": a_te,
            "n_train": float(len(y_tr)),
            "n_val": float(len(y_va)),
            "n_test": float(len(y_te)),
            "emb_dim": float(self.emb_dim),
            "temporal_only": float(self.temporal_only),
            "final_lr": lr,
            "epochs": float(epochs),
        }

        self.is_trained = True
        return metrics

    # ------------------------------------------------------------------
    # Inference (callable, matches wc_* predict style)
    # ------------------------------------------------------------------
    def predict_proba(
        self,
        team_a: str,
        team_b: str,
        elo_a: float = 1500.0,
        elo_b: float = 1500.0,
    ) -> Tuple[float, float, float]:
        """
        Return (p_win_a, p_draw, p_win_b) using frozen post-history embeddings + trained head.
        Falls back to zero-emb for unseen teams (rare in backtest).
        Always renormalizes.
        """
        if not self.is_trained or self.head_W1 is None:
            raise RuntimeError(
                "TemporalGraphNN not trained or loaded. Call train() or load() first."
            )

        emb_a = self.team_embs.get(
            team_a, np.zeros(self.emb_dim, dtype=np.float32)
        ).copy()
        emb_b = self.team_embs.get(
            team_b, np.zeros(self.emb_dim, dtype=np.float32)
        ).copy()

        diff = emb_a - emb_b
        abs_diff = np.abs(diff)
        elo_proxy = (elo_a - elo_b) / 400.0
        feat = np.concatenate([diff, abs_diff, [elo_proxy]]).astype(np.float32).reshape(1, -1)

        logits = self._forward_head(feat)
        probs = self._softmax(logits)[0]
        s = float(probs.sum())
        if s <= 0:
            return (1.0 / 3.0, 1.0 / 3.0, 1.0 / 3.0)
        return (float(probs[0] / s), float(probs[1] / s), float(probs[2] / s))

    # ------------------------------------------------------------------
    # Persist / restore weights (np.savez, AGENT reproducible artifacts)
    # ------------------------------------------------------------------
    def save(self, path: Optional[str | Path] = None) -> Path:
        """Save all weights + metadata. Default: training/tgnn_d{dim}_{fg|t}.npz"""
        if path is None:
            variant = f"d{self.emb_dim}_{'t' if self.temporal_only else 'fg'}"
            path = Path("training") / f"tgnn_{variant}.npz"
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)

        teams = sorted(self.team_embs.keys())
        if teams:
            emb_mat = np.stack([self.team_embs[t] for t in teams], axis=0)
        else:
            emb_mat = np.zeros((0, self.emb_dim), dtype=np.float32)

        np.savez(
            p,
            teams=np.asarray(teams, dtype="U8"),
            embs=emb_mat,
            W_msg=self.W_msg,
            b_msg=self.b_msg,
            Wz=self.Wz,
            bz=self.bz,
            Wr=self.Wr,
            br=self.br,
            Wh=self.Wh,
            bh=self.bh,
            head_W1=self.head_W1 if self.head_W1 is not None else np.zeros(1, dtype=np.float32),
            head_b1=self.head_b1 if self.head_b1 is not None else np.zeros(1, dtype=np.float32),
            head_W2=self.head_W2 if self.head_W2 is not None else np.zeros(1, dtype=np.float32),
            head_b2=self.head_b2 if self.head_b2 is not None else np.zeros(1, dtype=np.float32),
            head_W3=self.head_W3 if self.head_W3 is not None else np.zeros(1, dtype=np.float32),
            head_b3=self.head_b3 if self.head_b3 is not None else np.zeros(1, dtype=np.float32),
            emb_dim=np.array(self.emb_dim, dtype=np.int32),
            temporal_only=np.array(int(self.temporal_only), dtype=np.int32),
            seed=np.array(self.seed, dtype=np.int32),
            input_dim=np.array(self._input_dim or 0, dtype=np.int32),
            is_trained=np.array(int(self.is_trained), dtype=np.int32),
        )
        return p

    def load(self, path: str | Path) -> None:
        """Load weights (exact round-trip with save)."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Weight file not found: {p}")
        data = np.load(p, allow_pickle=False)

        self.emb_dim = int(data["emb_dim"])
        self.temporal_only = bool(int(data["temporal_only"]))
        self.seed = int(data["seed"])
        self._input_dim = int(data["input_dim"]) if "input_dim" in data else None
        self.is_trained = bool(int(data["is_trained"]))

        # Rebuild rng (not used after load for predict)
        self.rng = np.random.default_rng(self.seed)

        self.W_msg = data["W_msg"].astype(np.float32)
        self.b_msg = data["b_msg"].astype(np.float32)
        self.Wz = data["Wz"].astype(np.float32)
        self.bz = data["bz"].astype(np.float32)
        self.Wr = data["Wr"].astype(np.float32)
        self.br = data["br"].astype(np.float32)
        self.Wh = data["Wh"].astype(np.float32)
        self.bh = data["bh"].astype(np.float32)

        teams = data["teams"].astype(str).tolist()
        embs = data["embs"].astype(np.float32)
        self.team_embs = {t: embs[i] for i, t in enumerate(teams)}
        self.team_hist = {t: [] for t in teams}  # history not needed for inference

        # Head
        self.head_W1 = data["head_W1"].astype(np.float32) if data["head_W1"].size > 1 else None
        self.head_b1 = data["head_b1"].astype(np.float32) if data["head_b1"].size > 1 else None
        self.head_W2 = data["head_W2"].astype(np.float32) if data["head_W2"].size > 1 else None
        self.head_b2 = data["head_b2"].astype(np.float32) if data["head_b2"].size > 1 else None
        self.head_W3 = data["head_W3"].astype(np.float32) if data["head_W3"].size > 1 else None
        self.head_b3 = data["head_b3"].astype(np.float32) if data["head_b3"].size > 1 else None


# ----------------------------------------------------------------------
# Convenience callable (wc_replicable style) for direct p_win integration
# ----------------------------------------------------------------------
def tgnn_predict_1x2(
    team_a: str,
    team_b: str,
    elo_a: float = 1500.0,
    elo_b: float = 1500.0,
    model: Optional[TemporalGraphNN] = None,
    default_model_path: Optional[str | Path] = None,
) -> Tuple[float, float, float]:
    """
    Drop-in style helper returning (pA, pD, pB).
    If model is None, attempts load from default path (training/tgnn_d8_fg.npz) or raises.
    Use after train() or for production load.
    """
    if model is None:
        model = TemporalGraphNN(emb_dim=8, temporal_only=False, seed=42)
        path = Path(default_model_path or "training/tgnn_d8_fg.npz")
        if not path.exists():
            # Try to auto-train if the CSV exists (for quick local repro)
            csvp = Path("wc_backtest_historical_dataset.csv")
            if csvp.exists():
                model.train(csv_path=str(csvp))
                model.save(path)
            else:
                raise RuntimeError(
                    "No trained model and no default weights. "
                    "Instantiate TemporalGraphNN and call .train() first, or provide weights."
                )
        else:
            model.load(path)
    return model.predict_proba(team_a, team_b, elo_a, elo_b)


# ----------------------------------------------------------------------
# Self-contained runner + example (matches other wc_*_*.py)
# ----------------------------------------------------------------------
if __name__ == "__main__":
    print("=" * 72)
    print("TemporalGraphNN — replicable numpy walk + head (AGENT.md / Rule 25)")
    print("=" * 72)

    results: Dict[str, Dict[str, float]] = {}
    saved_paths: List[Path] = []

    for dim in [4, 8, 16]:
        for temporal_only in [False, True]:
            variant = f"d{dim}_{'temporal' if temporal_only else 'fullgraph'}"
            print(f"\n--- Training {variant} ---")
            m = TemporalGraphNN(emb_dim=dim, seed=42, temporal_only=temporal_only)
            mets = m.train(verbose=False)
            results[variant] = mets
            p = m.save()
            saved_paths.append(p)
            print(f"  Brier (train/val/test): {mets['brier_train']:.5f} / {mets['brier_val']:.5f} / {mets['brier_test']:.5f}")
            print(f"  Acc   (train/val/test): {mets['acc_train']:.4f} / {mets['acc_val']:.4f} / {mets['acc_test']:.4f}")
            print(f"  Saved: {p}")

            # quick sanity predict on a known pair
            pa, pd, pb = m.predict_proba("BRA", "ARG", 2060.0, 2050.0)
            print(f"  BRA vs ARG (example) p: {pa:.4f} / {pd:.4f} / {pb:.4f}")

    print("\n" + "=" * 72)
    print("SUMMARY (lower brier better; deterministic seed=42)")
    for v, m in results.items():
        print(f"  {v:22s}  test_brier={m['brier_test']:.5f}  test_acc={m['acc_test']:.4f}")
    print("=" * 72)

    # Demonstrate integration helper + load roundtrip
    print("\nIntegration demo (tgnn_predict_1x2 + load):")
    m8 = TemporalGraphNN(emb_dim=8, temporal_only=False, seed=42)
    m8.load(saved_paths[1])  # d8 fullgraph
    p_demo = tgnn_predict_1x2("NED", "JPN", 1950.0, 1840.0, model=m8)
    print(f"  NED vs JPN p_win (loaded): {p_demo}")
    print("\nReady for use in wc_replicable_pipeline.py or wc_backtest_framework.py as extra signal.")
    print("Remember: respect Rule 27 / trap_analysis before raising any ensemble weight.")