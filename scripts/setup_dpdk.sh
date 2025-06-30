#!/bin/bash
# DPDK Environment Setup Script for Python Integration

set -e

# Check root privileges
if [ "$EUID" -ne 0 ]; then
  echo "Please run as root for DPDK setup"
  exit 1
fi

echo "Setting up DPDK environment for Python integration..."

# Install DPDK and development packages
apt-get update
apt-get install -y dpdk dpdk-dev libdpdk-dev python3-dev build-essential

# Configure hugepages
echo 1024 > /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages
mkdir -p /mnt/huge
mount -t hugetlbfs none /mnt/huge

# Load required kernel modules
modprobe uio
modprobe uio_pci_generic

# Bind network interface to DPDK
INTERFACE=${1:-eth0}
if [ -f /sys/class/net/$INTERFACE/device/uevent ]; then
    PCI_ADDR=$(basename $(readlink /sys/class/net/$INTERFACE/device))
    echo "Binding $INTERFACE ($PCI_ADDR) to DPDK-compatible driver..."
    dpdk-devbind.py --bind=uio_pci_generic $PCI_ADDR
    
    echo "Network interface binding status:"
    dpdk-devbind.py --status
else
    echo "Warning: Interface $INTERFACE not found. Please specify correct interface."
    echo "Available interfaces:"
    ls /sys/class/net/
fi

# Set library path for DPDK shared libraries
echo "/usr/local/lib/x86_64-linux-gnu" > /etc/ld.so.conf.d/dpdk.conf
ldconfig

echo "DPDK environment setup complete!"
echo "Run with: sudo python3 src/main.py"
