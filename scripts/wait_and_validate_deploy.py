#!/usr/bin/env python3
"""Wait for GitHub Pages propagation then run Playwright deployed-site tests.

Per AGENT.md update protocol: This ensures the live site has correct layout and implementation of *all* matches (old + newly incremented sections), bilingual toggle, recommendations, etc.
Run as final step after any new screenshot batch update (retrain, sections, tests, build).
Must pass test_deployed_site.py with 0 failures.
See AGENT.md "Automated Update Protocol" for full automatic/comprehensive cycle.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from urllib.request import urlopen
from urllib.error import URLError, HTTPError


def normalize_url(url: str) -> str:
    url = url.strip()
    if not url:
        raise ValueError("DEPLOY_URL is empty")
    if not url.endswith("/"):
        url += "/"
    return url


def wait_for_live(url: str, timeout_sec: int = 300, interval: int = 10) -> None:
    deadline = time.time() + timeout_sec
    last_err = None
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=15) as resp:
                body = resp.read(8000).decode("utf-8", errors="replace")
                if resp.status == 200 and "WCdecider" in body and "v4.1" in body:
                    print(f"[wait] Live OK: {url} ({len(body)} bytes sampled)")
                    return
                last_err = f"status={resp.status}, missing markers"
        except (URLError, HTTPError, TimeoutError) as e:
            last_err = str(e)
        print(f"[wait] Not ready yet ({last_err}); retry in {interval}s...")
        time.sleep(interval)
    raise RuntimeError(f"Deploy URL not live after {timeout_sec}s: {url} — last: {last_err}")


def resolve_deploy_url() -> str:
    url = os.environ.get("DEPLOY_URL", "").strip()
    if url:
        return normalize_url(url)
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if repo and "/" in repo:
        owner, name = repo.split("/", 1)
        return normalize_url(f"https://{owner}.github.io/{name}/")
    raise ValueError("Set DEPLOY_URL or GITHUB_REPOSITORY for deployed validation")


def main() -> int:
    url = resolve_deploy_url()
    print(f"[validate] DEPLOY_URL={url}")
    wait_for_live(url)
    env = {**os.environ, "DEPLOY_URL": url}
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/test_deployed_site.py",
        "-v", "--tb=short",
    ]
    return subprocess.call(cmd, env=env)


if __name__ == "__main__":
    raise SystemExit(main())