# Real-Time Network Intrusion Detection System

This project implements a high-performance network intrusion detection system using Python and DPDK for packet capture, feature extraction, and Kafka for real-time data streaming. The system captures network packets at line speed, extracts 30+ cybersecurity features, and streams structured data to Kafka for machine learning analysis.

## Prerequisites
- Ubuntu 22.04 LTS (or similar Linux distribution)
- Root or sudo access
- Network interface compatible with DPDK
- At least 4GB RAM and 2GB free disk space
- Internet connection for downloading dependencies

## Project Structure
```
network-intrusion-detection/
├── config/
│   ├── dpdk_config.ini          # DPDK configuration settings
│   └── kafka_config.ini         # Kafka producer settings
├── scripts/
│   ├── setup_dpdk.sh           # DPDK environment setup
│   ├── install_deps.sh         # Python dependencies installer
│   └── run.sh                  # Application launcher
├── src/
│   ├── dpdk/
│   │   ├── __init__.py
│   │   ├── dpdk_wrapper.py     # DPDK Python wrapper
│   │   ├── mbuf_struct.py      # DPDK mbuf structures
│   │   └── packet_capture.py   # High-performance packet capture
│   ├── packet_parser.py        # 30+ feature extraction
│   ├── kafka_producer.py       # Kafka message streaming
│   ├── json_converter.py       # JSON data formatting
│   └── main.py                 # Main application
├── requirements.txt             # Python dependencies
├── Dockerfile                  # Container deployment
├── docker-compose.yml          # Multi-service orchestration
└── README.md                   # This file
```

## Complete Setup Instructions (Start to Finish)

### Step 1: Update System and Install Base Dependencies
```bash
# Update package repositories
sudo apt update && sudo apt upgrade -y

# Install essential build tools and libraries
sudo apt install -y \
    build-essential \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    libpcap-dev \
    libnuma-dev \
    dpdk \
    dpdk-dev \
    libdpdk-dev \
    git \
    curl \
    wget
```
**What this does:** Installs all system-level dependencies including DPDK libraries, Python development tools, and build essentials required for the project.

### Step 2: Navigate to Project Directory
```bash
# Go to your project directory
cd network-intrusion-detection

# Make all scripts executable
chmod +x scripts/*.sh
```
**What this does:** Sets proper permissions for all shell scripts so they can be executed.

### Step 3: Setup DPDK Environment
```bash
# First, check available network interfaces
ip link show

# Setup DPDK with your network interface (replace 'eth0' with your interface)
sudo ./scripts/setup_dpdk.sh eth0
```
**What this does:** 
- Configures hugepages (large memory pages for DPDK)
- Loads necessary kernel modules (uio, uio_pci_generic)
- Binds your network interface to DPDK-compatible drivers
- Sets up shared library paths

**Important:** Replace `eth0` with your actual network interface name from the `ip link show` output.

### Step 4: Install Python Dependencies
```bash
# Create virtual environment and install Python packages
./scripts/install_deps.sh
```
**What this does:**
- Creates a Python virtual environment in `venv/` directory
- Installs confluent-kafka and other required Python packages
- Activates the virtual environment for use

### Step 5: Setup Kafka Infrastructure
You have two options for running Kafka:

#### Option A: Using Docker (Recommended)
```bash
# Install Docker if not already installed
sudo apt install -y docker.io docker-compose

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Add your user to docker group (logout/login required after this)
sudo usermod -aG docker $USER

# Start Kafka services
docker-compose up -d
```

#### Option B: Manual Kafka Installation
```bash
# Download and setup Kafka manually
wget https://downloads.apache.org/kafka/2.13-3.5.0/kafka_2.13-3.5.0.tgz
tar -xzf kafka_2.13-3.5.0.tgz
cd kafka_2.13-3.5.0

# Start Zookeeper
bin/zookeeper-server-start.sh config/zookeeper.properties &

# Start Kafka
bin/kafka-server-start.sh config/server.properties &
```

**What this does:** Sets up the Kafka message broker that will receive and distribute the network flow data.

### Step 6: Verify DPDK Setup
```bash
# Check hugepage allocation
grep Huge /proc/meminfo

# Verify network interface binding
dpdk-devbind.py --status

# Check DPDK libraries
ldconfig -p | grep dpdk
```
**What this does:** Validates that DPDK is properly configured and your network interface is correctly bound.

### Step 7: Run the Network Capture Application
```bash
# Run the main application (requires root for DPDK)
sudo ./scripts/run.sh
```
**What this does:**
- Activates the Python virtual environment
- Sets up DPDK environment variables
- Starts the packet capture application
- Begins capturing packets and streaming to Kafka

### Step 8: Verify Data Flow
Open a new terminal and check if data is flowing:

```bash
# Check Kafka topics (if using Docker)
docker exec -it $(docker ps -q --filter name=kafka) kafka-topics --list --bootstrap-server localhost:9092

# Monitor network-flows topic
docker exec -it $(docker ps -q --filter name=kafka) kafka-console-consumer --bootstrap-server localhost:9092 --topic network-flows --from-beginning
```

**What this does:** Verifies that network flow data is being successfully captured and sent to Kafka.

## Configuration Options

