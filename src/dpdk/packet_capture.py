#!/usr/bin/env python3
import time
import logging
import configparser
from typing import Callable, Optional
from .dpdk_wrapper import DPDKWrapper
from .mbuf_struct import RteMbuf
import ctypes

class DPDKPacketCapture:
    """High-performance packet capture using DPDK"""
    
    def __init__(self, config_file: str = "config/dpdk_config.ini"):
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        
        # DPDK configuration
        self.port_id = self.config.getint('dpdk', 'port_id', fallback=0)
        self.nb_mbufs = self.config.getint('dpdk', 'nb_mbufs', fallback=8191)
        self.cache_size = self.config.getint('dpdk', 'cache_size', fallback=250)
        self.burst_size = self.config.getint('dpdk', 'burst_size', fallback=32)
        self.rx_ring_size = self.config.getint('dpdk', 'rx_ring_size', fallback=1024)
        self.tx_ring_size = self.config.getint('dpdk', 'tx_ring_size', fallback=1024)
        
        # DPDK wrapper instance
        self.dpdk = DPDKWrapper()
        self.mempool = None
        self.running = False
        self.packet_count = 0
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
    
    def initialize(self) -> bool:
        """Initialize DPDK packet capture"""
        try:
            # EAL initialization arguments
            eal_args = [
                'python_dpdk_app',  # Application name
                '-l', '0-3',        # Core list
                '-n', '4',          # Memory channels
                '--huge-dir', '/mnt/huge',  # Hugepage directory
                '--proc-type', 'auto'       # Process type
            ]
            
            # Initialize EAL
            self.dpdk.initialize_eal(eal_args)
            
            # Check available ports
            nb_ports = self.dpdk.get_port_count()
            if nb_ports == 0:
                raise RuntimeError("No Ethernet ports found")
            
            self.logger.info(f"Found {nb_ports} Ethernet ports")
            
            # Create mempool for packet buffers
            self.mempool = self.dpdk.create_mempool(
                name="mbuf_pool",
                nb_mbufs=self.nb_mbufs,
                cache_size=self.cache_size,
                data_room_size=2048,  # Default data room size
                socket_id=0  # NUMA socket
            )
            
            # Configure port
            self.dpdk.configure_port(self.port_id, 1, 1)  # 1 RX queue, 1 TX queue
            
            # Setup queues
            self.dpdk.setup_rx_queue(self.port_id, 0, self.rx_ring_size, 0, self.mempool)
            self.dpdk.setup_tx_queue(self.port_id, 0, self.tx_ring_size, 0)
            
            # Start port
            self.dpdk.start_port(self.port_id)
            
            self.logger.info(f"DPDK packet capture initialized on port {self.port_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"DPDK initialization failed: {e}")
            return False
    
    def start_capture(self, callback: Callable[[bytes, float], None]):
        """Start packet capture with callback function"""
        if not self.mempool:
            if not self.initialize():
                return
        
        self.running = True
        self.logger.info("Starting DPDK packet capture...")
        
        try:
            while self.running:
                # Receive packets in burst mode
                mbufs = self.dpdk.receive_packets(self.port_id, 0, self.burst_size)
                
                if not mbufs:
                    # No packets received, small delay to prevent CPU spinning
                    time.sleep(0.001)
                    continue
                
                # Process each received packet
                for mbuf_ptr in mbufs:
                    try:
                        # Convert pointer to RteMbuf structure
                        mbuf = RteMbuf.from_address(mbuf_ptr)
                        
                        # Extract packet data
                        packet_data = mbuf.get_packet_data()
                        
                        if packet_data:
                            # Get current timestamp
                            timestamp = time.time()
                            
                            # Call user callback
                            callback(packet_data, timestamp)
                            
                            self.packet_count += 1
                            
                            # Log progress
                            if self.packet_count % 1000 == 0:
                                self.logger.info(f"Captured {self.packet_count} packets")
                    
                    except Exception as e:
                        self.logger.warning(f"Error processing packet: {e}")
                    
                    finally:
                        # Free the mbuf
                        self.dpdk.free_packet(mbuf_ptr)
                        
        except KeyboardInterrupt:
            self.logger.info("Capture interrupted by user")
        except Exception as e:
            self.logger.error(f"Capture error: {e}")
        finally:
            self.stop_capture()
    
    def stop_capture(self):
        """Stop packet capture"""
        self.running = False
        self.logger.info(f"DPDK capture stopped. Total packets: {self.packet_count}")
    
    def get_stats(self) -> dict:
        """Get capture statistics"""
        return {
            'total_packets': self.packet_count,
            'port_id': self.port_id,
            'running': self.running,
            'mempool_created': self.mempool is not None
        }
