#!/usr/bin/env bash
# NuclearHazard Docker Setup & Run Script
# Usage: ./run-prod-nuclear-pi.sh [DATA_DIR]
#
# This script automatically:
#   1. Checks if Pi host setup is complete
#   2. If not, configures the Pi and reboots (run script again after reboot)
#   3. If yes, starts the NuclearHazard Docker container
#
# DATA_DIR defaults to ./rh-data

set -e

IMAGE="${IMAGE:-racefpv/rotorhazard-nuclearpi:latest}"
DATA_DIR="${1:-./rh-data}"
BOOT_CONFIG="/boot/firmware/config.txt"
UDEV_RULE="/etc/udev/rules.d/99-serial0-fix.rules"
SETUP_MARKER="/etc/nuclearhazard-setup-complete"

# Detect Pi model
detect_pi_model() {
    if grep -q "Raspberry Pi 5" /proc/cpuinfo 2>/dev/null; then
        echo "pi5"
    elif grep -q "Raspberry Pi 4" /proc/cpuinfo 2>/dev/null; then
        echo "pi4"
    elif grep -q "Raspberry Pi 3" /proc/cpuinfo 2>/dev/null; then
        echo "pi3"
    elif grep -q "Raspberry Pi Zero 2" /proc/cpuinfo 2>/dev/null; then
        echo "pi02"
    else
        echo "unknown"
    fi
}

# Check if host setup is complete
check_setup_complete() {
    # Check for our setup marker file
    if [ -f "$SETUP_MARKER" ]; then
        return 0
    fi
    
    # Also check if key indicators exist (in case marker was deleted)
    if [ -f "$UDEV_RULE" ] && grep -q "dtparam=i2c_baudrate=75000" "$BOOT_CONFIG" 2>/dev/null; then
        # Setup was done but marker missing, recreate it
        sudo touch "$SETUP_MARKER"
        return 0
    fi
    
    return 1
}

# Perform one-time host setup
do_host_setup() {
    echo "=============================================="
    echo "NuclearHazard Pi Host Setup"
    echo "=============================================="
    echo ""
    
    PI_MODEL=$(detect_pi_model)
    echo "Detected: Raspberry Pi model '$PI_MODEL'"
    echo ""
    
    # Check for root/sudo
    if [ "$EUID" -ne 0 ]; then
        echo "This setup requires root privileges."
        echo "Re-running with sudo..."
        exec sudo "$0" "$@"
    fi
    
    echo "Configuring hardware interfaces..."
    
    # Enable serial, I2C, SPI via raspi-config
    raspi-config nonint do_serial_hw 0
    raspi-config nonint do_serial_cons 1
    raspi-config nonint do_i2c 0
    raspi-config nonint do_spi 0
    
    echo "✓ Serial, I2C, SPI enabled"
    
    # Add boot config overlays if not present
    if ! grep -q "# NuclearHazard Config" "$BOOT_CONFIG" 2>/dev/null; then
        echo "" >> "$BOOT_CONFIG"
        echo "# NuclearHazard Config" >> "$BOOT_CONFIG"
        echo "dtparam=i2c_baudrate=75000" >> "$BOOT_CONFIG"
        echo "dtoverlay=act-led,gpio=24" >> "$BOOT_CONFIG"
        echo "dtoverlay=gpio-led,gpio=26,label=pwrled,trigger=default-on" >> "$BOOT_CONFIG"
        echo "dtparam=act_led_trigger=heartbeat" >> "$BOOT_CONFIG"
        
        # Add Pi-specific overlays
        case "$PI_MODEL" in
            pi5)
                echo "" >> "$BOOT_CONFIG"
                echo "[pi5]" >> "$BOOT_CONFIG"
                echo "dtoverlay=uart0-pi5" >> "$BOOT_CONFIG"
                echo "dtoverlay=i2c1-pi5" >> "$BOOT_CONFIG"
                ;;
            pi4)
                echo "" >> "$BOOT_CONFIG"
                echo "[pi4]" >> "$BOOT_CONFIG"
                echo "dtoverlay=gpio-shutdown,gpio_pin=19,debounce=5000" >> "$BOOT_CONFIG"
                ;;
            pi3|pi02)
                echo "" >> "$BOOT_CONFIG"
                echo "[$PI_MODEL]" >> "$BOOT_CONFIG"
                echo "dtoverlay=gpio-shutdown,gpio_pin=19,debounce=5000" >> "$BOOT_CONFIG"
                echo "core_freq=250" >> "$BOOT_CONFIG"
                ;;
        esac
        
        echo "" >> "$BOOT_CONFIG"
        echo "[all]" >> "$BOOT_CONFIG"
        echo "# End NuclearHazard Config" >> "$BOOT_CONFIG"
        
        echo "✓ Boot config overlays added"
    else
        echo "✓ Boot config already configured"
    fi
    
    # Create udev rule for serial symlink
    if [ ! -f "$UDEV_RULE" ]; then
        echo 'SUBSYSTEM=="tty", KERNEL=="ttyAMA0", SYMLINK+="serial0"' > "$UDEV_RULE"
        udevadm control --reload-rules
        udevadm trigger
        echo "✓ Serial udev rule created"
    else
        echo "✓ Serial udev rule exists"
    fi
    
    # Create setup marker
    touch "$SETUP_MARKER"
    
    echo ""
    echo "=============================================="
    echo "Setting up Docker container for auto-start"
    echo "=============================================="
    echo ""
    
    # Pull the Docker image now so it's ready after reboot
    echo "Pulling NuclearHazard Docker image..."
    docker pull "$IMAGE"
    echo "✓ Docker image pulled"
    
    # Create data directory
    mkdir -p "${DATA_DIR}"
    
    # Remove existing container if present
    if docker ps -a --format '{{.Names}}' | grep -q '^nuclearhazard-server$'; then
        docker rm -f nuclearhazard-server 2>/dev/null || true
    fi
    
    # Create and start the container (it will auto-restart after reboot)
    echo "Creating Docker container..."
    
    # Build device mount args (only mount devices that exist)
    DEVICE_MOUNTS=""
    for dev in /dev/gpiochip* /dev/gpiomem /dev/mem /dev/i2c-* /dev/spidev* /dev/ttyAMA0 /dev/serial0; do
        [ -e "$dev" ] && DEVICE_MOUNTS="$DEVICE_MOUNTS --device=$dev"
    done
    
    # Get gpio group ID if it exists
    GPIO_GID=$(getent group gpio 2>/dev/null | cut -d: -f3 || echo "")
    GROUP_ADD=""
    [ -n "$GPIO_GID" ] && GROUP_ADD="--group-add $GPIO_GID"
    
    docker run -d \
        --name nuclearhazard-server \
        --restart unless-stopped \
        -p 80:5000 \
        -p 5000:5000 \
        -v "${DATA_DIR}:/app/data" \
        -v /proc/device-tree:/proc/device-tree:ro \
        -v /sys:/sys \
        -v /run/udev:/run/udev:ro \
        $DEVICE_MOUNTS \
        $GROUP_ADD \
        -e RH_DATA_DIR=/app/data \
        -e NH_FIRST_RUN=1 \
        --privileged \
        "$IMAGE"
    
    echo "✓ Docker container created (will auto-start after reboot)"
    
    echo ""
    echo "=============================================="
    echo "SETUP COMPLETE - REBOOTING"
    echo "=============================================="
    echo ""
    echo "After reboot, NuclearHazard will start automatically!"
    echo ""
    echo "  URL:          http://localhost (also :5000)"
    echo "  Credentials:  NuclearHazard / nuclearhazard"
    echo ""
    echo "No need to run this script again."
    echo ""
    echo "Rebooting in 10 seconds... (Ctrl+C to cancel)"
    echo ""
    
    sleep 10
    reboot
}

