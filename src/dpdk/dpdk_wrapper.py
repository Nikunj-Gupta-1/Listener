#!/usr/bin/env python3
import ctypes
import ctypes.util
import logging
from typing import Optional, List

class DPDKWrapper:
    """Python wrapper for DPDK shared libraries using ctypes"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # DPDK shared libraries
        self.eal_lib = None
        self.ethdev_lib = None
        self.mempool_lib = None
        self.mbuf_lib = None
        
        # Function pointers
        self.rte_eal_init = None
        self.rte_eth_dev_count_avail = None
        self.rte_eth_dev_configure = None
        self.rte_eth_rx_queue_setup = None
        self.rte_eth_tx_queue_setup = None
        self.rte_eth_dev_start = None
        self.rte_eth_rx_burst = None
        self.rte_mempool_create = None
        self.rte_pktmbuf_pool_create = None
        self.rte_pktmbuf_free = None
        
        self._load_libraries()
        self._setup_functions()
    
    def _load_libraries(self):
        """Load DPDK shared libraries"""
        try:
            # Try to find DPDK libraries
            eal_lib_path = ctypes.util.find_library('rte_eal')
            if not eal_lib_path:
                # Fallback to common paths
                eal_lib_path = '/usr/local/lib/x86_64-linux-gnu/librte_eal.so'
            
            self.eal_lib = ctypes.CDLL(eal_lib_path)
            self.logger.info(f"Loaded librte_eal from {eal_lib_path}")
            
            # Load other DPDK libraries
            self.ethdev_lib = ctypes.CDLL('/usr/local/lib/x86_64-linux-gnu/librte_ethdev.so')
            self.mempool_lib = ctypes.CDLL('/usr/local/lib/x86_64-linux-gnu/librte_mempool.so')
            self.mbuf_lib = ctypes.CDLL('/usr/local/lib/x86_64-linux-gnu/librte_mbuf.so')
            
            self.logger.info("Successfully loaded all DPDK libraries")
            
        except OSError as e:
            self.logger.error(f"Failed to load DPDK libraries: {e}")
            raise RuntimeError("DPDK libraries not found. Please ensure DPDK is installed.")
    
    def _setup_functions(self):
        """Setup DPDK function signatures"""
        try:
            # rte_eal_init(int argc, char **argv)
            self.rte_eal_init = self.eal_lib.rte_eal_init
            self.rte_eal_init.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_char_p)]
            self.rte_eal_init.restype = ctypes.c_int
            
            # rte_eth_dev_count_avail()
            self.rte_eth_dev_count_avail = self.ethdev_lib.rte_eth_dev_count_avail
            self.rte_eth_dev_count_avail.argtypes = []
            self.rte_eth_dev_count_avail.restype = ctypes.c_uint16
            
            # rte_eth_dev_configure(uint16_t port_id, uint16_t nb_rx_q, uint16_t nb_tx_q, const struct rte_eth_conf *eth_conf)
            self.rte_eth_dev_configure = self.ethdev_lib.rte_eth_dev_configure
            self.rte_eth_dev_configure.argtypes = [ctypes.c_uint16, ctypes.c_uint16, ctypes.c_uint16, ctypes.c_void_p]
            self.rte_eth_dev_configure.restype = ctypes.c_int
            
            # rte_eth_rx_queue_setup(uint16_t port_id, uint16_t rx_queue_id, uint16_t nb_rx_desc, unsigned int socket_id, const struct rte_eth_rxconf *rx_conf, struct rte_mempool *mb_pool)
            self.rte_eth_rx_queue_setup = self.ethdev_lib.rte_eth_rx_queue_setup
            self.rte_eth_rx_queue_setup.argtypes = [ctypes.c_uint16, ctypes.c_uint16, ctypes.c_uint16, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
            self.rte_eth_rx_queue_setup.restype = ctypes.c_int
            
            # rte_eth_tx_queue_setup(uint16_t port_id, uint16_t tx_queue_id, uint16_t nb_tx_desc, unsigned int socket_id, const struct rte_eth_txconf *tx_conf)
            self.rte_eth_tx_queue_setup = self.ethdev_lib.rte_eth_tx_queue_setup
            self.rte_eth_tx_queue_setup.argtypes = [ctypes.c_uint16, ctypes.c_uint16, ctypes.c_uint16, ctypes.c_uint, ctypes.c_void_p]
            self.rte_eth_tx_queue_setup.restype = ctypes.c_int
            
            # rte_eth_dev_start(uint16_t port_id)
            self.rte_eth_dev_start = self.ethdev_lib.rte_eth_dev_start
            self.rte_eth_dev_start.argtypes = [ctypes.c_uint16]
            self.rte_eth_dev_start.restype = ctypes.c_int
            
            # rte_eth_rx_burst(uint16_t port_id, uint16_t queue_id, struct rte_mbuf **rx_pkts, const uint16_t nb_pkts)
            self.rte_eth_rx_burst = self.ethdev_lib.rte_eth_rx_burst
            self.rte_eth_rx_burst.argtypes = [ctypes.c_uint16, ctypes.c_uint16, ctypes.POINTER(ctypes.c_void_p), ctypes.c_uint16]
            self.rte_eth_rx_burst.restype = ctypes.c_uint16
            
            # rte_pktmbuf_pool_create(const char *name, unsigned n, unsigned cache_size, uint16_t priv_size, uint16_t data_room_size, int socket_id)
            self.rte_pktmbuf_pool_create = self.mbuf_lib.rte_pktmbuf_pool_create
            self.rte_pktmbuf_pool_create.argtypes = [ctypes.c_char_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint16, ctypes.c_uint16, ctypes.c_int]
            self.rte_pktmbuf_pool_create.restype = ctypes.c_void_p
            
            # rte_pktmbuf_free(struct rte_mbuf *m)
            self.rte_pktmbuf_free = self.mbuf_lib.rte_pktmbuf_free
            self.rte_pktmbuf_free.argtypes = [ctypes.c_void_p]
            self.rte_pktmbuf_free.restype = None
            
            self.logger.info("Successfully setup DPDK function signatures")
            
        except AttributeError as e:
            self.logger.error(f"Failed to setup DPDK functions: {e}")
            raise RuntimeError("DPDK function signatures could not be established")
    
    def initialize_eal(self, eal_args: List[str]) -> int:
        """Initialize DPDK EAL (Environment Abstraction Layer)"""
        try:
            # Convert Python strings to C char**
            argc = len(eal_args)
            argv = (ctypes.c_char_p * argc)()
            for i, arg in enumerate(eal_args):
                argv[i] = arg.encode('utf-8')
            
            result = self.rte_eal_init(argc, argv)
            if result < 0:
                raise RuntimeError(f"EAL initialization failed with code {result}")
            
            self.logger.info(f"EAL initialized successfully, processed {result} arguments")
            return result
            
        except Exception as e:
            self.logger.error(f"EAL initialization error: {e}")
            raise
    
    def get_port_count(self) -> int:
        """Get number of available Ethernet ports"""
        return self.rte_eth_dev_count_avail()
    
    def create_mempool(self, name: str, nb_mbufs: int, cache_size: int, data_room_size: int, socket_id: int) -> ctypes.c_void_p:
        """Create a mempool for packet buffers"""
        pool = self.rte_pktmbuf_pool_create(
            name.encode('utf-8'),
            nb_mbufs,
            cache_size,
            0,  # priv_size
            data_room_size,
            socket_id
        )
        
        if not pool:
            raise RuntimeError(f"Failed to create mempool {name}")
        
        self.logger.info(f"Created mempool {name} with {nb_mbufs} mbufs")
        return pool
    
    def configure_port(self, port_id: int, nb_rx_queues: int, nb_tx_queues: int) -> int:
        """Configure Ethernet port"""
        # Use NULL for default configuration
        result = self.rte_eth_dev_configure(port_id, nb_rx_queues, nb_tx_queues, None)
        if result < 0:
            raise RuntimeError(f"Port {port_id} configuration failed with code {result}")
        
        self.logger.info(f"Configured port {port_id} with {nb_rx_queues} RX, {nb_tx_queues} TX queues")
        return result
    
    def setup_rx_queue(self, port_id: int, queue_id: int, nb_desc: int, socket_id: int, mempool: ctypes.c_void_p) -> int:
        """Setup RX queue"""
        result = self.rte_eth_rx_queue_setup(port_id, queue_id, nb_desc, socket_id, None, mempool)
        if result < 0:
            raise RuntimeError(f"RX queue setup failed for port {port_id}, queue {queue_id} with code {result}")
        
        self.logger.info(f"Setup RX queue {queue_id} on port {port_id}")
        return result
    
    def setup_tx_queue(self, port_id: int, queue_id: int, nb_desc: int, socket_id: int) -> int:
        """Setup TX queue"""
        result = self.rte_eth_tx_queue_setup(port_id, queue_id, nb_desc, socket_id, None)
        if result < 0:
            raise RuntimeError(f"TX queue setup failed for port {port_id}, queue {queue_id} with code {result}")
        
        self.logger.info(f"Setup TX queue {queue_id} on port {port_id}")
        return result
    
    def start_port(self, port_id: int) -> int:
        """Start Ethernet port"""
        result = self.rte_eth_dev_start(port_id)
        if result < 0:
            raise RuntimeError(f"Port {port_id} start failed with code {result}")
        
        self.logger.info(f"Started port {port_id}")
        return result
    
    def receive_packets(self, port_id: int, queue_id: int, nb_pkts: int) -> List[ctypes.c_void_p]:
        """Receive packets using DPDK burst mode"""
        # Allocate array for mbuf pointers
        rx_pkts = (ctypes.c_void_p * nb_pkts)()
        
        # Receive packets
        nb_rx = self.rte_eth_rx_burst(port_id, queue_id, rx_pkts, nb_pkts)
        
        # Return list of received mbufs
        return [rx_pkts[i] for i in range(nb_rx)]
    
    def free_packet(self, mbuf: ctypes.c_void_p):
        """Free packet mbuf"""
        if mbuf:
            self.rte_pktmbuf_free(mbuf)
