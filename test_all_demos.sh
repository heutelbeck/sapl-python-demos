#!/usr/bin/env bash
# Run test_demo.sh against all SAPL demos and collect comparative results.
#
# Prerequisites:
#   - Docker running (Keycloak + SAPL PDP shared across demos)
#   - Python venv at /tmp/sapl-venv with all deps installed
#   - NestJS demo built (npm run build in sapl-nestjs-demo)
#   - .NET 9 SDK available (via nix develop or directly)
#   - PHP 8.3+ and Composer, with sapl-php-demos dependencies installed
#     (composer install) and sapl-php available via the path repository
#
# Usage:
#   ./test_all_demos.sh

# Resilient run: a failed setup step for one demo must not abort the whole
# suite. Test-assertion failures already do not abort (test_demo.sh runs in a
# pipe). Each demo records its own result file; missing files surface as
# "no results" in the comparative summary.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_DIR="${PYTHON_DIR:-/home/dominic/git/sapl-python-demos}"
NESTJS_DIR="${NESTJS_DIR:-/home/dominic/git/sapl-nestjs-demo}"
DOTNET_DIR="${DOTNET_DIR:-/home/dominic/git/sapl-dotnet-demos}"
SPRING_DIR="${SPRING_DIR:-/home/dominic/git/sapl-demos/spring-demo}"
PHP_DIR="${PHP_DIR:-/home/dominic/git/sapl-php-demos}"
VENV="${VENV:-/tmp/sapl-venv/bin}"
PORT="${PORT:-3000}"
RESULTS_DIR="${RESULTS_DIR:-/tmp/sapl-test-results}"

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
    cd "$PYTHON_DIR/flask_demo" && docker compose up -d
    echo "Waiting 30s for Keycloak realm import..."
    sleep 30
fi

printf "\n${BOLD}========================================${NC}\n"
printf "${BOLD}  SAPL Demo Comparative Test Suite${NC}\n"
printf "${BOLD}========================================${NC}\n\n"

# ---- Flask ----
printf "${BOLD}[1/9] Flask Demo${NC}\n"
kill_port
cd "$PYTHON_DIR/flask_demo" && "$VENV/python" app.py > /tmp/flask_demo.log 2>&1 &
wait_for_server "http://localhost:$PORT/api/hello"
cd "$SCRIPT_DIR" && bash test_demo.sh "http://localhost:$PORT" --jwt 2>&1 | tee "$RESULTS_DIR/flask.txt"
kill_port

# ---- FastAPI ----
printf "\n${BOLD}[2/9] FastAPI Demo${NC}\n"
cd "$PYTHON_DIR/fastapi_demo" && "$VENV/python" -m app.main > /tmp/fastapi_demo.log 2>&1 &
wait_for_server "http://localhost:$PORT/api/hello"
cd "$SCRIPT_DIR" && bash test_demo.sh "http://localhost:$PORT" --jwt 2>&1 | tee "$RESULTS_DIR/fastapi.txt"
kill_port

# ---- Django ----
printf "\n${BOLD}[3/9] Django Demo${NC}\n"
cd "$PYTHON_DIR/django_demo" && "$VENV/uvicorn" demo_project.asgi:application --host 0.0.0.0 --port "$PORT" > /tmp/django_demo.log 2>&1 &
wait_for_server "http://localhost:$PORT/api/hello"
cd "$SCRIPT_DIR" && bash test_demo.sh "http://localhost:$PORT" --jwt 2>&1 | tee "$RESULTS_DIR/django.txt"
kill_port

# ---- Tornado ----
printf "\n${BOLD}[4/9] Tornado Demo${NC}\n"
cd "$PYTHON_DIR/tornado_demo" && "$VENV/python" app.py > /tmp/tornado_demo.log 2>&1 &
wait_for_server "http://localhost:$PORT/api/hello"
cd "$SCRIPT_DIR" && bash test_demo.sh "http://localhost:$PORT" --jwt 2>&1 | tee "$RESULTS_DIR/tornado.txt"
kill_port

