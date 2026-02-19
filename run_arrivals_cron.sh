#!/bin/bash
# Cron job script to run MTA arrivals every 30 seconds

# Add this to your crontab to run every minute:
# * * * * * /home/pi/mta-arrivals/run_arrivals_cron.sh

# Path to your project
PROJECT_DIR="/home/pi/mta-arrivals"
PYTHON_BIN="$PROJECT_DIR/.venv/bin/python"
SCRIPT="$PROJECT_DIR/mta_arrivals_single.py"
LOG_FILE="$PROJECT_DIR/arrivals.log"

# Run the script and log output with timestamp
echo "$(date): Running MTA arrivals check" >> "$LOG_FILE"
cd "$PROJECT_DIR"
$PYTHON_BIN "$SCRIPT" >> "$LOG_FILE" 2>&1