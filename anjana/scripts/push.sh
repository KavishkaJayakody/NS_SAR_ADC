#!/bin/bash

# ---- server config -------------------------------------------------------
SERVER_USER="${SERVER_USER:-user24}"          # change to user22 / user24 as needed
SERVER_HOST="${SERVER_HOST:-10.8.158.20}"
REMOTE="${SERVER_USER}@${SERVER_HOST}:/home/${SERVER_USER}/NS_SAR_ADC"
LOCAL=~/Workspace/Git/NS_SAR_ADC
# --------------------------------------------------------------------------

echo "Sending to Cadence server as ${SERVER_USER}..."

rsync -avz --exclude='*.cdslck*' --exclude='*.log*' --exclude='.git/' \
    "$LOCAL/" "$REMOTE/"
#rsync -avz --exclude='*.cdslck*' --exclude='*.log*' --exclude='.git/' \
#    "$LOCAL/libraries/NS_SAR_behavioural/" "$REMOTE/libraries/NS_SAR_behavioural/"

echo "Send complete!"
pw-play /usr/share/sounds/freedesktop/stereo/complete.oga 2>/dev/null || echo -e "\a"
