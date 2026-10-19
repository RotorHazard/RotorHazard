#!/usr/bin/env sh
# Run production image on macOS with a serial device (e.g. timing Arduino) that
# was attached via USB/IP. Use this only after you have exported the device from
# the Mac with a USB/IP server (e.g. pyusbip) and attached it inside Docker so
# it appears as /dev/ttyACM0 or /dev/ttyUSB0. See docker/README.md § "Using the
# timing hardware with Docker on Mac (USB/IP)".
#
# Usage: ./run-prod-mac-usb.sh SERIAL_DEVICE [DATA_DIR]
#   SERIAL_DEVICE  Device node inside Docker after usbip attach (e.g. /dev/ttyACM0)
#   DATA_DIR       Defaults to ./data
#
# Example: ./run-prod-mac-usb.sh /dev/ttyACM0
#          ./run-prod-mac-usb.sh /dev/ttyUSB0 /path/to/data

set -e
if [ -z "${1:-}" ]; then
    echo "Usage: $0 SERIAL_DEVICE [DATA_DIR]"
    echo "  SERIAL_DEVICE  e.g. /dev/ttyACM0 (device visible in Docker after usbip attach)"
    echo "  DATA_DIR       defaults to ./data"
    echo ""
    echo "See docker/README.md for USB/IP setup on macOS."
    exit 1
fi

SERIAL_DEVICE="$1"
DATA_DIR="${2:-./data}"
IMAGE="${IMAGE:-racefpv/rotorhazard:latest}"

docker run -d \
  --name rotorhazard-server \
  --restart unless-stopped \
  -p 5000:5000 \
  -v "${DATA_DIR}:/app/data" \
  -e RH_DATA_DIR=/app/data \
  --privileged \
  --device "${SERIAL_DEVICE}" \
  "$IMAGE"

echo "RotorHazard running at http://localhost:5000 (data: ${DATA_DIR}, serial: ${SERIAL_DEVICE})"
echo "Keep the container where you ran 'usbip attach' running so the device stays available."
