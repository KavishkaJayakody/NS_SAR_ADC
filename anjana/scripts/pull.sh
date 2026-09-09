#!/bin/bash

# ---- server config -------------------------------------------------------
SERVER_USER="${SERVER_USER:-user23}"          # change to user22 / user24 as needed
SERVER_HOST="${SERVER_HOST:-10.8.158.20}"
REMOTE="${SERVER_USER}@${SERVER_HOST}:/home/${SERVER_USER}/NS_SAR_ADC"
LOCAL=~/Workspace/Git/NS_SAR_ADC
# --------------------------------------------------------------------------

echo "Starting sync from Cadence server as ${SERVER_USER}..."

rsync -avz --exclude='*.cdslck*' --exclude='*.log*' --exclude='.git' \
    "$REMOTE/libraries/" "$LOCAL/libraries/"

rsync -avz --exclude='*.cdslck*' --exclude='*.log*' --exclude='.git' \
    "$REMOTE/simulation/adc_output.csv" "$LOCAL/simulation/adc_output.csv"

# rsync -avz --exclude='*.cdslck*' --exclude='*.log*' --exclude='.git' \
#     "$REMOTE/doc/" "$LOCAL/doc/"

echo "Sync complete!"

pw-play /usr/share/sounds/freedesktop/stereo/complete.oga 2>/dev/null || echo -e "\a"


echo "Running CSV benchmark..."
# python3 "$LOCAL/scripts/csv_benchmark.py"
