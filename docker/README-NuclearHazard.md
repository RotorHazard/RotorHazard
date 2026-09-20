# NuclearHazard Docker Setup

## Requirements

- Raspberry Pi 3, 4, or 5
- NuclearHazard timing board
- **External power supply for the NuclearHazard board** (USB power from the Pi alone is not sufficient)
- Docker installed on the Pi

## Quick start

On your Raspberry Pi, from the repo or any directory where you have the script:

```bash
./docker/scripts/run-prod-nuclear-pi.sh
```

Optional: pass a custom data directory (default is `./rh-data`):

```bash
./docker/scripts/run-prod-nuclear-pi.sh /path/to/rh-data
```

## What the script does

1. **First run:** Configures the Pi for NuclearHazard (serial, I2C, SPI, boot overlays, udev), pulls the Docker image, creates the container, and reboots.
2. **After reboot:** NuclearHazard starts automatically and keeps running (restart policy: unless-stopped).

No need to run the script again unless you want to change the data directory or re-run host setup.

## Access

After reboot:

- On the Pi: **http://localhost** or **http://localhost:5000**
- From another device: **http://\<pi-ip-address\>**

**Login:** `NuclearHazard` / `nuclearhazard`

---

## Troubleshooting

### Check if the container is running

```bash
docker ps
```

### View logs

```bash
docker logs -f nuclearhazard-server
```

### Restart

```bash
docker restart nuclearhazard-server
```

### Stop

```bash
docker stop nuclearhazard-server
```

### No nodes detected / can't communicate with processor

- **Power:** The NuclearHazard board needs an external power supply, not just USB from the Pi.
- Ensure the board is firmly seated on the GPIO header.
- Check logs for serial/port errors.

### Firmware flash fails

If automatic GPIO reset doesn’t work:

1. Stop the container: `docker stop nuclearhazard-server`
2. Power off the Pi.
3. Install the Boot0 jumper on the NuclearHazard board.
4. Power on the Pi.
5. Start the container: `docker start nuclearhazard-server`
6. Flash firmware via the web UI.
7. Power off, remove the Boot0 jumper, then power on again.

### GPIO errors on Pi 5

The container creates a `/dev/gpiochip4` symlink for Pi 5. If you see GPIO errors:

```bash
docker restart nuclearhazard-server
```

### Reset to a fresh state

```bash
docker rm -f nuclearhazard-server
sudo rm /etc/nuclearhazard-setup-complete
rm -rf ./rh-data
./docker/scripts/run-prod-nuclear-pi.sh
```

---

## Optional: WiFi hotspot

Automatic WiFi hotspot fallback (useful in the field):

```bash
./docker/scripts/setup-wifi-hotspot.sh
```

Then set your WiFi credentials:

```bash
nano ~/wifi_config.txt
```

- Line 1: WiFi SSID  
- Line 2: WiFi password  

On boot the Pi will:

1. Try to connect to the configured WiFi.
2. If that fails, start a hotspot:
   - SSID: `NuclearHazard`
   - Password: `nuclearhazard`

To disable the hotspot service:

```bash
sudo systemctl disable nuclearhazard-hotspot.service
```
