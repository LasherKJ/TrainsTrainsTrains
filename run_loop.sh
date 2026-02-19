#!/bin/bash
# Simple loop script to run MTA arrivals every N seconds
# Usage: ./run_loop.sh [seconds] (default: 30)

INTERVAL=${1:-30}  # Default to 30 seconds if no argument provided
PROJECT_DIR="/home/pi/mta-arrivals"  # Adjust path as needed
PYTHON_BIN="$PROJECT_DIR/.venv/bin/python"
SCRIPT="$PROJECT_DIR/mta_arrivals_single.py"

echo "Starting MTA arrivals monitoring (every $INTERVAL seconds)"
echo "Press Ctrl+C to stop"
echo "================================"

cd "$PROJECT_DIR"

while true; do
    echo ""
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Fetching arrivals..."
    $PYTHON_BIN "$SCRIPT"
    echo ""
    echo "Next update in $INTERVAL seconds..."
    sleep "$INTERVAL"
done