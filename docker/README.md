# RotorHazard Docker

## Local development (build from source)

Default compose file: builds from source so devs don’t pull from Docker Hub.

From **repo root**:

```bash
docker-compose -f docker/docker-compose.yml up -d
```

Or from `docker/`:

```bash
docker-compose up -d
```

Dev uses a **named volume** (`rotorhazard-dev-data`) so the repo has no data directory and personal data isn’t committed. To wipe dev data: `docker volume rm rotorhazard-dev-data` (after stopping the container).

## Production / published image (Docker Hub)

Use the pre-built image (e.g. on a Pi or when you don’t have the repo):

```bash
docker pull racefpv/rotorhazard:latest
```

Run with the prod compose file (same ports/volumes, no build):

From **repo root**:

```bash
docker-compose -f docker/docker-compose.prod.yml up -d
```

Or from `docker/`:

```bash
docker-compose -f docker-compose.prod.yml up -d
```

**Without compose** (same behavior, one container):

```bash
# Script (default data dir: ./data)
chmod +x docker/run-prod.sh
./docker/run-prod.sh

# Or custom data dir
./docker/run-prod.sh /opt/rotorhazard/data
```

One-liner (set your own path for the volume):

```bash
docker run -d --name rotorhazard-server --restart unless-stopped -p 5000:5000 -v ./data:/app/data -e RH_DATA_DIR=/app/data --privileged racefpv/rotorhazard:latest
```

| File                      | Use case        | Image source   |
|---------------------------|-----------------|----------------|
| `docker-compose.yml`      | Local dev       | Build from repo |
| `docker-compose.prod.yml` | Production / Pi | Docker Hub     |

## Dockerfiles

| File           | Use case   | Requirements        |
|----------------|------------|---------------------|
| `Dockerfile`   | Non-Pi (x64/amd64) | `reqsNonPi.txt`  |
| `Dockerfile.pi` | Raspberry Pi (arm64) | `requirements.txt` (RPi.GPIO, rpi-ws281x, etc.) |

Build from **repo root**:
- Non-Pi: `docker build -f docker/Dockerfile -t rotorhazard .`
- Pi: `docker build -f docker/Dockerfile.pi -t rotorhazard:pi .`

## Multi-platform build (amd64 + arm64)

To push one tag that works on both x64 and Raspberry Pi, build each platform with its Dockerfile and push to the same tag:

From the **repo root**:

```bash
docker buildx create --use --name multi  # one-time

# Non-Pi image for amd64
docker buildx build --platform linux/amd64 -f docker/Dockerfile -t racefpv/rotorhazard:latest --push .

# Pi image for arm64 (uses requirements.txt with RPi.GPIO, etc.)
docker buildx build --platform linux/arm64 -f docker/Dockerfile.pi -t racefpv/rotorhazard:latest --push .
```

Result: `docker pull racefpv/rotorhazard:latest` gets the non-Pi image on amd64 and the Pi image on arm64.
