#!/bin/bash
# Double-click this file in Finder to run the Track B prototype.
# It runs the tests, rebuilds dashboard.html, and opens it in your browser.

cd "$(dirname "$0")" || exit 1

echo "Track B: Manufacturing Intelligence Prototype"
echo "============================================="

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 was not found. Install it from https://www.python.org/downloads/ and run this again."
  read -n 1 -s -r -p "Press any key to close..."
  exit 1
fi

echo
echo "1. Running checks..."
if python3 -m unittest test_analysis; then
  echo "   All checks passed."
else
  echo "   Some checks failed. The dashboard will still be built, but review the errors above."
fi

echo
echo "2. Printing KPIs..."
python3 analysis.py

echo
echo "3. Building dashboard.html..."
python3 build_dashboard.py

echo
echo "4. Opening the dashboard..."
open dashboard.html

echo
read -n 1 -s -r -p "Done. Press any key to close this window..."
echo
