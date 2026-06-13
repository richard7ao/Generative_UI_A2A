#!/bin/bash
# Test runner for the A2A Customer Service Agent unit tests.
#
# Self-contained: builds an isolated venv with the cs_agent runtime deps + pytest
# the first time it runs, then executes the unit suite. Re-runs reuse the venv.
#   Usage:  bash tests/run_tests.sh
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV="$REPO_ROOT/.venv-test"

UNIT_TESTS=(
    "tests/test_intent_classification.py"
    "tests/test_circuit_breaker.py"
    "tests/test_query_expansion.py"
)

echo "=============================================="
echo "A2A Customer Service Agent - Test Suite"
echo "=============================================="

# 1. Build the test venv once (cs_agent deps are needed because the tests import
#    research_client_tool / rag_tools, which pull in a2a-sdk, google-adk, redis).
if [ ! -x "$VENV/bin/python" ]; then
    echo "Creating test venv at $VENV (first run only) ..."
    if command -v uv >/dev/null 2>&1; then
        uv venv "$VENV" --python 3.12 || exit 1
        uv pip install --python "$VENV" \
            -r "$REPO_ROOT/cs_agent/requirements.txt" pytest pytest-asyncio || exit 1
    else
        python3 -m venv "$VENV" || exit 1
        "$VENV/bin/pip" install -q \
            -r "$REPO_ROOT/cs_agent/requirements.txt" pytest pytest-asyncio || exit 1
    fi
fi

# 2. cs_agent uses flat sibling imports (env_toolset, circuit_breaker) while the
#    tests import them as `cs_agent.*`, so both the repo root and cs_agent/ must be
#    importable. ENV_API_* get harmless defaults for any module that reads them.
export PYTHONPATH="$REPO_ROOT:$REPO_ROOT/cs_agent"
export ENV_API_URL="${ENV_API_URL:-http://localhost:8090}"
export ENV_API_TOKEN="${ENV_API_TOKEN:-dev-agent-token}"

cd "$REPO_ROOT" || exit 1
"$VENV/bin/python" -m pytest "${UNIT_TESTS[@]}" -v --tb=short -p no:cacheprovider
RESULT=$?

echo "=============================================="
if [ $RESULT -eq 0 ]; then
    echo "ALL TESTS PASSED"
else
    echo "SOME TESTS FAILED (pytest exit $RESULT)"
fi
exit $RESULT
