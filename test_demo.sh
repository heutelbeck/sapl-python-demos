#!/usr/bin/env bash
# Universal test script for SAPL demos (FastAPI, Django, Flask, NestJS).
# Validates that all shared endpoints produce identical behavior.
#
# Usage:
#   ./test_demo.sh                              # default: http://localhost:3000
#   ./test_demo.sh http://localhost:8000         # custom base URL
#   ./test_demo.sh http://localhost:3000 --jwt   # include JWT export tests
#
# Requirements: curl, jq
#
# Note: There is no health-check test. If the server is unreachable,
# the first test (GET /api/hello) will fail and all subsequent tests
# will also fail -- making the root cause obvious.

set -euo pipefail

BASE_URL="${1:-http://localhost:3000}"
RUN_JWT=false
if [[ "${2:-}" == "--jwt" ]]; then
    RUN_JWT=true
fi

# Strip trailing slash
BASE_URL="${BASE_URL%/}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BOLD='\033[1m'
NC='\033[0m'

PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

pass() {
    PASS_COUNT=$((PASS_COUNT + 1))
    printf "${GREEN}PASS${NC} %s\n" "$1"
}

fail() {
    FAIL_COUNT=$((FAIL_COUNT + 1))
    printf "${RED}FAIL${NC} %s -- %s\n" "$1" "$2"
}

skip() {
    SKIP_COUNT=$((SKIP_COUNT + 1))
    printf "${YELLOW}SKIP${NC} %s -- %s\n" "$1" "$2"
}

# Helper: GET request, capture body + HTTP status
do_get() {
    local url="${BASE_URL}${1}"
    local response
    response=$(curl -s -w "\n%{http_code}" --max-time 10 "$url" 2>/dev/null) || {
        BODY=""
        HTTP_CODE="000"
        return
    }
    HTTP_CODE=$(echo "$response" | tail -1)
    BODY=$(echo "$response" | sed '$d')
}

# Helper: POST request
do_post() {
    local url="${BASE_URL}${1}"
    local response
    response=$(curl -s -w "\n%{http_code}" --max-time 10 -X POST "$url" 2>/dev/null) || {
        BODY=""
        HTTP_CODE="000"
        return
    }
    HTTP_CODE=$(echo "$response" | tail -1)
    BODY=$(echo "$response" | sed '$d')
}

# Helper: GET with auth header
do_get_auth() {
    local url="${BASE_URL}${1}"
    local token="$2"
    local response
    response=$(curl -s -w "\n%{http_code}" --max-time 10 -H "Authorization: Bearer ${token}" "$url" 2>/dev/null) || {
        BODY=""
        HTTP_CODE="000"
        return
    }
    HTTP_CODE=$(echo "$response" | tail -1)
    BODY=$(echo "$response" | sed '$d')
}

# Helper: SSE stream, capture first N seconds
do_sse() {
    local url="${BASE_URL}${1}"
    local timeout="${2:-3}"
    BODY=$(curl -s -N --max-time "$timeout" "$url" 2>/dev/null) || true
}

# Helper: check JSON field exists and optionally matches value
json_has() {
    local path="$1"
    local expected="${2:-}"
    local actual
    actual=$(echo "$BODY" | jq -r "$path" 2>/dev/null) || return 1
    if [[ "$actual" == "null" ]]; then
        return 1
    fi
    if [[ -n "$expected" && "$actual" != "$expected" ]]; then
        return 1
    fi
    return 0
}

# Helper: check JSON field contains substring
json_contains() {
    local path="$1"
    local substring="$2"
    local actual
    actual=$(echo "$BODY" | jq -r "$path" 2>/dev/null) || return 1
    if [[ "$actual" == *"$substring"* ]]; then
        return 0
    fi
    return 1
}

printf "${BOLD}SAPL Demo Test Suite${NC}\n"
printf "Target: %s\n\n" "$BASE_URL"

# ============================================================
# 1. Basic Authorization
# ============================================================
printf "${BOLD}--- Basic Authorization ---${NC}\n"

do_get "/api/hello"
if [[ "$HTTP_CODE" == "200" ]] && json_has ".message" "hello"; then
    pass "GET /api/hello -- manual PDP access"
else
    fail "GET /api/hello -- manual PDP access" "HTTP ${HTTP_CODE}"
fi

do_get "/api/patient/P-001"
if [[ "$HTTP_CODE" == "200" ]] && json_has ".name" "Jane Doe"; then
    if json_has ".ssn" "123-45-6789"; then
        fail "GET /api/patient/P-001 -- SSN blackened" "SSN not blackened: 123-45-6789"
    else
        pass "GET /api/patient/P-001 -- SSN blackened"
    fi