# ---- NestJS (HTTP transport) ----
printf "\n${BOLD}[5/9] NestJS Demo (HTTP)${NC}\n"
# NestJS needs its own PDP with its policies (missing permit-read-patients, permit-transfer)
# but the shared PDP has those policies which is fine -- extra policies don't hurt.
cd "$NESTJS_DIR" && SAPL_TRANSPORT=http node dist/main > /tmp/nestjs_demo.log 2>&1 &
wait_for_server "http://localhost:$PORT/api/hello"
cd "$SCRIPT_DIR" && bash test_demo.sh "http://localhost:$PORT" --jwt 2>&1 | tee "$RESULTS_DIR/nestjs-http.txt"
kill_port

# ---- NestJS (RSocket transport) ----
printf "\n${BOLD}[6/9] NestJS Demo (RSocket)${NC}\n"
# Same demo, RSocket transport against the shared SAPL Node on its RSocket port.
cd "$NESTJS_DIR" && SAPL_TRANSPORT=rsocket SAPL_PDP_RSOCKET_HOST=localhost SAPL_PDP_RSOCKET_PORT=7000 node dist/main > /tmp/nestjs_rsocket_demo.log 2>&1 &
wait_for_server "http://localhost:$PORT/api/hello"
cd "$SCRIPT_DIR" && bash test_demo.sh "http://localhost:$PORT" --jwt 2>&1 | tee "$RESULTS_DIR/nestjs-rsocket.txt"
kill_port

# ---- .NET ----
printf "\n${BOLD}[7/9] .NET Demo${NC}\n"
DOTNET_CMD="dotnet"
if ! command -v dotnet &>/dev/null; then
    DOTNET_CMD="nix develop /home/dominic/.dotfiles#dotnet --command dotnet"
fi
$DOTNET_CMD build "$DOTNET_DIR/sapl-dotnet-demos.csproj" --verbosity quiet > /dev/null 2>&1
$DOTNET_CMD run --project "$DOTNET_DIR/sapl-dotnet-demos.csproj" --no-build > /tmp/dotnet_demo.log 2>&1 &
wait_for_server "http://localhost:$PORT/api/hello"
cd "$SCRIPT_DIR" && bash test_demo.sh "http://localhost:$PORT" --jwt 2>&1 | tee "$RESULTS_DIR/dotnet.txt"
kill_port

# ---- Spring (the reference implementation) ----
printf "\n${BOLD}[8/9] Spring Demo${NC}\n"
# Maven Spring Boot run binds to the configured server.port (default 8080 in the
# spring-demo profile). Override to PORT so the same test_demo.sh assertions apply.
cd "$SPRING_DIR" && SERVER_PORT="$PORT" SAPL_PDP_URL="http://localhost:8443" \
    mvn -q spring-boot:run > /tmp/spring_demo.log 2>&1 &
wait_for_server "http://localhost:$PORT/api/hello" 60
cd "$SCRIPT_DIR" && bash test_demo.sh "http://localhost:$PORT" --jwt 2>&1 | tee "$RESULTS_DIR/spring.txt"
# Spring boot:run via mvn does not expose a clean shutdown hook; use kill_port.
kill_port

# ---- PHP (Symfony) ----
printf "\n${BOLD}[9/9] PHP Demo (Symfony)${NC}\n"
# Symfony app served by the PHP built-in server with the front controller as
# router. Consumes the shared PDP over HTTP and the shared Keycloak for --jwt.
cd "$PHP_DIR" && SAPL_PDP_BASE_URL="http://localhost:8443" APP_ENV=dev \
    php -S 0.0.0.0:"$PORT" -t public public/index.php > /tmp/php_demo.log 2>&1 &
wait_for_server "http://localhost:$PORT/api/hello"
cd "$SCRIPT_DIR" && bash test_demo.sh "http://localhost:$PORT" --jwt 2>&1 | tee "$RESULTS_DIR/php.txt"
kill_port

# ---- Comparative Summary ----
printf "\n${BOLD}========================================${NC}\n"
printf "${BOLD}  Comparative Summary${NC}\n"
printf "${BOLD}========================================${NC}\n\n"

printf "%-12s %s\n" "Demo" "Result"
printf "%-12s %s\n" "----" "------"
for demo in flask fastapi django tornado nestjs-http nestjs-rsocket dotnet spring php; do
    result=$(grep "^Total:" "$RESULTS_DIR/${demo}.txt" 2>/dev/null | sed 's/\x1b\[[0-9;]*m//g' || echo "no results")
    printf "%-12s %s\n" "$demo" "$result"
done

printf "\nDetailed results in: %s/\n" "$RESULTS_DIR"
