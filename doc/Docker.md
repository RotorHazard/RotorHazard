# Docker Setup for RotorHazard Server

## Quick start

### Local development (build from source)

From the **repository root**:

```bash
docker-compose -f docker/docker-compose.yml up -d
```

Or from the `docker/` directory:

```bash
cd docker
docker-compose down   # clean up any existing container first
docker-compose up -d
```

Access the web interface at `http://localhost:5000`.

To stop:

```bash
docker-compose -f docker/docker-compose.yml down   # from repo root
# or from docker/:  docker-compose down
```

### Production (pre-built image)

Pull the image from your registry and run it (e.g. on a server or Pi without the repo):

```bash
docker pull <your-registry>/rotorhazard:latest
docker run -d \
  --name rotorhazard-server \
  --restart unless-stopped \
  -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  -e RH_DATA_DIR=/app/data \
  --privileged \
  <your-registry>/rotorhazard:latest
```

Or use the run script (recommended; image tag configurable via `IMAGE`):

```bash
./docker/scripts/run-prod.sh           # data dir: ./data
./docker/scripts/run-prod.sh /path/to/data
```

### Building the image yourself

From the repository root:

```bash
docker build -f docker/Dockerfile -t rotorhazard-server .
docker run -d \
  --name rotorhazard-server \
  -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  -e RH_DATA_DIR=/app/data \
  --privileged \
  rotorhazard-server
```

## Configuration

### Change port

**Docker Compose:** Edit `docker/docker-compose.yml`:

```yaml
ports:
  - "8080:5000"  # change 8080 to your desired port
```

**Docker run:** Change the `-p` flag:

```bash
docker run -d \
  --name rotorhazard-server \
  -p 8080:5000 \
  -v $(pwd)/data:/app/data \
  -e RH_DATA_DIR=/app/data \
  --privileged \
  <your-image>
```

### Hardware access (USB, GPIO, SPI, I2C)

**Raspberry Pi:** Use the Pi image and run script for full GPIO/SPI/I2C support. The default compose and run examples use `--privileged`, which gives the container full hardware access.

**Alternative (specific devices only):** Edit `docker/docker-compose.yml`:

```yaml
# Comment out: privileged: true
# Uncomment:
devices:
  - /dev/gpiomem:/dev/gpiomem
  - /dev/spidev0.0:/dev/spidev0.0
  - /dev/i2c-1:/dev/i2c-1
  - /dev/ttyUSB0:/dev/ttyUSB0
  - /dev/ttyACM0:/dev/ttyACM0
```

## Image variants and Pi / NuclearHazard

- **Default (x64):** `Dockerfile` — for amd64/x64.
- **Raspberry Pi (arm64):** `Dockerfile.pi` — extends the base image with Pi requirements and GPIO/LED support.
- **NuclearHazard (arm64):** Uses the Pi image plus an entrypoint and defaults; recommended setup is the run script on the Pi.

For build design, multi-platform builds, and NuclearHazard setup, see [docker/README.md](../docker/README.md) and [docker/README-NuclearHazard.md](../docker/README-NuclearHazard.md).