else
    fail "GET /api/patient/P-001 -- pre_enforce content filter" "HTTP ${HTTP_CODE}"
fi

do_get "/api/patients"
if [[ "$HTTP_CODE" == "200" ]]; then
    local_body="$BODY"
    arr_len=$(echo "$local_body" | jq 'length' 2>/dev/null) || arr_len=0
    if [[ "$arr_len" -ge 1 ]]; then
        first_ssn=$(echo "$local_body" | jq -r '.[0].ssn' 2>/dev/null)
        if [[ "$first_ssn" == "123-45-6789" ]]; then
            fail "GET /api/patients -- list SSN blackened" "SSN not blackened"
        else
            pass "GET /api/patients -- list SSN blackened"
        fi
    else
        fail "GET /api/patients -- list SSN blackened" "empty array"
    fi
else
    fail "GET /api/patients -- post_enforce" "HTTP ${HTTP_CODE}"
fi

do_post "/api/transfer?amount=8000"
if [[ "$HTTP_CODE" == "200" ]]; then
    transferred=$(echo "$BODY" | jq -r '.transferred' 2>/dev/null)
    if [[ "$transferred" == "5000" || "$transferred" == "5000.0" ]]; then
        pass "POST /api/transfer?amount=8000 -- capped to 5000"
    else
        fail "POST /api/transfer?amount=8000 -- amount capping" "got ${transferred}, expected 5000"
    fi
else
    fail "POST /api/transfer?amount=8000 -- argument manipulation" "HTTP ${HTTP_CODE}"
fi

# ============================================================
# 2. Constraint Handlers
# ============================================================
printf "\n${BOLD}--- Constraint Handlers ---${NC}\n"

do_get "/api/constraints/patient"
if [[ "$HTTP_CODE" == "200" ]] && json_has ".name"; then
    if json_has ".ssn" "123-45-6789"; then
        fail "GET /api/constraints/patient -- blacken" "SSN not blackened"
    else
        pass "GET /api/constraints/patient -- content filter blacken"
    fi
else
    fail "GET /api/constraints/patient" "HTTP ${HTTP_CODE}"
fi

do_get "/api/constraints/patient-full"
if [[ "$HTTP_CODE" == "200" ]]; then
    ssn_val=$(echo "$BODY" | jq -r '.ssn' 2>/dev/null)
    # Handle both snake_case (Python) and camelCase (NestJS) field names
    notes_val=$(echo "$BODY" | jq -r '.internal_notes // .internalNotes // "ABSENT"' 2>/dev/null)
    email_val=$(echo "$BODY" | jq -r '.email' 2>/dev/null)
    if [[ "$ssn_val" != "123-45-6789" && "$notes_val" == "ABSENT" && "$email_val" == "redacted@example.com" ]]; then
        pass "GET /api/constraints/patient-full -- all filter actions"
    else
        fail "GET /api/constraints/patient-full" "ssn=${ssn_val} notes=${notes_val} email=${email_val}"
    fi
else
    fail "GET /api/constraints/patient-full" "HTTP ${HTTP_CODE}"
fi

do_get "/api/constraints/logged"
if [[ "$HTTP_CODE" == "200" ]] && json_has ".message"; then
    pass "GET /api/constraints/logged -- runnable handler"
else
    fail "GET /api/constraints/logged" "HTTP ${HTTP_CODE}"
fi

do_get "/api/constraints/audited"
if [[ "$HTTP_CODE" == "200" ]] && json_has ".message"; then
    pass "GET /api/constraints/audited -- consumer handler"
else
    fail "GET /api/constraints/audited" "HTTP ${HTTP_CODE}"
fi

do_get "/api/constraints/audit-log"
if [[ "$HTTP_CODE" == "200" ]]; then
    arr_len=$(echo "$BODY" | jq 'length' 2>/dev/null) || arr_len=0
    if [[ "$arr_len" -ge 1 ]]; then
        pass "GET /api/constraints/audit-log -- non-empty"
    else
        fail "GET /api/constraints/audit-log" "empty audit log (call /audited first)"
    fi
else
    fail "GET /api/constraints/audit-log" "HTTP ${HTTP_CODE}"
fi

do_get "/api/constraints/redacted"
if [[ "$HTTP_CODE" == "200" ]]; then
    ssn_val=$(echo "$BODY" | jq -r '.ssn' 2>/dev/null)
    cc_val=$(echo "$BODY" | jq -r '.creditCard' 2>/dev/null)
    if [[ "$ssn_val" == "[REDACTED]" && "$cc_val" == "[REDACTED]" ]]; then
        pass "GET /api/constraints/redacted -- fields redacted"
    else
        fail "GET /api/constraints/redacted" "ssn=${ssn_val} creditCard=${cc_val}"
    fi
