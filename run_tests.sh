#!/data/data/com.termux/files/usr/bin/bash
set -e
echo "STEP 1/2: Python unit tests (test_broker.py)"
echo "  └─ 1.1/2: Running broker unit tests"
python3 /root/forex-grid/test_broker.py || true
echo ""
echo "STEP 2/2: Playwright UI tests (pw-test.mjs)"
echo "  └─ 2.1/2: Running Playwright tests"
cd /root/playwright-test && node pw-test.mjs 2>&1 || true
echo ""
echo "Done"