# Run Docker container
run_docker() {
    echo "=============================================="
    echo "Starting NuclearHazard Docker Container"
    echo "=============================================="
    echo ""
    
    # Create data directory if it doesn't exist
    mkdir -p "${DATA_DIR}"
    
    # Check for first run to enable config initialization
    if [ ! -f "${DATA_DIR}/.nh_initialized" ]; then
        echo "First run detected - NuclearHazard defaults will be applied"
        FIRST_RUN=1
    else
        FIRST_RUN=0
    fi
    
    # Stop and remove existing container if present
    if docker ps -a --format '{{.Names}}' | grep -q '^nuclearhazard-server$'; then
        echo "Removing existing container..."
        docker stop nuclearhazard-server 2>/dev/null || true
        docker rm nuclearhazard-server 2>/dev/null || true
    fi
    
    # Build device mount args (only mount devices that exist)
    DEVICE_MOUNTS=""
    for dev in /dev/gpiochip* /dev/gpiomem /dev/mem /dev/i2c-* /dev/spidev* /dev/ttyAMA0 /dev/serial0; do
        [ -e "$dev" ] && DEVICE_MOUNTS="$DEVICE_MOUNTS --device=$dev"
    done
    
    # Get gpio group ID if it exists
    GPIO_GID=$(getent group gpio 2>/dev/null | cut -d: -f3 || echo "")
    GROUP_ADD=""
    [ -n "$GPIO_GID" ] && GROUP_ADD="--group-add $GPIO_GID"
    
    docker run -d \
        --name nuclearhazard-server \
        --restart unless-stopped \
        -p 80:5000 \
        -p 5000:5000 \
        -v "${DATA_DIR}:/app/data" \
        -v /proc/device-tree:/proc/device-tree:ro \
        -v /sys:/sys \
        -v /run/udev:/run/udev:ro \
        $DEVICE_MOUNTS \
        $GROUP_ADD \
        -e RH_DATA_DIR=/app/data \
        -e NH_FIRST_RUN="${FIRST_RUN}" \
        --privileged \
        "$IMAGE"
    
    echo ""
    echo "=============================================="
    echo "NuclearHazard is running!"
    echo "=============================================="
    echo ""
    echo "  URL:          http://localhost (also :5000)"
    echo "  Data:         ${DATA_DIR}"
    echo "  Credentials:  NuclearHazard / nuclearhazard"
    echo ""
    echo "Commands:"
    echo "  View logs:    docker logs -f nuclearhazard-server"
    echo "  Stop:         docker stop nuclearhazard-server"
    echo "  Restart:      docker restart nuclearhazard-server"
    echo "  Remove:       docker rm -f nuclearhazard-server"
    echo ""
}

# Main logic
main() {
    echo ""
    
    # Check if we're on a Raspberry Pi
    if [ ! -f /proc/cpuinfo ] || ! grep -q "Raspberry Pi\|BCM" /proc/cpuinfo 2>/dev/null; then
        echo "Warning: This doesn't appear to be a Raspberry Pi."
        echo "NuclearHazard is designed for Pi hardware."
        echo ""
    fi
    
    if check_setup_complete; then
        echo "✓ Host setup complete"
        run_docker
    else
        echo "Host setup not complete - starting one-time configuration..."
        echo ""
        do_host_setup
    fi
}

main "$@"