else
    fail "GET /api/constraints/redacted" "HTTP ${HTTP_CODE}"
fi

do_get "/api/constraints/documents"
if [[ "$HTTP_CODE" == "200" ]]; then
    classifications=$(echo "$BODY" | jq -r '.[].classification' 2>/dev/null | sort -u)
    if echo "$classifications" | grep -q "CONFIDENTIAL\|SECRET"; then
        fail "GET /api/constraints/documents" "contains CONFIDENTIAL or SECRET"
    else
        pass "GET /api/constraints/documents -- filtered by classification"
    fi
else
    fail "GET /api/constraints/documents" "HTTP ${HTTP_CODE}"
fi

do_get "/api/constraints/timestamped"
if [[ "$HTTP_CODE" == "200" ]]; then
    # Python uses policy_timestamp, NestJS uses policyTimestamp
    ts_val=$(echo "$BODY" | jq -r '.policy_timestamp // .policyTimestamp // "null"' 2>/dev/null)
    if [[ "$ts_val" != "not injected" && "$ts_val" != "null" ]]; then
        pass "GET /api/constraints/timestamped -- timestamp injected"
    else
        fail "GET /api/constraints/timestamped" "timestamp not injected: ${ts_val}"
    fi
else
    fail "GET /api/constraints/timestamped" "HTTP ${HTTP_CODE}"
fi

do_get "/api/constraints/error-demo"
if [[ "$HTTP_CODE" == "500" ]]; then
    if echo "$BODY" | grep -q "support.example.com"; then
        pass "GET /api/constraints/error-demo -- error pipeline (500 + support URL)"
    else
        pass "GET /api/constraints/error-demo -- error pipeline (500)"
    fi
else
    fail "GET /api/constraints/error-demo" "HTTP ${HTTP_CODE}, expected 500"
fi

# ============================================================
# 3. Advanced Patterns
# ============================================================
printf "\n${BOLD}--- Advanced Patterns ---${NC}\n"

do_get "/api/constraints/resource-replaced"
if [[ "$HTTP_CODE" == "200" ]]; then
    if json_has ".policyGenerated" "true" || json_has ".policyGenerated"; then
        pass "GET /api/constraints/resource-replaced -- PDP resource"
    else
        fail "GET /api/constraints/resource-replaced" "missing policyGenerated field"
    fi
else
    fail "GET /api/constraints/resource-replaced" "HTTP ${HTTP_CODE}"
fi

do_get "/api/constraints/advised"
if [[ "$HTTP_CODE" == "200" ]] && json_has ".message"; then
    pass "GET /api/constraints/advised -- advice (best-effort, 200 OK)"
else
    fail "GET /api/constraints/advised" "HTTP ${HTTP_CODE}, expected 200"
fi

do_get "/api/constraints/record/42"
if [[ "$HTTP_CODE" == "200" ]] && json_has ".id" "42"; then
    pass "GET /api/constraints/record/42 -- post_enforce with return value"
else
    fail "GET /api/constraints/record/42" "HTTP ${HTTP_CODE}"
fi

do_get "/api/constraints/unhandled"
if [[ "$HTTP_CODE" == "403" ]]; then
    pass "GET /api/constraints/unhandled -- unhandled obligation (403)"
else
    fail "GET /api/constraints/unhandled" "HTTP ${HTTP_CODE}, expected 403"
fi

# ============================================================
# 4. Streaming (SSE)
# ============================================================
printf "\n${BOLD}--- Streaming (SSE) ---${NC}\n"

# The streaming policy cycles PERMIT/DENY on a 20-second boundary:
#   seconds 0-19: PERMIT, 20-39: DENY, 40-59: PERMIT
# enforce_till_denied terminates on first DENY, so we wait until
# we're early in a PERMIT window to guarantee data.

SSE_TIMEOUT=25

wait_for_permit_window() {
    local sec
    sec=$(date +%S | sed 's/^0//')
    local waited=0
    while ! { [[ $sec -ge 0 && $sec -le 10 ]] || [[ $sec -ge 40 && $sec -le 50 ]]; }; do
        sleep 1
        waited=$((waited + 1))
        sec=$(date +%S | sed 's/^0//')
        if [[ $waited -ge 30 ]]; then
            break
        fi
    done
    if [[ $waited -gt 0 ]]; then
        printf "  (waited %ds for PERMIT window, now at second %d)\n" "$waited" "$sec"
    fi
}

