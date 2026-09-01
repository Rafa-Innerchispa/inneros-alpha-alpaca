# InnerOS Alpha — Alpaca paper trading agent

Governed multi-agent **paper-only** options trading console for the
[Alpaca AI Trading Agents Hackathon](https://lablab.ai/ai-hackathons/alpaca-ai-trading-agents-hackathon)
(28 Aug–4 Sep 2026).

**Paper only. No live money. No secrets in this repo.**

## Status

| Layer | Owner | State |
|---|---|---|
| GitHub repo | Codex `ops_b7fe97e7640f` | Created; spine pending |
| Demo console | Cursor `ops_ad1a26fc70d4` | Fixture-marked UI on `cursor/alpaca-console-20260901` |
| Paper backend | Codex `ops_b7fe97e7640f` | FastAPI spine with risk gates |
| Risk gates | Antigravity `ops_5bfb63ddfe24` | Proposed |
| Judge / previous hackathon | frozen | Do not touch |

## Demo console (local)

```bash
python3 -m http.server 8099 --directory apps/console
```

Open http://127.0.0.1:8099/ — portfolio $100k paper, pipeline
Market → Strategy → Risk → Execution, kill switch, Live Trace.

Trace rows tagged **FIXTURE** are not live fills. Terminal states are
`PASS` / `BLOCKED` / `NO_TRADE` / `FAIL` only.

## Paper backend (local)

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[test,mongo]"
uvicorn inneros_alpha_alpaca.app:app --reload --host 127.0.0.1 --port 8080
```

Smoke checks:

```bash
pytest -q
curl http://127.0.0.1:8080/health
```

The backend defaults to paper mode, never stores secrets, and returns
`NO_TRADE` instead of pretending to submit orders when Alpaca paper credentials
are missing.

## Layout

```
apps/console/     Cursor demo UI (this branch)
src/              Codex backend spine (not in this bootstrap)
tests/            Codex smoke tests
docs/             hackathon notes
.env.example      no secrets
```
