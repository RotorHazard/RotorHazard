#!/bin/sh
set -e

CONFIG_FILE="/app/data/config.json"
MARKER_FILE="/app/data/.nh_initialized"

# Pi 5 GPIO fix: create gpiochip4 symlink if it doesn't exist
# (Docker passes the real device but not the symlink)
if [ -e /dev/gpiochip0 ] && [ ! -e /dev/gpiochip4 ]; then
    ln -sf /dev/gpiochip0 /dev/gpiochip4 2>/dev/null || true
fi

apply_nh_defaults() {
    if [ -f "$CONFIG_FILE" ] && [ ! -f "$MARKER_FILE" ]; then
        echo "Applying NuclearHazard defaults to config..."
        
        # Use sed to apply NuclearHazard branding and settings
        sed -i 's/"ADMIN_USERNAME": "admin"/"ADMIN_USERNAME": "NuclearHazard"/' "$CONFIG_FILE" 2>/dev/null || true
        sed -i 's/"ADMIN_PASSWORD": "rotorhazard"/"ADMIN_PASSWORD": "nuclearhazard"/' "$CONFIG_FILE" 2>/dev/null || true
        sed -i 's/"SHUTDOWN_BUTTON_GPIOPIN": 18/"SHUTDOWN_BUTTON_GPIOPIN": 19/' "$CONFIG_FILE" 2>/dev/null || true
        sed -i 's/"hue_0": "212"/"hue_0": "100"/' "$CONFIG_FILE" 2>/dev/null || true
        sed -i 's/"sat_0": "55"/"sat_0": "75"/' "$CONFIG_FILE" 2>/dev/null || true
        sed -i 's/"timerName": "RotorHazard"/"timerName": "NuclearHazard"/' "$CONFIG_FILE" 2>/dev/null || true
        sed -i 's/"LED_COUNT": 0/"LED_COUNT": 100/' "$CONFIG_FILE" 2>/dev/null || true
        
        touch "$MARKER_FILE"
        echo "NuclearHazard defaults applied."
    fi
}

if [ "${NH_FIRST_RUN:-0}" = "1" ]; then
    # Start server in background, wait for config to be created, apply defaults, then restart
    echo "First run mode: starting server to generate config..."
    python server.py --data /app/data &
    SERVER_PID=$!
    
    # Wait for config file to appear (max 30 seconds)
    WAIT_COUNT=0
    while [ ! -f "$CONFIG_FILE" ] && [ $WAIT_COUNT -lt 30 ]; do
        sleep 1
        WAIT_COUNT=$((WAIT_COUNT + 1))
    done
    
    if [ -f "$CONFIG_FILE" ]; then
        sleep 2  # Give it a moment to finish writing
        kill $SERVER_PID 2>/dev/null || true
        wait $SERVER_PID 2>/dev/null || true
        apply_nh_defaults
    fi
    
    echo "Starting NuclearHazard server..."
    exec python server.py --data /app/data
else
    # Normal startup - apply defaults if config exists but hasn't been initialized
    apply_nh_defaults
    exec python server.py --data /app/data
fi
