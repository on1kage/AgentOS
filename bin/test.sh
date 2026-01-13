#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

# Hermetic pytest: no third-party plugin autoload, no parent config discovery.
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
export PYTHONPATH="$(pwd)/src"

# Collect-only first: fail closed if zero tests are discovered.
collect_out="$(/usr/bin/python3 -m pytest -q -c /dev/null --rootdir="$(pwd)" --collect-only tests_hermetic 2>&1 || true)"

# Accept both:
# - "collected N item(s)"
# - "N test(s) collected"
collected_count="$(
  printf "%s\n" "$collect_out" | awk '
    /collected [0-9]+ item/ {print $2; exit}
    /^[0-9]+ test(s)? collected/ {print $1; exit}
  '
)"

if [ -z "${collected_count:-}" ]; then
  echo "ERROR: could not parse pytest collection output"
  echo "$collect_out"
  exit 2
fi

if [ "$collected_count" -eq 0 ]; then
  echo "ERROR: pytest collected 0 tests (fail-closed)"
  echo "$collect_out"
  exit 3
fi

exec /usr/bin/python3 -m pytest -q -c /dev/null --rootdir="$(pwd)" tests_hermetic
