# Docker Setup for RotorHazard Server

## Quick Start

### Using Docker Compose (Recommended)

1. **Build and run the container:**
   ```bash
   cd tools
   docker-compose down  # Clean up any existing containers first
   docker-compose up -d
   ```

2. **Access the web interface:**
   Open your browser and navigate to `http://localhost:5000`

3. **Stop the container:**
   ```bash
   docker-compose down
   ```
   
   (Run from the `tools` directory)

### Using Docker directly

1. **Build the image:**
   ```bash
   docker build -f tools/Dockerfile -t rotorhazard-server .
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

**Docker Compose:** Edit `tools/docker-compose.yml`:
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

### USB Device Access

USB devices are accessible by default. To use specific devices only, edit `tools/docker-compose.yml`:

```yaml
# Comment out: privileged: true
# Uncomment:
devices:
  - /dev/ttyUSB0:/dev/ttyUSB0
  - /dev/ttyACM0:/dev/ttyACM0
```