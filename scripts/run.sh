#!/bin/bash
# Run the Python DPDK packet capture application

set -e

# Check for root privileges (required for DPDK)
if [ "$EUID" -ne 0 ]; then
    echo "DPDK applications require root privileges."
    echo "Please run with: sudo $0"
    exit 1
fi

# Set environment for DPDK
export RTE_SDK=/usr/share/dpdk
export RTE_TARGET=x86_64-native-linuxapp-gcc

# Ensure hugepages are mounted
if ! mount | grep -q hugetlbfs; then
    echo "Setting up hugepages..."
    mkdir -p /mnt/huge
    mount -t hugetlbfs none /mnt/huge
    echo 1024 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
fi

# Check if virtual environment exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Run the DPDK application
echo "Starting Python DPDK Network Capture Application..."
python3 src/main.py

echo "Application stopped."
