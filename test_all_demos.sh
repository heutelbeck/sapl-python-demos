#!/usr/bin/env bash
# Run test_demo.sh against all 4 SAPL demos and collect comparative results.
#
# Prerequisites:
#   - Docker running (Keycloak + SAPL PDP shared across demos)
#   - Python venv at /tmp/sapl-venv with all deps installed
#   - NestJS demo built (npm run build in sapl-nestjs-demo)
#
# Usage:
#   ./test_all_demos.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NESTJS_DIR="/home/dominic/git/sapl-nestjs-demo"
VENV="/tmp/sapl-venv/bin"
PORT=3000
RESULTS_DIR="/tmp/sapl-test-results"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BOLD='\033[1m'
NC='\033[0m'

mkdir -p "$RESULTS_DIR"

kill_port() {
    lsof -ti:"$PORT" 2>/dev/null | xargs kill -9 2>/dev/null || true
    sleep 2
}

wait_for_server() {
    local url="$1"
    local max_wait="${2:-15}"
    local waited=0
    while ! curl -s --max-time 2 "$url" >/dev/null 2>&1; do
        sleep 1
        waited=$((waited + 1))
        if [[ $waited -ge $max_wait ]]; then
            echo "  ERROR: server not ready after ${max_wait}s"
            return 1
        fi
    done
}

# Ensure docker containers are running (Keycloak + PDP)
# The PDP uses whichever policies are mounted; since all Python demos
# have identical policies, we just need any one docker-compose running.
if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -q "sapl-pdp"; then
    echo "Starting docker containers from flask_demo..."
    cd "$SCRIPT_DIR/flask_demo" && docker compose up -d
    echo "Waiting 30s for Keycloak realm import..."
    sleep 30
fi

printf "\n${BOLD}========================================${NC}\n"
printf "${BOLD}  SAPL Demo Comparative Test Suite${NC}\n"
printf "${BOLD}========================================${NC}\n\n"

# ---- Flask ----
printf "${BOLD}[1/4] Flask Demo${NC}\n"
kill_port
cd "$SCRIPT_DIR/flask_demo" && "$VENV/python" app.py > /tmp/flask_demo.log 2>&1 &
wait_for_server "http://localhost:$PORT/api/hello"
cd "$SCRIPT_DIR" && bash test_demo.sh "http://localhost:$PORT" --jwt 2>&1 | tee "$RESULTS_DIR/flask.txt"
kill_port

# ---- FastAPI ----
printf "\n${BOLD}[2/4] FastAPI Demo${NC}\n"
cd "$SCRIPT_DIR/fastapi_demo" && "$VENV/python" -m app.main > /tmp/fastapi_demo.log 2>&1 &
wait_for_server "http://localhost:$PORT/api/hello"
cd "$SCRIPT_DIR" && bash test_demo.sh "http://localhost:$PORT" --jwt 2>&1 | tee "$RESULTS_DIR/fastapi.txt"
kill_port

# ---- Django ----
printf "\n${BOLD}[3/4] Django Demo${NC}\n"
cd "$SCRIPT_DIR/django_demo" && "$VENV/uvicorn" demo_project.asgi:application --host 0.0.0.0 --port "$PORT" > /tmp/django_demo.log 2>&1 &
wait_for_server "http://localhost:$PORT/api/hello"
cd "$SCRIPT_DIR" && bash test_demo.sh "http://localhost:$PORT" --jwt 2>&1 | tee "$RESULTS_DIR/django.txt"
kill_port

# ---- NestJS ----
printf "\n${BOLD}[4/4] NestJS Demo${NC}\n"
# NestJS needs its own PDP with its policies (missing permit-read-patients, permit-transfer)
# but the shared PDP has those policies which is fine -- extra policies don't hurt.
# NestJS uses a different Keycloak client_id.
cd "$NESTJS_DIR" && node dist/main > /tmp/nestjs_demo.log 2>&1 &
wait_for_server "http://localhost:$PORT/api/hello"
cd "$SCRIPT_DIR" && KEYCLOAK_CLIENT_ID=nestjs-app bash test_demo.sh "http://localhost:$PORT" --jwt 2>&1 | tee "$RESULTS_DIR/nestjs.txt"
kill_port

# ---- Comparative Summary ----
printf "\n${BOLD}========================================${NC}\n"
printf "${BOLD}  Comparative Summary${NC}\n"
printf "${BOLD}========================================${NC}\n\n"

printf "%-12s %s\n" "Demo" "Result"
printf "%-12s %s\n" "----" "------"
for demo in flask fastapi django nestjs; do
    result=$(grep "^Total:" "$RESULTS_DIR/${demo}.txt" 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g' || echo "no results")
    printf "%-12s %s\n" "$demo" "$result"
done

printf "\nDetailed results in: %s/\n" "$RESULTS_DIR"
