# WCdecider

Screenshot-driven FIFA World Cup 2026 betting analysis with a replicable v4.1 Elo + Dixon-Coles ensemble pipeline.

## Live report

After deploy: **https://pillb.github.io/WCdecider/**

## Local

```bash
python3 wc_model_v4_replicable_pipeline.py
python3 scripts/build_site.py
python3 -m http.server 8765 --directory site
# open http://127.0.0.1:8765/
```

## Tests

```bash
pip install -r requirements-ci.txt
playwright install chromium
pytest tests/ -v
```

Deployed-site validation:

```bash
DEPLOY_URL=https://pillb.github.io/WCdecider/ pytest tests/test_deployed_site.py -v
```