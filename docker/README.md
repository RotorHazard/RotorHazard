# RotorHazard Docker

## Local development (build from source)

Builds from source so you don’t need to pull from a registry.

From `docker/`:

```bash
docker-compose up -d
```

Uses a **named volume** (`rotorhazard-dev-data`) so the repo has no data directory and personal data isn’t committed. To wipe dev data: `docker volume rm rotorhazard-dev-data` (after stopping the container).

## Production (pre-built image)

Pull and run the image from your registry (e.g. on a server or Pi without the repo):

```bash
docker pull <your-registry>/rotorhazard:latest
```

**Using the run script** (recommended; set `IMAGE` if your tag differs):

```bash
chmod +x docker/scripts/run-prod.sh
./docker/scripts/run-prod.sh              # data dir: ./data
./docker/scripts/run-prod.sh /path/to/data # custom data dir
```

**Or run the container directly:**

```bash
docker run -d --name rotorhazard-server --restart unless-stopped \
  -p 5000:5000 -v ./data:/app/data -e RH_DATA_DIR=/app/data \
  --privileged <your-registry>/rotorhazard:latest
```

### USB/serial (timing hardware) and macOS

Docker Desktop on **macOS** runs containers inside a Linux VM, so the VM does **not** see the Mac’s USB devices directly. You have two options:

- **Recommended!! (simplest):** Run RotorHazard **natively** on the Mac (no Docker) when you need the timing Arduino. Use Docker on Mac only for UI-only or testing without hardware.
- **Experimental (Docker + USB on Mac):** Docker Desktop **4.35.0+** supports **USB/IP**, so the container can use USB devices that are exported from the host over the network. This can work for the timing serial device on Mac if you run a USB/IP server on the Mac and attach the device inside Docker. See [Using the timing hardware with Docker on Mac (USB/IP)](#using-the-timing-hardware-with-docker-on-mac-usbip) below.

On **Linux, WSL, or Windows**, the same container can access USB serial when run with `--privileged` or with explicit `--device` flags; no USB/IP is required.

---

### Using the timing hardware with Docker on Mac (USB/IP)

This is optional and experimental. You need **Docker Desktop 4.35.0 or newer**.

1. **Export the Arduino from the Mac with a USB/IP server**  
   The Mac must run a USB/IP server that shares the USB‑serial device. Open-source options:
   - **[pyusbip](https://github.com/tumayt/pyusbip)** (Python) – reported to work with USB‑serial (e.g. CP2102) on macOS.  
     ```bash
     git clone https://github.com/tumayt/pyusbip && cd pyusbip
     python3 -m venv .venv && source .venv/bin/activate
     pip install libusb1
     python pyusbip   # then bind/share your Arduino (see project README)
     ```
   - The Rust-based [jiegec/usbip](https://github.com/jiegec/usbip) does **not** support USB‑to‑serial on macOS.

2. **Attach the device inside Docker**  
   In a **privileged** container that can see the host, attach the device so it appears in the Docker VM (e.g. as `/dev/ttyACM0` or `/dev/ttyUSB0`):
   - Use Docker’s [USB/IP instructions](https://docs.docker.com/desktop/features/usbip/) (privileged container, `nsenter`, `usbip list -r host.docker.internal`, then `usbip attach -r host.docker.internal -b <BUSID>`).
   - Or use a “device manager” image such as [jonathanberi/devmgr](https://hub.docker.com/r/jonathanberi/devmgr) and attach the device there; keep that container running.

3. **Run RotorHazard with the serial device**  
   Once the device is attached, it appears as a normal device in the Docker VM. You can use the helper script (pass the device name you see after attach), or run `docker run` yourself:
   ```bash
   chmod +x docker/scripts/run-prod-mac-usb.sh
   ./docker/scripts/run-prod-mac-usb.sh /dev/ttyACM0              # data dir ./data
   ./docker/scripts/run-prod-mac-usb.sh /dev/ttyUSB0 /path/to/data
   ```
   Or manually:
   ```bash
   docker run -d --name rotorhazard-server --restart unless-stopped \
     -p 5000:5000 -v ./data:/app/data -e RH_DATA_DIR=/app/data \
     --privileged --device /dev/ttyACM0 \
     <your-registry>/rotorhazard:latest
   ```
   Use the actual device name you see after attach (e.g. `ttyACM0` or `ttyUSB0`). The container that performed `usbip attach` must stay running.

**Caveats:** macOS USB/IP servers are incomplete; not all USB‑serial adapters may work. If this path fails, use a native Mac install for timing hardware. For a supported, cross‑platform USB‑over‑IP solution (including serial), commercial options such as [VirtualHere](https://www.virtualhere.com/) exist.

**References:** [Docker: Using USB/IP](https://docs.docker.com/desktop/features/usbip/), [Golioth: USB with Docker on Windows and macOS](https://blog.golioth.io/usb-docker-windows-macos/).

---

## Image build design

Images are layered so the main Dockerfile is the base and Pi/NuclearHazard variants extend it:

| Layer | Image | Dockerfile | Description |
|-------|--------|------------|-------------|
| Base | (internal stage) | `Dockerfile` (target: `base`) | Common app layout + system deps, no Python deps |
| Default | `rotorhazard:latest` | `Dockerfile` | x64/amd64, uses `reqsNonPi.txt` |
| Pi | `rotorhazard-pi:latest` | `Dockerfile.pi` | arm64, FROM base + Pi requirements + GPIO/LED/VRxC |
| NuclearHazard | `rotorhazard-nuclearpi:latest` | `Dockerfile.nuclearpi` | arm64, FROM Pi + entrypoint + NuclearHazard defaults |

- **Dockerfile**: Defines the `base` stage (shared app copy, no pip) and the `default` stage (non-Pi server). Default build target is the final stage.
- **Dockerfile.pi**: `FROM` the base image; adds Pi-specific apt/pip and same CMD.
- **Dockerfile.nuclearpi**: `FROM` the Pi image; adds `nh_entrypoint.sh`, `NH_FIRST_RUN`, and ENTRYPOINT only.

## Build (and optionally push) images

From **repo root**. The script builds the base image when building Pi or NuclearHazard, then builds in order: rotorhazard (default) → pi → nuclearpi.

**Default: build only** (no push), so it works without registry access. Use `--push` to push after building; set `IMAGE_PREFIX` (e.g. your Docker Hub username) when pushing.

```bash
./docker/scripts/build-and-push.sh              # build all, load locally
./docker/scripts/build-and-push.sh --push       # build and push (set IMAGE_PREFIX for your registry)
./docker/scripts/build-and-push.sh --only=pi
./docker/scripts/build-and-push.sh --only=nuclearpi
IMAGE_PREFIX=myuser ./docker/scripts/build-and-push.sh --push       # push to myuser/rotorhazard:*
```

Resulting image tags (the build script pushes to the registry you configure; see script for `IMAGE` / tag variables):

| Image | Platform |
|-------|----------|
| `rotorhazard:base` | arm64 (intermediate, for pi/nuclearpi) |
| `rotorhazard:latest` | amd64 + arm64 |
| `rotorhazard-pi:latest` | arm64 |
| `rotorhazard-nuclearpi:latest` | arm64 |

## Manual builds

Build from **repo root**. For Pi or NuclearHazard you must build (or pull) the base image first. Use your own registry/tag as needed.

```bash
# One-time: create buildx builder
docker buildx create --use --name multi

# Default (x64)
docker build -f docker/Dockerfile -t rotorhazard:latest .

# Pi (arm64) – base must exist (build or pull)
docker buildx build --platform linux/arm64 -f docker/Dockerfile --target base -t rotorhazard:base --load .
docker buildx build --platform linux/arm64 -f docker/Dockerfile.pi -t rotorhazard-pi:latest --load .

# NuclearHazard (arm64) – Pi image must exist
docker buildx build --platform linux/arm64 -f docker/Dockerfile.nuclearpi -t rotorhazard-nuclearpi:latest --load .
```

---

## NuclearHazard (Pi / arm64)

NuclearHazard uses the Pi image plus an entrypoint and default config. **Recommended:** use the run script on the Pi; it does host setup, pulls the image, and configures auto-start.

**Quick start on a Raspberry Pi:**

```bash
chmod +x docker/scripts/run-prod-nuclear-pi.sh
./docker/scripts/run-prod-nuclear-pi.sh
```

The script configures the Pi, pulls the NuclearHazard image (tag is configurable via `IMAGE` in the script), and reboots. After reboot, the server runs at `http://localhost`. Default credentials: `NuclearHazard` / `nuclearhazard`.

**Important:** The NuclearHazard board needs an external power supply; USB from the Pi alone is not sufficient.

See [README-NuclearHazard.md](README-NuclearHazard.md) for access, troubleshooting, and optional WiFi hotspot setup.
