FROM ubuntu:22.04

# Install DPDK and dependencies
RUN apt-get update && apt-get install -y \
    dpdk dpdk-dev libdpdk-dev \
    python3 python3-pip python3-venv \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY scripts/ ./scripts/

# Make scripts executable
RUN chmod +x scripts/*.sh

# Setup DPDK shared library paths
RUN echo "/usr/lib/x86_64-linux-gnu" > /etc/ld.so.conf.d/dpdk.conf && \
    ldconfig

# Create entrypoint script
RUN echo '#!/bin/bash\n\
echo "Setting up hugepages..."\n\
mkdir -p /mnt/huge\n\
mount -t hugetlbfs none /mnt/huge 2>/dev/null || true\n\
echo 1024 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages 2>/dev/null || true\n\
\n\
echo "Loading kernel modules..."\n\
modprobe uio 2>/dev/null || true\n\
modprobe uio_pci_generic 2>/dev/null || true\n\
\n\
exec python3 src/main.py' > /entrypoint.sh && \
chmod +x /entrypoint.sh

# Run as privileged container
ENTRYPOINT ["/entrypoint.sh"]
