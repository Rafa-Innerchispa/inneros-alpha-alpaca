#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== pytest (Python 3.12 container; host 3.14 lacks pydantic wheels) =="
docker run --rm -v "$ROOT:/app" -w /app python:3.12-slim bash -lc \
  'pip install -q -r requirements.txt && python -m pytest -q --tb=line'

echo "== backend health =="
curl -fsS http://127.0.0.1:8088/health | python3 -c \
  "import sys,json;d=json.load(sys.stdin); assert d['ok'] and d['paper_only']; print('health OK')"

echo "== pipeline analysis-only =="
curl -fsS -X POST 'http://127.0.0.1:8088/api/pipeline/SPY?execute=false' | python3 -c \
  "import sys,json;d=json.load(sys.stdin); c=d['correlation_id']; assert all(e['correlation_id']==c for e in d['trace']); assert d['execution']['status']=='blocked'; print('pipeline OK', c)"

echo "== console static =="
curl -fsS -o /dev/null -w 'console HTTP %{http_code}\n' http://127.0.0.1:8099/

echo "smoke-docker PASS"
