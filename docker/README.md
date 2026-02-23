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

## Build and push (all images)

From **repo root**. The script builds the base image when building Pi or NuclearHazard, then builds in order: rotorhazard (default) → pi → nuclearpi.

```bash
./docker/scripts/build-and-push.sh              # build and push all
./docker/scripts/build-and-push.sh --no-push    # build only
./docker/scripts/build-and-push.sh --only=pi    # build/push one image
./docker/scripts/build-and-push.sh --only=nuclearpi
./docker/scripts/build-and-push.sh --only=rotorhazard
```

Resulting image tags (the build script pushes to the registry you configure; see script for `IMAGE` / tag variables):

| Image | Platform |
|-------|----------|
| `rotorhazard:base` | arm64 (intermediate, for pi/nuclearpi) |
| `rotorhazard:latest` | amd64 |
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
