#!/usr/bin/env bash
# Run a local LeaseShield smoke test: start both apps, audit the fixture, and
# open the GUI. Requires macOS/Linux, Python 3.11, Node.js, and an LLM API key.
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

die() {
  printf '\nERROR: %s\n' "$1" >&2
  if [[ -n "${LOG_DIR:-}" ]]; then
    for log in "$LOG_DIR"/*.log; do
      [[ -f "$log" ]] || continue
      printf '\n--- %s (last 35 lines) ---\n' "$(basename "$log")" >&2
      tail -n 35 "$log" >&2 || true
    done
  fi
  exit 1
}

command -v python3.11 >/dev/null 2>&1 || die "Python 3.11 is required. On macOS, install it with: brew install python@3.11"
command -v node >/dev/null 2>&1 || die "Node.js is required. Install Node.js 20 or newer, then reopen Terminal."
command -v npm >/dev/null 2>&1 || die "npm is required; reinstall Node.js with npm included."
command -v curl >/dev/null 2>&1 || die "curl is required."

NODE_MAJOR="$(node -p 'Number(process.versions.node.split(".")[0])')"
(( NODE_MAJOR >= 20 )) || die "Node.js 20 or newer is required; found $(node --version)."

[[ -f .env ]] || die "Missing .env. Copy .env.example to .env and set OPENAI_API_KEY (or LLM_API_KEY)."
[[ -f sample-commercial-lease-test.pdf ]] || die "Missing sample-commercial-lease-test.pdf fixture."

# Load local credentials without echoing them. .env must contain shell-compatible KEY=value lines.
set -a
# shellcheck disable=SC1091
source .env
set +a
[[ -n "${OPENAI_API_KEY:-}${LLM_API_KEY:-}" ]] || die "Set OPENAI_API_KEY or LLM_API_KEY in .env to run an audit."

if [[ ! -x .venv/bin/python ]]; then
  python3.11 -m venv .venv
fi
.venv/bin/python -m pip install -r backend/requirements.txt
npm --prefix frontend install --no-audit --no-fund

LOG_DIR="$(mktemp -d "${TMPDIR:-/tmp}/leaseshield-test.XXXXXX")"
UPLOAD_DIR="$LOG_DIR/uploads"
mkdir -p "$UPLOAD_DIR"
BACKEND_PID=""
FRONTEND_PID=""
cleanup() {
  [[ -z "$FRONTEND_PID" ]] || kill "$FRONTEND_PID" 2>/dev/null || true
  [[ -z "$BACKEND_PID" ]] || kill "$BACKEND_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

export LEASESHIELD_UPLOAD_DIR="$UPLOAD_DIR"
export CORS_ORIGINS="http://localhost:3000"
.venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000 >"$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!

backend_ready=false
for _ in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:8000/health >/dev/null; then backend_ready=true; break; fi
  sleep 1
done
$backend_ready || die "Backend did not become ready."

NEXT_PUBLIC_API_URL="http://localhost:8000" npm --prefix frontend run dev -- --port 3000 >"$LOG_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!

frontend_ready=false
for _ in $(seq 1 120); do
  if curl -fsS http://127.0.0.1:3000/upload >/dev/null; then frontend_ready=true; break; fi
  sleep 1
done
$frontend_ready || die "Frontend did not become ready."

printf 'Uploading synthetic lease to the audit API...\n'
HTTP_CODE="$(curl -sS -o "$LOG_DIR/audit.json" -w '%{http_code}' -F "file=@$ROOT/sample-commercial-lease-test.pdf;type=application/pdf" http://127.0.0.1:8000/api/audit || true)"
[[ "$HTTP_CODE" == "200" ]] || die "Audit endpoint returned HTTP $HTTP_CODE. See backend log above."

REPORT_ID="$(python3.11 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("report_id", ""))' "$LOG_DIR/audit.json")"
[[ -n "$REPORT_ID" ]] || die "Audit response did not include report_id."
curl -fsS "http://127.0.0.1:8000/api/report/$REPORT_ID" -o "$LOG_DIR/report.json" || die "Could not retrieve the generated report."
python3.11 - "$LOG_DIR/report.json" <<'PY'
import json, sys
report = json.load(open(sys.argv[1]))
assert report.get("report_id"), "missing report_id"
assert report.get("file_name") == "sample-commercial-lease-test.pdf", "unexpected file_name"
assert isinstance(report.get("risk_flags"), list), "risk_flags must be a list"
print(f"Report check passed: {len(report['risk_flags'])} risk flags, score {report['overall_risk_score']}/100")
PY

printf '\nSmoke test passed. Open http://localhost:3000/upload to use the GUI.\n'
printf 'The sample report is: http://localhost:3000/dashboard/%s\n' "$REPORT_ID"
if command -v open >/dev/null 2>&1; then open "http://localhost:3000/dashboard/$REPORT_ID"; fi
printf 'Press Ctrl+C here when finished; temporary test files are removed on exit.\n'
wait "$FRONTEND_PID"