### DPDK Configuration (`config/dpdk_config.ini`)
```ini
[dpdk]
port_id = 0              # Network port to monitor
nb_mbufs = 8191          # Number of packet buffers
cache_size = 250         # Memory pool cache size
burst_size = 32          # Packets processed per burst
rx_ring_size = 1024      # Receive ring buffer size
```

### Kafka Configuration (`config/kafka_config.ini`)
```ini
[kafka]
bootstrap_servers = localhost:9092    # Kafka broker address
topic = network-flows                 # Destination topic
batch_size = 16384                   # Message batching size
compression_type = lz4               # Message compression
```

## Monitoring and Verification

### Check Application Status
```bash
# View application logs
sudo tail -f /var/log/syslog | grep python

# Monitor system resources
htop

# Check network interface statistics
cat /proc/net/dev
```

### Access Kafka UI (if using Docker)
Open your web browser and go to: `http://localhost:8080`

This provides a web interface to monitor Kafka topics, messages, and system health.

### Sample Output Data
The system generates JSON messages with 30+ features like this:
```json
{
  "src_ip": "192.168.1.100",
  "dst_ip": "192.168.1.200",
  "src_port": 54321,
  "dst_port": 80,
  "protocol": 6,
  "packet_length": 1420,
  "flow_duration": 0.045,
  "total_fwd_packets": 5,
  "total_bwd_packets": 3,
  "packet_length_mean": 892.5,
  "flow_bytes_per_second": 31555.6,
  "tcp_flags": 24,
  "label": "BENIGN"
}
```

## Stopping the Application

### Graceful Shutdown
```bash
# In the terminal running the application, press:
Ctrl+C
```

### Stop Kafka Services
```bash
# If using Docker
docker-compose down

# If using manual Kafka installation
# Kill Kafka and Zookeeper processes
pkill -f kafka
pkill -f zookeeper
```

### Cleanup DPDK (Optional)
```bash
# Unbind network interface from DPDK
sudo dpdk-devbind.py --bind=<original_driver> <pci_address>

# Example:
sudo dpdk-devbind.py --bind=e1000e 0000:00:03.0
```

## Troubleshooting Common Issues

### Issue: "No Ethernet ports found"
**Solution:**
```bash
# Check if interface is properly bound
dpdk-devbind.py --status

# Re-run DPDK setup
sudo ./scripts/setup_dpdk.sh <your_interface>
```

### Issue: "Failed to load DPDK libraries"
**Solution:**
```bash
# Update library cache
sudo ldconfig

# Check library paths
echo $LD_LIBRARY_PATH
```

### Issue: "Permission denied" errors
**Solution:**
```bash
# Ensure you're running with sudo
sudo ./scripts/run.sh

# Check file permissions
ls -la scripts/
```

### Issue: Kafka connection failures
**Solution:**
```bash
# Check if Kafka is running
docker ps | grep kafka

# Verify Kafka connectivity
telnet localhost 9092
```

### Issue: Low packet capture rate
**Solution:**
```bash
# Check hugepage allocation
echo 2048 | sudo tee /sys/kernel/mm/hugepages/hugepages-2048kB/nr_hugepages

# Verify CPU isolation
cat /proc/cmdline
```

## Performance Expectations

### Typical Performance Metrics
- **Packet Capture Rate:** 10,000-100,000 packets/second
- **Feature Extraction:** 30+ features per packet
- **Memory Usage:** 500MB-2GB depending on traffic volume
- **CPU Usage:** 1-2 cores at 50-80% utilization
- **Kafka Throughput:** 1,000-10,000 messages/second

### System Requirements for Optimal Performance
- **CPU:** 4+ cores, 2.4GHz+
- **RAM:** 8GB+ (4GB for hugepages)
- **Network:** 1Gbps+ interface with DPDK support
- **Storage:** SSD recommended for Kafka logs

## Next Steps

After successfully running the packet capture system:

1. **Add Machine Learning:** Implement the job server component for real-time threat detection
2. **Scale Deployment:** Use Kubernetes for production deployment
3. **Add Alerting:** Integrate with SIEM systems for security response
4. **Optimize Performance:** Tune DPDK and Kafka parameters for your specific environment

## Features Extracted

The system extracts 30+ network flow features for machine learning analysis:

### Basic Network Features (9)
- Source/Destination IP addresses and ports
- Protocol type and packet characteristics
- TTL, TOS, and header information

### TCP-Specific Features (8)
- TCP flags (SYN, ACK, FIN, RST, PSH, URG)
- TCP sequence and acknowledgment numbers
- TCP window sizes

### Flow Statistics (4)
- Forward/backward packet and byte counts
- Flow duration and timing information

### Packet Length Analysis (6)
- Mean, standard deviation, min/max packet lengths
- Packet length variance and forward packet statistics

### Flow Rate Calculations (4)
- Bytes per second and packets per second
- Forward and backward flow rates

### Inter-arrival Timing (4)
- Inter-arrival time statistics
- Forward and backward timing analysis

### Activity Analysis (4)
- Active and idle period statistics
- Flow activity patterns

## Support and Documentation

- **DPDK Documentation:** https://doc.dpdk.org/
- **Kafka Documentation:** https://kafka.apache.org/documentation/
- **Project Issues:** Check logs in `/var/log/syslog` for detailed error messages

## License
MIT License - see LICENSE file for details.