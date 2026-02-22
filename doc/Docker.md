# Docker Setup for RotorHazard Server

## Quick Start

### Using Docker Compose (Recommended)

1. **Build and run the container:**
   ```bash
   cd docker
   docker-compose down  # Clean up any existing containers first
   docker-compose up -d
   ```

2. **Access the web interface:**
   Open your browser and navigate to `http://localhost:5000`

3. **Stop the container:**
   ```bash
   docker-compose down
   ```
   
   (Run from the `docker` directory)

### Using Docker directly

1. **Build the image:**
   ```bash
   docker build -f docker/Dockerfile -t rotorhazard-server .
   ```
   
   (Run from the repository root directory)

2. **Run the container:**
   ```bash
   docker run -d \
     --name rotorhazard-server \
     -p 5000:5000 \
     -v $(pwd)/data:/app/data \
     --privileged \
     rotorhazard-server
   ```

3. **View logs:**
   ```bash
   docker logs -f rotorhazard-server
   ```

4. **Access the web interface:**
   Open your browser and navigate to `http://localhost:5000`

5. **Stop the container:**
   ```bash
   docker stop rotorhazard-server
   docker rm rotorhazard-server
   ```

## Configuration

### Change Port

**Docker Compose:** Edit `docker/docker-compose.yml`:
```yaml
ports:
  - "8080:5000"  # Change 8080 to your desired port
```

**Docker run:** Change the `-p` flag:
```bash
docker run -d \
  --name rotorhazard-server \
  -p 8080:5000 \  # Change 8080 to your desired port
  -v $(pwd)/data:/app/data \
  --privileged \
  rotorhazard-server
```

### Hardware Access (USB, GPIO, SPI, I2C)

**Raspberry Pi GPIO/SPI/I2C:** `privileged: true` is enabled by default, which gives full access to hardware.

**Alternative (specific devices only):** Edit `docker/docker-compose.yml`:

```yaml
# Comment out: privileged: true
# Uncomment:
devices:
  - /dev/gpiomem:/dev/gpiomem       # GPIO
  - /dev/spidev0.0:/dev/spidev0.0   # SPI bus 0, device 0
  - /dev/i2c-1:/dev/i2c-1           # I2C bus 1 (typical on Pi)
  - /dev/ttyUSB0:/dev/ttyUSB0       # USB serial
  - /dev/ttyACM0:/dev/ttyACM0       # USB serial
```