# Blender Render API Server
# Multi-stage build for smaller final image

FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

# Download and extract Blender
WORKDIR /opt
RUN wget -q "https://download.blender.org/release/Blender4.3/blender-4.3.2-linux-x64.tar.xz" \
    && tar -xf blender-4.3.2-linux-x64.tar.xz \
    && rm blender-4.3.2-linux-x64.tar.xz

# Final image
FROM python:3.11-slim

# Install Blender runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxi6 \
    libxxf86vm1 \
    libxfixes3 \
    libxrender1 \
    libgl1 \
    libglu1-mesa \
    libsm6 \
    libxkbcommon0 \
    libegl1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Blender from builder
COPY --from=builder /opt/blender-4.3.2-linux-x64 /opt/blender-4.3.2-linux-x64

WORKDIR /app

# Install Python dependencies
COPY server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY scripts/ ./scripts/
COPY server/ ./server/

# Create output directories
RUN mkdir -p output jobs

# Environment
ENV BLENDER_PATH=/opt/blender-4.3.2-linux-x64/blender
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the API server
CMD ["python", "-m", "uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "8080"]
