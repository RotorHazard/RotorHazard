#!/usr/bin/env bash
# NuclearHazard WiFi Hotspot Setup (Optional)
# 
# This script sets up automatic WiFi hotspot fallback:
# - Tries to connect to a configured WiFi network on boot
# - If that fails, creates a hotspot for direct connection
#
# Usage: ./setup-wifi-hotspot.sh
#
# After running, edit /home/$USER/wifi_config.txt with your WiFi credentials.
# The hotspot will be created with SSID "NuclearHazard" and password "nuclearhazard"

set -e

# Check for root/sudo
if [ "$EUID" -ne 0 ]; then
    echo "This script requires root privileges."
    echo "Re-running with sudo..."
    exec sudo "$0" "$@"
fi

# Get the actual user (not root)
ACTUAL_USER="${SUDO_USER:-$USER}"
USER_HOME=$(eval echo ~$ACTUAL_USER)

echo "=============================================="
echo "NuclearHazard WiFi Hotspot Setup"
echo "=============================================="
echo ""

# Create the hotspot script
echo "Creating hotspot script..."
cat > "$USER_HOME/hotspot.sh" << 'HOTSPOT_SCRIPT'
#!/bin/bash

# WiFi Hotspot Fallback Script
# Tries to connect to configured WiFi, falls back to hotspot if it fails

WIFI_CONFIG_FILE="$HOME/wifi_config.txt"

# Read SSID and password from config file
if [ -f "$WIFI_CONFIG_FILE" ]; then
    SSID=$(awk "NR==1" "$WIFI_CONFIG_FILE")
    PASSWORD=$(awk "NR==2" "$WIFI_CONFIG_FILE")
else
    SSID=""
    PASSWORD=""
fi

# If no config or empty, go straight to hotspot
if [ -z "$SSID" ] || [ "$SSID" = "ssid" ]; then
    echo "No WiFi configured, starting hotspot..."
    nmcli dev wifi hotspot ifname wlan0 ssid "NuclearHazard" password "nuclearhazard"
    if [ $? -eq 0 ]; then
        echo "Hotspot created: SSID=NuclearHazard, Password=nuclearhazard"
    else
        echo "Failed to create hotspot."
        exit 1
    fi
    exit 0
fi

echo "Attempting to connect to WiFi: $SSID"

# Try to connect to the configured WiFi
if nmcli dev wifi connect "$SSID" password "$PASSWORD" ifname wlan0; then
    echo "Successfully connected to WiFi: $SSID"
    exit 0
else
    echo "Failed to connect to WiFi. Starting hotspot instead."
    nmcli dev wifi hotspot ifname wlan0 ssid "NuclearHazard" password "nuclearhazard"
    if [ $? -eq 0 ]; then
        echo "Hotspot created: SSID=NuclearHazard, Password=nuclearhazard"
    else
        echo "Failed to create hotspot."
        exit 1
    fi
fi
HOTSPOT_SCRIPT

chmod +x "$USER_HOME/hotspot.sh"
chown "$ACTUAL_USER:$ACTUAL_USER" "$USER_HOME/hotspot.sh"
echo "✓ Created $USER_HOME/hotspot.sh"

# Create default WiFi config file
if [ ! -f "$USER_HOME/wifi_config.txt" ]; then
    cat > "$USER_HOME/wifi_config.txt" << 'WIFI_CONFIG'
ssid
password
WIFI_CONFIG
    chown "$ACTUAL_USER:$ACTUAL_USER" "$USER_HOME/wifi_config.txt"
    echo "✓ Created $USER_HOME/wifi_config.txt (edit with your WiFi credentials)"
else
    echo "✓ WiFi config already exists: $USER_HOME/wifi_config.txt"
fi

# Create systemd service
echo "Creating systemd service..."
cat > /etc/systemd/system/nuclearhazard-hotspot.service << SYSTEMD_SERVICE
[Unit]
Description=NuclearHazard WiFi Hotspot Service
After=NetworkManager.service
Wants=NetworkManager.service

[Service]
Type=oneshot
ExecStartPre=/bin/sleep 15
ExecStart=$USER_HOME/hotspot.sh
User=$ACTUAL_USER
WorkingDirectory=$USER_HOME
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
SYSTEMD_SERVICE

echo "✓ Created systemd service"

# Enable the service
systemctl daemon-reload
systemctl enable nuclearhazard-hotspot.service
echo "✓ Enabled hotspot service"

echo ""
echo "=============================================="
echo "WiFi Hotspot Setup Complete!"
echo "=============================================="
echo ""
echo "IMPORTANT: Edit your WiFi credentials:"
echo "  nano $USER_HOME/wifi_config.txt"
echo ""
echo "  Line 1: Your WiFi SSID (network name)"
echo "  Line 2: Your WiFi password"
echo ""
echo "On boot, the Pi will:"
echo "  1. Try to connect to your configured WiFi"
echo "  2. If that fails, create a hotspot:"
echo "     SSID: NuclearHazard"
echo "     Password: nuclearhazard"
echo ""
echo "To disable: sudo systemctl disable nuclearhazard-hotspot.service"
echo "To test now: sudo $USER_HOME/hotspot.sh"
echo ""
