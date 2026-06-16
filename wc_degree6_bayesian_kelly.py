#!/usr/bin/env python3
"""
WCdecider Degree 6 — Hierarchical Bayesian Draw Uncertainty → Conservative Kelly
================================================================================

Models ±3pp draw-probability bands around v4 1X2 anchor outputs, then computes
quarter-Kelly stakes with a conservative haircut vs point-estimate Kelly.

Scope:
  - WC_2026_GROUP (9 settled MD1–MD3 matches)
  - Draw-heavy WC shocks: ARG-KSA, GER-JPN, ESP-CPV (2018/2022/2026)

Run: python3 wc_degree6_bayesian_kelly.py

Optional full MCMC: pip install pymc && python3 wc_degree6_bayesian_kelly.py --pymc
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from wc_backtest_framework import HistoricalMatch, get_all_matches, model_v4_1x2
from wc_model_v3 import quarter_kelly

# ---------------------------------------------------------------------------
# Degree-6 constants
# ---------------------------------------------------------------------------

DRAW_BAND_PP = 0.03          # ±3 percentage-point uncertainty on p_draw
KELLY_FRACTION = 0.25        # quarter-Kelly per AGENT.md
BANKROLL = 200.0

SHOCK_KEYS = [
    ("ARG", "KSA"),   # WC 2022 1-2 upset; draw band matters for fav traps
    ("GER", "JPN"),   # WC 2022 1-2 upset
    ("ESP", "CPV"),   # WC 2026 0-0 draw shock
]

# MD2 actual bets (from MD3_FINAL_REPORT.md)
MD2_BETS = [
    {
        "match_key": ("AUS", "TUR"),
        "pick": "A",
        "odds": 5.35,
        "actual_stake": 15.0,
        "result": "W",
        "pnl": 65.25,
    },
    {
        "match_key": ("CIV", "ECU"),
        "pick": "A",
        "odds": 3.80,
        "actual_stake": 10.0,
        "result": "W",
        "pnl": 28.00,
    },
    {
        "match_key": ("NED", "JPN"),
        "pick": "A",
        "odds": 2.15,
        "actual_stake": 30.0,
        "result": "L",
        "pnl": -30.00,
    },
    {
        "match_key": ("SWE", "TUN"),
        "pick": "B",   # Tunisia underdog
        "odds": 4.40,
        "actual_stake": 25.0,
        "result": "L",
        "pnl": -25.00,
    },
]


@dataclass
class DrawBand:
    """Hierarchical draw uncertainty band around point estimate."""
    p_draw_point: float
    p_draw_lo: float
    p_draw_hi: float
    prior_mean: float
    prior_n_eff: float


@dataclass
class KellyComparison:
    match: str
    pick: str
    odds: float
    p_point: float
    p_conservative: float
    stake_point: float
    stake_conservative: float
    haircut_pct: float
    outcome: str
    p_draw_v4: float
    draw_band: DrawBand


def kelly_fraction(p: float, o: float) -> float:
    if o <= 1.0:
        return 0.0
    return max(0.0, (p * o - 1.0) / (o - 1.0))


def quarter_kelly_stake(p: float, o: float, bankroll: float = BANKROLL) -> float:
    return KELLY_FRACTION * kelly_fraction(p, o) * bankroll


def hierarchical_draw_prior(matches: List[HistoricalMatch]) -> Tuple[float, float]:
    """
    Empirical-Bayes prior: WC group-stage draw rate with effective sample size.
    Pool WC 2018 + 2022 + 2026 strata (degree-6 hierarchy level 1).
    """
    wc = [m for m in matches if "WC_" in m.competition and "GROUP" in m.competition]
    n_draw = sum(1 for m in wc if m.outcome == "D")
    n = len(wc)
    # Beta(2,2) weakly informative prior → posterior mean
    alpha, beta = 2.0 + n_draw, 2.0 + (n - n_draw)
    return alpha / (alpha + beta), n


def draw_band(
    p_draw_point: float,
    prior_mean: float,
    prior_n_eff: float,
    band_pp: float = DRAW_BAND_PP,
) -> DrawBand:
    """
    Combine hierarchical prior with point estimate:
      p_post = (n_eff * p_point + n_prior * prior_mean) / (n_eff + n_prior)
    Band = ±band_pp around p_post (degree-6 operational band).
    """
    n_eff = 4.0  # pseudo-count for single-match v4 anchor
    p_post = (n_eff * p_draw_point + prior_n_eff * prior_mean) / (n_eff + prior_n_eff)
    p_lo = max(0.10, p_post - band_pp)
    p_hi = min(0.40, p_post + band_pp)
    return DrawBand(
        p_draw_point=p_draw_point,
        p_draw_lo=p_lo,
        p_draw_hi=p_hi,
        prior_mean=prior_mean,
        prior_n_eff=prior_n_eff,
    )


def redistribute_1x2(
    p_a: float, p_d: float, p_b: float, p_d_new: float
) -> Tuple[float, float, float]:
    """Fix draw mass; scale win probs proportionally."""
    rem = 1.0 - p_d_new
    win_sum = p_a + p_b
    if win_sum <= 0:
        return rem / 2, p_d_new, rem / 2
    scale = rem / win_sum
    return p_a * scale, p_d_new, p_b * scale


def conservative_pick_prob(
    p_a: float, p_d: float, p_b: float, pick: str, band: DrawBand
) -> Tuple[float, float]:
    """
    Worst-case pick probability within draw band (minimizes Kelly stake).
    - Fav/underdog win picks: use p_draw_hi (steals mass from wins)
    - Draw pick: use p_draw_lo
    """
    idx = {"A": 0, "D": 1, "B": 2}
    probs = [p_a, p_d, p_b]
    if pick == "D":
        p_d_use = band.p_draw_lo
    else:
        p_d_use = band.p_draw_hi
    ca, cd, cb = redistribute_1x2(p_a, p_d, p_b, p_d_use)
    cons = [ca, cd, cb][idx[pick]]
    point = probs[idx[pick]]
    return point, cons


def compare_kelly(
    match_label: str,
    p_a: float,
    p_d: float,
    p_b: float,
    pick: str,
    odds: float,
    band: DrawBand,
    outcome: str = "",
) -> KellyComparison:
    p_point, p_cons = conservative_pick_prob(p_a, p_d, p_b, pick, band)
    s_point = quarter_kelly_stake(p_point, odds)
    s_cons = quarter_kelly_stake(p_cons, odds)
    haircut = 0.0 if s_point <= 0 else (1.0 - s_cons / s_point) * 100.0
    return KellyComparison(
        match=match_label,
        pick=pick,
        odds=odds,
        p_point=p_point,
        p_conservative=p_cons,
        stake_point=s_point,
        stake_conservative=s_cons,
        haircut_pct=haircut,
        outcome=outcome,
        p_draw_v4=p_d,
        draw_band=band,
    )


def find_match(matches: List[HistoricalMatch], key: Tuple[str, str]) -> Optional[HistoricalMatch]:
    a, b = key
    for m in matches:
        if (m.team_a, m.team_b) == (a, b) or (m.team_a, m.team_b) == (b, a):
            return m
    return None


def wc2026_group(matches: List[HistoricalMatch]) -> List[HistoricalMatch]:
    return [m for m in matches if m.competition == "WC_2026_GROUP"]


def analyze_wc2026_group(matches: List[HistoricalMatch]) -> List[KellyComparison]:
    prior_mean, prior_n = hierarchical_draw_prior(matches)
    results = []
    for m in wc2026_group(matches):
        p_a, p_d, p_b = model_v4_1x2(m)
        band = draw_band(p_d, prior_mean, prior_n)
        # Evaluate each outcome at market odds (diagnostic)
        for pick, odds in [("A", m.o_win_a), ("D", m.o_draw), ("B", m.o_win_b)]:
            results.append(compare_kelly(
                f"{m.team_a}-{m.team_b}",
                p_a, p_d, p_b, pick, odds, band, outcome=m.outcome,
            ))
    return results


def analyze_shocks(matches: List[HistoricalMatch]) -> List[Dict]:
    prior_mean, prior_n = hierarchical_draw_prior(matches)
    rows = []
    for key in SHOCK_KEYS:
        m = find_match(matches, key)
        if not m:
            continue
        p_a, p_d, p_b = model_v4_1x2(m)
        band = draw_band(p_d, prior_mean, prior_n)
        _, p_a_cons = conservative_pick_prob(p_a, p_d, p_b, "A", band)
        _, p_d_cons = conservative_pick_prob(p_a, p_d, p_b, "D", band)
        rows.append({
            "match": f"{m.team_a}-{m.team_b} ({m.date})",
            "actual": m.outcome,
            "score": m.score,
            "p_draw_v4": p_d,
            "band_lo_hi": (band.p_draw_lo, band.p_draw_hi),
            "pA_conservative": p_a_cons,
            "pD_conservative": p_d_cons,
            "draw_realized": m.outcome == "D",
            "fav_trap": m.o_win_a < 1.5 and m.outcome != "A",
        })
    return rows


def md2_counterfactual(matches: List[HistoricalMatch]) -> Dict:
    """Would conservative Kelly have reduced MD2 losses?"""
    prior_mean, prior_n = hierarchical_draw_prior(matches)
    actual_pnl = sum(b["pnl"] for b in MD2_BETS)
    actual_stake = sum(b["actual_stake"] for b in MD2_BETS)

    rows = []
    cons_pnl = 0.0
    cons_stake = 0.0
    point_pnl = 0.0
    point_stake = 0.0

    for bet in MD2_BETS:
        m = find_match(matches, bet["match_key"])
        if not m:
            continue
        p_a, p_d, p_b = model_v4_1x2(m)
        band = draw_band(p_d, prior_mean, prior_n)
        k = compare_kelly(
            f"{bet['match_key'][0]}-{bet['match_key'][1]}",
            p_a, p_d, p_b, bet["pick"], bet["odds"], band, bet["result"],
        )
        # Cap at actual stake for apples-to-apples (we only reduce, never increase)
        s_cons = min(bet["actual_stake"], k.stake_conservative)
        s_point = min(bet["actual_stake"], k.stake_point)

        if bet["result"] == "W":
            cons_pnl += s_cons * (bet["odds"] - 1)
            point_pnl += s_point * (bet["odds"] - 1)
        else:
            cons_pnl -= s_cons
            point_pnl -= s_point
        cons_stake += s_cons
        point_stake += s_point

        rows.append({
            "match": k.match,
            "pick": bet["pick"],
            "odds": bet["odds"],
            "p_point": k.p_point,
            "p_cons": k.p_conservative,
            "haircut_pct": k.haircut_pct,
            "actual_stake": bet["actual_stake"],
            "point_stake": round(s_point, 2),
            "cons_stake": round(s_cons, 2),
            "saved_on_loss": round(bet["actual_stake"] - s_cons, 2) if bet["result"] == "L" else 0.0,
            "result": bet["result"],
        })

    loss_saved = sum(r["saved_on_loss"] for r in rows)
    return {
        "rows": rows,
        "actual_pnl": actual_pnl,
        "actual_stake": actual_stake,
        "point_kelly_pnl": round(point_pnl, 2),
        "conservative_pnl": round(cons_pnl, 2),
        "loss_stake_saved": round(loss_saved, 2),
        "would_reduce_losses": cons_pnl > actual_pnl or loss_saved > 0,
        "ned_jpn_pass": rows[2]["cons_stake"] < 5.0 if len(rows) > 2 else None,
    }


def pymc_draw_posterior_stub(
    p_draw_point: float,
    prior_mean: float = 0.26,
    band_pp: float = DRAW_BAND_PP,
    draws: int = 2000,
) -> Optional[Dict]:
    """
    Optional PyMC path: hierarchical Beta-Binomial on WC draw rate.
    Returns posterior quantiles; None if pymc not installed.
    """
    try:
        import pymc as pm  # type: ignore
        import numpy as np
    except ImportError:
        return None

    # Synthetic WC group observations: 26% draw rate, n=100 pseudo
    n_matches = 100
    n_draws_obs = int(round(prior_mean * n_matches))

    with pm.Model():
        # Level-1: global WC group draw rate
        mu_global = pm.Beta("mu_global", alpha=2, beta=6)
        # Level-2: match-level draw prob shrunk toward global
        theta = pm.Beta("theta", alpha=mu_global * 20, beta=(1 - mu_global) * 20)
        pm.Binomial("obs", n=n_matches, p=theta, observed=n_draws_obs)
        idata = pm.sample(draws=draws, tune=500, progressbar=False, random_seed=42)

    post = idata.posterior["theta"].values.flatten()
    return {
        "mean": float(post.mean()),
        "q05": float(np.quantile(post, 0.05)),
        "q95": float(np.quantile(post, 0.95)),
        "band_pp": band_pp,
        "point_anchor": p_draw_point,
    }


def three_critiques() -> List[str]:
    return [
        "±3pp band is operational, not fully identified: N=9 WC26 + 3 shock archetypes "
        "cannot pin a hierarchical σ; the band is a sensitivity envelope, not a posterior CI.",
        "Conservative Kelly only shifts mass via draw — it ignores win/loss correlation "
        "(Dixon-Coles ρ) and joint combo paths; draw-heavy 0-0 shocks still under-weight "
        "rotation/minnow channels that v4 Rule 21 already handles in p_point.",
        "Haircut helps MOD favorite traps (NED-JPN) but also trims winning SPEC longshots "
        "(AUS, CIV); net MD2 P&L improves only if loss reduction exceeds foregone win upside — "
        "pair with Rule 24 tier gates, not Kelly alone.",
    ]


def run_degree6(use_pymc: bool = False) -> Dict:
    matches = get_all_matches()
    prior_mean, prior_n = hierarchical_draw_prior(matches)
    wc26 = wc2026_group(matches)
    group_rows = analyze_wc2026_group(matches)
    shocks = analyze_shocks(matches)
    md2 = md2_counterfactual(matches)

    # Positive-EV picks only (EV > 1.5% at point estimate)
    ev_rows = []
    for k in group_rows:
        ev = (k.p_point * k.odds - 1) * 100
        if ev >= 1.5:
            ev_rows.append(k)

    haircuts = [k.haircut_pct for k in ev_rows if k.stake_point > 0]
    mean_haircut = sum(haircuts) / len(haircuts) if haircuts else 0.0

    pymc_result = None
    if use_pymc and wc26:
        _, p_d, _ = model_v4_1x2(wc26[0])
        pymc_result = pymc_draw_posterior_stub(p_d, prior_mean=prior_mean)

    return {
        "prior": {"wc_draw_rate": prior_mean, "n_wc_matches": int(prior_n)},
        "wc2026_n": len(wc26),
        "mean_haircut_pct": mean_haircut,
        "ev_positive_rows": ev_rows,
        "shocks": shocks,
        "md2": md2,
        "critiques": three_critiques(),
        "pymc": pymc_result,
    }


def print_report(result: Dict) -> None:
    print("=" * 78)
    print("DEGREE 6 — Hierarchical Bayesian Draw Bands → Conservative Quarter-Kelly")
    print("=" * 78)
    prior = result["prior"]
    print(f"\nHierarchical prior: WC group draw rate = {prior['wc_draw_rate']:.1%} "
          f"(N={prior['n_wc_matches']} matches)")
    print(f"Draw uncertainty band: ±{DRAW_BAND_PP*100:.0f}pp around posterior-merged estimate")

    print(f"\n--- WC_2026_GROUP (N={result['wc2026_n']}) v4 1X2 + Kelly haircut (EV≥1.5%) ---")
    print(f"{'Match':<12} {'Pick':<4} {'Odds':>5} {'p_pt':>6} {'p_cons':>6} "
          f"{'¼K_pt':>7} {'¼K_cons':>8} {'Haircut':>8} {'Act':>3}")
    for k in result["ev_positive_rows"]:
        print(f"{k.match:<12} {k.pick:<4} {k.odds:>5.2f} {k.p_point:>6.1%} {k.p_conservative:>6.1%} "
              f"{k.stake_point:>7.2f} {k.stake_conservative:>8.2f} {k.haircut_pct:>7.1f}% {k.outcome:>3}")

    print(f"\nMean stake haircut (EV≥1.5% picks): {result['mean_haircut_pct']:.1f}%")

    print("\n--- Draw-heavy shock cases (ARG-KSA, GER-JPN, ESP-CPV) ---")
    for s in result["shocks"]:
        lo, hi = s["band_lo_hi"]
        print(f"  {s['match']}: actual={s['actual']} score={s['score']} "
              f"pD_v4={s['p_draw_v4']:.1%} band=[{lo:.1%},{hi:.1%}] "
              f"fav_trap={s['fav_trap']}")

    md2 = result["md2"]
    print("\n--- MD2 counterfactual (actual vs conservative ¼-Kelly) ---")
    for r in md2["rows"]:
        print(f"  {r['match']} {r['pick']} @{r['odds']}: actual=S/{r['actual_stake']:.0f} "
              f"→ cons=S/{r['cons_stake']:.2f} (haircut {r['haircut_pct']:.1f}%) "
              f"{'saved S/'+str(r['saved_on_loss']) if r['saved_on_loss'] else ''} [{r['result']}]")
    print(f"\n  Actual MD2 P&L:        S/{md2['actual_pnl']:+.2f}  (stake S/{md2['actual_stake']:.0f})")
    print(f"  Point ¼-Kelly P&L:     S/{md2['point_kelly_pnl']:+.2f}")
    print(f"  Conservative ¼-Kelly:  S/{md2['conservative_pnl']:+.2f}")
    print(f"  Loss stake saved:      S/{md2['loss_stake_saved']:.2f}")
    print(f"  Would reduce MD2 losses? {'YES' if md2['would_reduce_losses'] else 'NO'}")
    if md2.get("ned_jpn_pass") is not None:
        print(f"  NED-JPN cons stake < S/5 (near-PASS)? {'YES' if md2['ned_jpn_pass'] else 'NO'}")

    print("\n--- Three critiques ---")
    for i, c in enumerate(result["critiques"], 1):
        print(f"  {i}. {c}")

    print("\n--- PyMC optional stub ---")
    if result["pymc"]:
        p = result["pymc"]
        print(f"  Posterior θ: mean={p['mean']:.3f} 90% CI=[{p['q05']:.3f},{p['q95']:.3f}]")
    else:
        print("  Path: wc_degree6_bayesian_kelly.pymc_draw_posterior_stub()")
        print("  Install: pip install pymc")
        print("  Run: python3 wc_degree6_bayesian_kelly.py --pymc")


if __name__ == "__main__":
    import sys
    use_pymc = "--pymc" in sys.argv
    print_report(run_degree6(use_pymc=use_pymc))