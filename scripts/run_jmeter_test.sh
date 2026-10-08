#!/usr/bin/env bash
# Run one JMeter open-loop load test configuration and save its .jtl under jmeter/results/.
#
# Usage: run_jmeter_test.sh <model_label> <rate_per_min> <duration_sec> <run_number>
# Example: run_jmeter_test.sh llama3.2_1b 30 90 1
set -euo pipefail

MODEL_LABEL="$1"
RATE="$2"
DURATION="$3"
RUN="$4"

JMETER_BIN="/c/Users/ryan/AppData/Local/Programs/Apache/apache-jmeter-5.6.3/bin/jmeter.bat"
JMX="jmeter/test_plans/ticket_triage_load_test.jmx"
OUT_DIR="jmeter/results"
OUT_BASE="${OUT_DIR}/${MODEL_LABEL}_rate${RATE}_run${RUN}"

mkdir -p "$OUT_DIR"
rm -f "${OUT_BASE}.jtl"

"$JMETER_BIN" -n \
  -t "$JMX" \
  -l "${OUT_BASE}.jtl" \
  -j "${OUT_BASE}.jmeter.log" \
  -JtargetThroughputPerMin="$RATE" \
  -JdurationSec="$DURATION" \
  -Jthreads=50 \
  -JnarrativesCsv=jmeter/test_plans/load_test_narratives.csv \
  -Jhost=localhost \
  -Jport=8000

echo "Wrote ${OUT_BASE}.jtl"