# -- till-denied --
wait_for_permit_window
do_sse "/api/streaming/heartbeat/till-denied" "$SSE_TIMEOUT"
if echo "$BODY" | grep -q "^data:"; then
    data_count=$(echo "$BODY" | grep -c "^data:" || true)
    has_seq=$(echo "$BODY" | grep -c '"seq"' || true)
    has_denied=$(echo "$BODY" | grep -c 'ACCESS_DENIED' || true)
    if [[ "$has_seq" -ge 1 ]]; then
        if [[ "$has_denied" -ge 1 ]]; then
            pass "SSE /api/streaming/heartbeat/till-denied -- ${data_count} events, terminated by DENY"
        else
            pass "SSE /api/streaming/heartbeat/till-denied -- ${data_count} events (timeout before DENY)"
        fi
    else
        fail "SSE /api/streaming/heartbeat/till-denied" "got ${data_count} SSE lines but no heartbeat seq data"
    fi
else
    fail "SSE /api/streaming/heartbeat/till-denied" "no SSE data received in ${SSE_TIMEOUT}s"
fi

# -- drop-while-denied --
do_sse "/api/streaming/heartbeat/drop-while-denied" "$SSE_TIMEOUT"
if echo "$BODY" | grep -q "^data:"; then
    data_count=$(echo "$BODY" | grep -c "^data:" || true)
    pass "SSE /api/streaming/heartbeat/drop-while-denied -- ${data_count} events"
else
    fail "SSE /api/streaming/heartbeat/drop-while-denied" "no SSE data lines received in ${SSE_TIMEOUT}s"
fi

# -- recoverable --
do_sse "/api/streaming/heartbeat/recoverable" "$SSE_TIMEOUT"
if echo "$BODY" | grep -q "^data:"; then
    data_count=$(echo "$BODY" | grep -c "^data:" || true)
    has_suspended=$(echo "$BODY" | grep -c 'ACCESS_SUSPENDED' || true)
    has_restored=$(echo "$BODY" | grep -c 'ACCESS_RESTORED' || true)
    detail=""
    if [[ "$has_suspended" -ge 1 ]]; then
        detail="${detail}, saw SUSPENDED"
    fi
    if [[ "$has_restored" -ge 1 ]]; then
        detail="${detail}, saw RESTORED"
    fi
    pass "SSE /api/streaming/heartbeat/recoverable -- ${data_count} events${detail}"
else
    fail "SSE /api/streaming/heartbeat/recoverable" "no SSE data lines received in ${SSE_TIMEOUT}s"
fi

# ============================================================
# 5. Export (JWT) -- optional
# ============================================================
if [[ "$RUN_JWT" == "true" ]]; then
    printf "\n${BOLD}--- Export (JWT) ---${NC}\n"

    KEYCLOAK_URL="${KEYCLOAK_URL:-http://localhost:8080}"
    CLIENT_ID="${KEYCLOAK_CLIENT_ID:-flask-app}"
    CLIENT_SECRET="${KEYCLOAK_CLIENT_SECRET:-dev-secret}"

    TOKEN=$(curl -s -X POST "${KEYCLOAK_URL}/realms/demo/protocol/openid-connect/token" -H 'Content-Type: application/x-www-form-urlencoded' -d 'grant_type=password' -d "client_id=${CLIENT_ID}" -d "client_secret=${CLIENT_SECRET}" -d 'username=clinician1' -d 'password=password' --max-time 10 2>/dev/null | jq -r '.access_token // empty')

    if [[ -z "$TOKEN" ]]; then
        skip "Export tests" "could not get Keycloak token (is Keycloak running?)"
    else
        do_get_auth "/api/exportData/1/1" "$TOKEN"
        if [[ "$HTTP_CODE" == "200" ]] && json_has ".pilotId" "1"; then
            pass "GET /api/exportData/1/1 -- clinician1 own pilot (permitted)"
        else
            fail "GET /api/exportData/1/1 -- clinician1 own pilot" "HTTP ${HTTP_CODE}"
        fi

        do_get_auth "/api/exportData/2/1" "$TOKEN"
        if [[ "$HTTP_CODE" == "403" ]]; then
            pass "GET /api/exportData/2/1 -- clinician1 wrong pilot (403)"
        else
            fail "GET /api/exportData/2/1 -- clinician1 wrong pilot" "HTTP ${HTTP_CODE}, expected 403"
        fi
    fi
else
    printf "\n${BOLD}--- Export (JWT) ---${NC}\n"
    skip "Export tests" "pass --jwt flag to enable (requires running Keycloak)"
fi

