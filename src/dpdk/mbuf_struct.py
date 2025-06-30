#!/usr/bin/env python3
import ctypes
from typing import Optional

class RteMempool(ctypes.Structure):
    """Simplified representation of rte_mempool structure"""
    _fields_ = [
        ('name', ctypes.c_char * 32),
        ('pool_config', ctypes.c_void_p),
        ('pool_id', ctypes.c_uint32),
        # Add more fields as needed
    ]

class RteMbuf(ctypes.Structure):
    """
    Python representation of rte_mbuf structure
    Simplified version focusing on essential fields for packet processing
    """
    _fields_ = [
        # Cache line 0
        ('buf_addr', ctypes.c_void_p),           # Virtual address of segment buffer
        ('buf_physaddr', ctypes.c_uint64),       # Physical address (deprecated in newer versions)
        ('buf_len', ctypes.c_uint16),            # Length of segment buffer
        ('refcnt', ctypes.c_uint16),             # Reference counter
        ('nb_segs', ctypes.c_uint8),             # Number of segments
        ('port', ctypes.c_uint8),                # Input port
        ('ol_flags', ctypes.c_uint64),           # Offload features
        
        # Cache line 1  
        ('pkt_len', ctypes.c_uint32),            # Total pkt len: sum of all segments
        ('data_len', ctypes.c_uint16),           # Amount of data in segment buffer
        ('vlan_tci', ctypes.c_uint16),           # VLAN Tag Control Identifier
        ('hash_rss', ctypes.c_uint32),           # RSS hash result if RSS enabled
        ('hash_fdir_lo', ctypes.c_uint32),       # Flow director hash (low)
        ('hash_fdir_hi', ctypes.c_uint32),       # Flow director hash (high)
        ('vlan_tci_outer', ctypes.c_uint16),     # Outer VLAN Tag Control Identifier
        ('pool', ctypes.POINTER(RteMempool)),    # Pool from which mbuf was allocated
        ('next', ctypes.POINTER('RteMbuf')),     # Next segment of scattered packet
    ]
    
    def get_packet_data(self) -> bytes:
        """Extract packet data from mbuf"""
        if not self.buf_addr or self.data_len == 0:
            return b''
        
        try:
            # Calculate data start address (buf_addr + headroom)
            # Default headroom is typically 128 bytes in DPDK
            headroom = 128
            data_ptr = self.buf_addr + headroom
            
            # Create bytes from memory
            data_array = (ctypes.c_ubyte * self.data_len).from_address(data_ptr)
            return bytes(data_array)
        except Exception as e:
            # If direct memory access fails, return empty bytes
            return b''
    
    def get_packet_info(self) -> dict:
        """Get packet information from mbuf"""
        return {
            'pkt_len': self.pkt_len,
            'data_len': self.data_len,
            'port': self.port,
            'nb_segs': self.nb_segs,
            'vlan_tci': self.vlan_tci,
            'buf_len': self.buf_len,
            'refcnt': self.refcnt
        }

# Setup pointer type after class definition
RteMbuf._fields_[8] = ('next', ctypes.POINTER(RteMbuf))
