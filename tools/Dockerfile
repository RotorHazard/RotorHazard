# RotorHazard Server Dockerfile
# Python 3.10+ is required (MIN_PYTHON_MAJOR_VERSION = 3, MIN_PYTHON_MINOR_VERSION = 10)
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file (using reqsNonPi.txt since we're not on a Raspberry Pi)
COPY src/server/reqsNonPi.txt /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy server application files
COPY src/server/ /app/src/server/

# Copy interface directory (required by server)
COPY src/interface/ /app/src/interface/

# Set working directory to server directory
WORKDIR /app/src/server

# Create data directory for persistent storage
RUN mkdir -p /app/data

# Expose the default HTTP port
EXPOSE 5000

# Set environment variable for data directory
ENV RH_DATA_DIR=/app/data

# Run the server with data directory flag
CMD ["python", "server.py", "--data", "/app/data"]