# ============================================================
# 6. Service-Layer Enforcement
# ============================================================
printf "\n${BOLD}--- Service-Layer Enforcement ---${NC}\n"

do_get "/api/services/patients"
if [[ "$HTTP_CODE" == "200" ]]; then
    arr_len=$(echo "$BODY" | jq 'length' 2>/dev/null) || arr_len=0
    if [[ "$arr_len" -ge 1 ]]; then
        pass "GET /api/services/patients -- list patients (${arr_len} items)"
    else
        fail "GET /api/services/patients" "empty array"
    fi
else
    fail "GET /api/services/patients" "HTTP ${HTTP_CODE}"
fi

do_get "/api/services/patients/find?name=Jane"
if [[ "$HTTP_CODE" == "200" ]]; then
    arr_len=$(echo "$BODY" | jq 'length' 2>/dev/null) || arr_len=0
    if [[ "$arr_len" -ge 1 ]]; then
        pass "GET /api/services/patients/find?name=Jane -- found ${arr_len} patient(s)"
    else
        fail "GET /api/services/patients/find?name=Jane" "no results"
    fi
else
    fail "GET /api/services/patients/find?name=Jane" "HTTP ${HTTP_CODE}"
fi

do_get "/api/services/patients/search?q=healthy"
if [[ "$HTTP_CODE" == "200" ]]; then
    arr_len=$(echo "$BODY" | jq 'length' 2>/dev/null) || arr_len=0
    if [[ "$arr_len" -ge 1 ]]; then
        # search-patients policy filters by classification (maxLevel=INTERNAL)
        classifications=$(echo "$BODY" | jq -r '.[].classification' 2>/dev/null | sort -u)
        if echo "$classifications" | grep -q "CONFIDENTIAL\|SECRET"; then
            fail "GET /api/services/patients/search" "contains CONFIDENTIAL or SECRET"
        else
            pass "GET /api/services/patients/search?q=healthy -- filtered (${arr_len} results)"
        fi
    else
        fail "GET /api/services/patients/search?q=healthy" "no results"
    fi
else
    fail "GET /api/services/patients/search?q=healthy" "HTTP ${HTTP_CODE}"
fi

do_get "/api/services/patients/P-001"
if [[ "$HTTP_CODE" == "200" ]] && json_has ".name" "Jane Doe"; then
    # patient-detail policy blackens SSN
    if json_has ".ssn" "123-45-6789"; then
        fail "GET /api/services/patients/P-001 -- SSN blackened" "SSN not blackened"
    else
        pass "GET /api/services/patients/P-001 -- detail with SSN blackened"
    fi
else
    fail "GET /api/services/patients/P-001" "HTTP ${HTTP_CODE}"
fi

do_get "/api/services/patients/P-001/summary"
if [[ "$HTTP_CODE" == "200" ]] && json_has ".name" "Jane Doe"; then
    # patient-summary policy redacts SSN and insurance
    ssn_val=$(echo "$BODY" | jq -r '.ssn' 2>/dev/null)
    ins_val=$(echo "$BODY" | jq -r '.insurance' 2>/dev/null)
    if [[ "$ssn_val" == "[REDACTED]" && "$ins_val" == "[REDACTED]" ]]; then
        pass "GET /api/services/patients/P-001/summary -- fields redacted"
    else
        fail "GET /api/services/patients/P-001/summary" "ssn=${ssn_val} insurance=${ins_val}"
    fi
else
    fail "GET /api/services/patients/P-001/summary" "HTTP ${HTTP_CODE}"
fi

do_post "/api/services/transfer?amount=8000"
if [[ "$HTTP_CODE" == "200" ]]; then
    transferred=$(echo "$BODY" | jq -r '.transferred' 2>/dev/null)
    if [[ "$transferred" == "5000" || "$transferred" == "5000.0" ]]; then
        pass "POST /api/services/transfer?amount=8000 -- capped to 5000"
    else
        fail "POST /api/services/transfer?amount=8000" "got ${transferred}, expected 5000"
    fi
else
    fail "POST /api/services/transfer?amount=8000" "HTTP ${HTTP_CODE}"
fi

# ============================================================
# Summary
# ============================================================
printf "\n${BOLD}--- Summary ---${NC}\n"
TOTAL=$((PASS_COUNT + FAIL_COUNT + SKIP_COUNT))
printf "Total: %d | ${GREEN}Passed: %d${NC} | ${RED}Failed: %d${NC} | ${YELLOW}Skipped: %d${NC}\n" \
    "$TOTAL" "$PASS_COUNT" "$FAIL_COUNT" "$SKIP_COUNT"

if [[ "$FAIL_COUNT" -gt 0 ]]; then
    exit 1
fi
