#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT_DIR"

cmake -S unit_tests -B build/tests -DCMAKE_BUILD_TYPE=Debug -DENABLE_COVERAGE=ON
cmake --build build/tests
ctest --test-dir build/tests --output-on-failure

mkdir -p coverage

gcovr -r . \
  --filter "components/.*" \
  --exclude "unit_tests/.*" \
  --exclude "components/vehicle_comms/toyota_prius_2010_pt.c" \
  --html-details --html coverage/coverage.html \
  --xml-pretty --xml coverage/coverage.xml \
  --txt coverage/coverage.txt

echo "Coverage reports written to coverage"
