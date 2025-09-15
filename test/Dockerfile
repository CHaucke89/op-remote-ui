# Dockerfile for testing OpenPilot UI streaming solution
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    cmake \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    curl \
    iproute2 \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .
COPY test/requirements-test.txt test/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r test/requirements-test.txt

# Copy application files
COPY stream_server.py .
COPY test/ test/

# Create shared memory directory
RUN mkdir -p /dev/shm

# Expose ports
EXPOSE 8081

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=stream_server.py

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8081/stats || exit 1

# Default command - run both simulator and server
CMD ["sh", "-c", "python test/mock_ui_simulator.py & python stream_server.py"]