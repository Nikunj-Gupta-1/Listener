#!/usr/bin/env python3
import struct
import socket
import time
import statistics
from datetime import datetime
from typing import Dict, Any, Optional
from collections import defaultdict

class FlowKey:
    """Represents a network flow identifier"""
    def __init__(self, src_ip: str, dst_ip: str, src_port: int, dst_port: int, protocol: int):
        # Normalize flow direction (smaller IP:port first for bidirectional flows)
        if (src_ip, src_port) < (dst_ip, dst_port):
            self.ip1, self.port1 = src_ip, src_port
            self.ip2, self.port2 = dst_ip, dst_port
            self.is_forward = True
        else:
            self.ip1, self.port1 = dst_ip, dst_port
            self.ip2, self.port2 = src_ip, src_port
            self.is_forward = False
        self.protocol = protocol
    
    def __hash__(self):
        return hash((self.ip1, self.port1, self.ip2, self.port2, self.protocol))
    
    def __eq__(self, other):
        return (self.ip1, self.port1, self.ip2, self.port2, self.protocol) == \
               (other.ip1, other.port1, other.ip2, other.port2, other.protocol)

class FlowState:
    """Maintains state for a network flow"""
    def __init__(self):
        # Basic flow info
        self.start_time = None
        self.last_time = None
        self.total_packets = 0
        
        # Forward direction (from initiator)
        self.fwd_packets = 0
        self.fwd_bytes = 0
        self.fwd_packet_lengths = []
        self.fwd_inter_arrival_times = []
        self.fwd_last_time = None
        
        # Backward direction (to initiator)
        self.bwd_packets = 0
        self.bwd_bytes = 0
        self.bwd_packet_lengths = []
        self.bwd_inter_arrival_times = []
        self.bwd_last_time = None
        
        # All packets for general statistics
        self.all_packet_lengths = []
        self.all_inter_arrival_times = []
        self.last_packet_time = None
        
        # TCP specific
        self.tcp_flags_count = defaultdict(int)
        self.tcp_window_sizes = []
        
        # Flow activity periods
        self.active_periods = []
        self.idle_periods = []
        self.last_activity_time = None
        
    def update(self, packet_length: int, timestamp: float, is_forward: bool, tcp_flags: int = 0, tcp_window: int = 0):
        """Update flow state with new packet"""
        current_time = timestamp
        
        # Initialize timing
        if self.start_time is None:
            self.start_time = current_time
            self.last_activity_time = current_time
        
        # Update general statistics
        self.total_packets += 1
        self.all_packet_lengths.append(packet_length)
        self.last_time = current_time
        
        # Calculate inter-arrival time
        if self.last_packet_time is not None:
            inter_arrival = current_time - self.last_packet_time
            self.all_inter_arrival_times.append(inter_arrival)
        self.last_packet_time = current_time
        
        # Update direction-specific statistics
        if is_forward:
            self.fwd_packets += 1
            self.fwd_bytes += packet_length
            self.fwd_packet_lengths.append(packet_length)
            
            if self.fwd_last_time is not None:
                fwd_inter_arrival = current_time - self.fwd_last_time
                self.fwd_inter_arrival_times.append(fwd_inter_arrival)
            self.fwd_last_time = current_time
        else:
            self.bwd_packets += 1
            self.bwd_bytes += packet_length
            self.bwd_packet_lengths.append(packet_length)
            
            if self.bwd_last_time is not None:
                bwd_inter_arrival = current_time - self.bwd_last_time
                self.bwd_inter_arrival_times.append(bwd_inter_arrival)
            self.bwd_last_time = current_time
        
        # TCP specific updates
        if tcp_flags > 0:
            self.tcp_flags_count[tcp_flags] += 1
        if tcp_window > 0:
            self.tcp_window_sizes.append(tcp_window)
        
        # Activity tracking
        if self.last_activity_time is not None:
            idle_time = current_time - self.last_activity_time
            if idle_time > 1.0:  # 1 second idle threshold
                self.idle_periods.append(idle_time)
        self.last_activity_time = current_time

class NetworkFeatures:
    def __init__(self):
        # Basic connection info (5 features)
        self.src_ip = ""
        self.dst_ip = ""
        self.src_port = 0
        self.dst_port = 0
        self.protocol = 0
        
        # Packet characteristics (4 features)
        self.packet_length = 0
        self.header_length = 0
        self.ttl = 0
        self.tos = 0
        
        # TCP specific (8 features)
        self.tcp_flags = 0
        self.tcp_window = 0
        self.tcp_seq = 0
        self.tcp_ack = 0
        self.tcp_flag_fin = 0
        self.tcp_flag_syn = 0
        self.tcp_flag_rst = 0
        self.tcp_flag_psh = 0
        self.tcp_flag_ack = 0
        self.tcp_flag_urg = 0
        
        # Timing features (2 features)
        self.timestamp = 0
        self.flow_duration = 0
        
        # Flow packet counts (4 features)
        self.total_fwd_packets = 0
        self.total_bwd_packets = 0
        self.total_length_fwd_packets = 0
        self.total_length_bwd_packets = 0
        
        # Packet length statistics (6 features)
        self.packet_length_mean = 0.0
        self.packet_length_std = 0.0
        self.packet_length_min = 0
        self.packet_length_max = 0
        self.packet_length_variance = 0.0
        self.fwd_packet_length_mean = 0.0
        
        # Flow rate features (4 features)
        self.flow_bytes_per_second = 0.0
        self.flow_packets_per_second = 0.0
        self.fwd_packets_per_second = 0.0
        self.bwd_packets_per_second = 0.0
        
        # Inter-arrival time features (4 features)
        self.flow_inter_arrival_time_mean = 0.0
        self.flow_inter_arrival_time_std = 0.0
        self.fwd_inter_arrival_time_mean = 0.0
        self.bwd_inter_arrival_time_mean = 0.0
        
        # Activity features (4 features)
        self.active_mean = 0.0
        self.active_std = 0.0
        self.idle_mean = 0.0
        self.idle_std = 0.0
        
        # Additional features (3 features)
        self.tcp_window_size_mean = 0.0
        self.tcp_flags_count = 0
        self.flow_bytes_total = 0
        
        # Classification
        self.label = "BENIGN"

class PacketParser:
    # Class-level flow tracking
    flow_states = {}
    last_cleanup = time.time()
    
    @staticmethod
    def cleanup_old_flows():
        """Clean up flows older than 300 seconds"""
        current_time = time.time()
        if current_time - PacketParser.last_cleanup > 60:  # Cleanup every minute
            cutoff_time = current_time - 300  # 5 minutes
            flows_to_remove = []
            
            for flow_key, flow_state in PacketParser.flow_states.items():
                if flow_state.last_time and flow_state.last_time < cutoff_time:
                    flows_to_remove.append(flow_key)
            
            for flow_key in flows_to_remove:
                del PacketParser.flow_states[flow_key]
            
            PacketParser.last_cleanup = current_time
    
    @staticmethod
    def parse_ethernet_header(packet_data: bytes) -> tuple:
        """Parse Ethernet header (first 14 bytes)"""
        if len(packet_data) < 14:
            return None, None, None
        
        eth_header = struct.unpack('!6s6sH', packet_data[:14])
        dest_mac = ':'.join(['%02x' % b for b in eth_header[0]])
        src_mac = ':'.join(['%02x' % b for b in eth_header[1]])
        eth_type = eth_header[2]
        
        return dest_mac, src_mac, eth_type
    
    @staticmethod
    def parse_ip_header(packet_data: bytes, offset: int = 14) -> tuple:
        """Parse IP header"""
        if len(packet_data) < offset + 20:
            return None, None
        
        ip_header = struct.unpack('!BBHHHBBH4s4s', packet_data[offset:offset+20])
        
        version_ihl = ip_header[0]
        version = version_ihl >> 4
        ihl = version_ihl & 0xF
        header_length = ihl * 4
        
        tos = ip_header[1]
        total_length = ip_header[2]
        ttl = ip_header[5]
        protocol = ip_header[6]
        src_ip = socket.inet_ntoa(ip_header[8])
        dst_ip = socket.inet_ntoa(ip_header[9])
        
        ip_info = {
            'version': version,
            'header_length': header_length,
            'tos': tos,
            'total_length': total_length,
            'ttl': ttl,
            'protocol': protocol,
            'src_ip': src_ip,
            'dst_ip': dst_ip
        }
        
        return ip_info, offset + header_length
    
    @staticmethod
    def parse_tcp_header(packet_data: bytes, offset: int) -> dict:
        """Parse TCP header"""
        if len(packet_data) < offset + 20:
            return {}
        
        tcp_header = struct.unpack('!HHLLBBHHH', packet_data[offset:offset+20])
        
        src_port = tcp_header[0]
        dst_port = tcp_header[1]
        seq_num = tcp_header[2]
        ack_num = tcp_header[3]
        flags = tcp_header[5]
        window = tcp_header[6]
        
        tcp_info = {
            'src_port': src_port,
            'dst_port': dst_port,
            'seq_num': seq_num,
            'ack_num': ack_num,
            'flags': flags,
            'window': window,
            'flag_fin': flags & 0x01,
            'flag_syn': (flags & 0x02) >> 1,
            'flag_rst': (flags & 0x04) >> 2,
            'flag_psh': (flags & 0x08) >> 3,
            'flag_ack': (flags & 0x10) >> 4,
            'flag_urg': (flags & 0x20) >> 5
        }
        
        return tcp_info
    
    @staticmethod
    def parse_udp_header(packet_data: bytes, offset: int) -> dict:
        """Parse UDP header"""
        if len(packet_data) < offset + 8:
            return {}
        
        udp_header = struct.unpack('!HHHH', packet_data[offset:offset+8])
        
        return {
            'src_port': udp_header[0],
            'dst_port': udp_header[1],
            'length': udp_header[2],
            'checksum': udp_header[3]
        }
    
    @staticmethod
    def calculate_flow_statistics(flow_state: FlowState, current_time: float) -> dict:
        """Calculate comprehensive flow statistics"""
        stats = {}
        
        # Flow duration
        if flow_state.start_time:
            stats['flow_duration'] = current_time - flow_state.start_time
        else:
            stats['flow_duration'] = 0
        
        # Packet counts
        stats['total_fwd_packets'] = flow_state.fwd_packets
        stats['total_bwd_packets'] = flow_state.bwd_packets
        stats['total_length_fwd_packets'] = flow_state.fwd_bytes
        stats['total_length_bwd_packets'] = flow_state.bwd_bytes
        
        # Packet length statistics
        if flow_state.all_packet_lengths:
            stats['packet_length_mean'] = statistics.mean(flow_state.all_packet_lengths)
            stats['packet_length_std'] = statistics.stdev(flow_state.all_packet_lengths) if len(flow_state.all_packet_lengths) > 1 else 0
            stats['packet_length_min'] = min(flow_state.all_packet_lengths)
            stats['packet_length_max'] = max(flow_state.all_packet_lengths)
            stats['packet_length_variance'] = statistics.variance(flow_state.all_packet_lengths) if len(flow_state.all_packet_lengths) > 1 else 0
        else:
            stats['packet_length_mean'] = 0
            stats['packet_length_std'] = 0
            stats['packet_length_min'] = 0
            stats['packet_length_max'] = 0
            stats['packet_length_variance'] = 0
        
        # Forward packet length statistics
        if flow_state.fwd_packet_lengths:
            stats['fwd_packet_length_mean'] = statistics.mean(flow_state.fwd_packet_lengths)
        else:
            stats['fwd_packet_length_mean'] = 0
        
        # Flow rate calculations
        duration = stats['flow_duration']
        if duration > 0:
            total_bytes = flow_state.fwd_bytes + flow_state.bwd_bytes
            stats['flow_bytes_per_second'] = total_bytes / duration
            stats['flow_packets_per_second'] = flow_state.total_packets / duration
            stats['fwd_packets_per_second'] = flow_state.fwd_packets / duration
            stats['bwd_packets_per_second'] = flow_state.bwd_packets / duration
        else:
            stats['flow_bytes_per_second'] = 0
            stats['flow_packets_per_second'] = 0
            stats['fwd_packets_per_second'] = 0
            stats['bwd_packets_per_second'] = 0
        
        # Inter-arrival time statistics
        if flow_state.all_inter_arrival_times:
            stats['flow_inter_arrival_time_mean'] = statistics.mean(flow_state.all_inter_arrival_times)
            stats['flow_inter_arrival_time_std'] = statistics.stdev(flow_state.all_inter_arrival_times) if len(flow_state.all_inter_arrival_times) > 1 else 0
        else:
            stats['flow_inter_arrival_time_mean'] = 0
            stats['flow_inter_arrival_time_std'] = 0
        
        if flow_state.fwd_inter_arrival_times:
            stats['fwd_inter_arrival_time_mean'] = statistics.mean(flow_state.fwd_inter_arrival_times)
        else:
            stats['fwd_inter_arrival_time_mean'] = 0
        
        if flow_state.bwd_inter_arrival_times:
            stats['bwd_inter_arrival_time_mean'] = statistics.mean(flow_state.bwd_inter_arrival_times)
        else:
            stats['bwd_inter_arrival_time_mean'] = 0
        
        # Activity statistics
        if flow_state.active_periods:
            stats['active_mean'] = statistics.mean(flow_state.active_periods)
            stats['active_std'] = statistics.stdev(flow_state.active_periods) if len(flow_state.active_periods) > 1 else 0
        else:
            stats['active_mean'] = 0
            stats['active_std'] = 0
        
        if flow_state.idle_periods:
            stats['idle_mean'] = statistics.mean(flow_state.idle_periods)
            stats['idle_std'] = statistics.stdev(flow_state.idle_periods) if len(flow_state.idle_periods) > 1 else 0
        else:
            stats['idle_mean'] = 0
            stats['idle_std'] = 0
        
        # TCP specific statistics
        if flow_state.tcp_window_sizes:
            stats['tcp_window_size_mean'] = statistics.mean(flow_state.tcp_window_sizes)
        else:
            stats['tcp_window_size_mean'] = 0
        
        stats['tcp_flags_count'] = sum(flow_state.tcp_flags_count.values())
        stats['flow_bytes_total'] = flow_state.fwd_bytes + flow_state.bwd_bytes
        
        return stats
    
    @staticmethod
    def parse_packet(packet_data: bytes, timestamp: float) -> NetworkFeatures:
        """Main packet parsing function with comprehensive feature extraction"""
        features = NetworkFeatures()
        features.timestamp = int(timestamp * 1000000)  # Convert to microseconds
        features.packet_length = len(packet_data)
        
        # Clean up old flows periodically
        PacketParser.cleanup_old_flows()
        
        try:
            # Parse Ethernet header
            dest_mac, src_mac, eth_type = PacketParser.parse_ethernet_header(packet_data)
            
            # Check for IPv4 (0x0800)
            if eth_type == 0x0800:
                ip_info, tcp_offset = PacketParser.parse_ip_header(packet_data)
                
                if ip_info:
                    features.src_ip = ip_info['src_ip']
                    features.dst_ip = ip_info['dst_ip']
                    features.protocol = ip_info['protocol']
                    features.ttl = ip_info['ttl']
                    features.tos = ip_info['tos']
                    features.header_length = ip_info['header_length']
                    
                    tcp_flags = 0
                    tcp_window = 0
                    
                    # Parse transport layer
                    if ip_info['protocol'] == 6:  # TCP
                        tcp_info = PacketParser.parse_tcp_header(packet_data, tcp_offset)
                        if tcp_info:
                            features.src_port = tcp_info['src_port']
                            features.dst_port = tcp_info['dst_port']
                            features.tcp_seq = tcp_info['seq_num']
                            features.tcp_ack = tcp_info['ack_num']
                            features.tcp_flags = tcp_info['flags']
                            features.tcp_window = tcp_info['window']
                            features.tcp_flag_fin = tcp_info['flag_fin']
                            features.tcp_flag_syn = tcp_info['flag_syn']
                            features.tcp_flag_rst = tcp_info['flag_rst']
                            features.tcp_flag_psh = tcp_info['flag_psh']
                            features.tcp_flag_ack = tcp_info['flag_ack']
                            features.tcp_flag_urg = tcp_info['flag_urg']
                            
                            tcp_flags = tcp_info['flags']
                            tcp_window = tcp_info['window']
                    
                    elif ip_info['protocol'] == 17:  # UDP
                        udp_info = PacketParser.parse_udp_header(packet_data, tcp_offset)
                        if udp_info:
                            features.src_port = udp_info['src_port']
                            features.dst_port = udp_info['dst_port']
                    
                    # Create flow key and update flow state
                    flow_key = FlowKey(
                        features.src_ip, features.dst_ip,
                        features.src_port, features.dst_port,
                        features.protocol
                    )
                    
                    # Initialize or get existing flow state
                    if flow_key not in PacketParser.flow_states:
                        PacketParser.flow_states[flow_key] = FlowState()
                    
                    flow_state = PacketParser.flow_states[flow_key]
                    
                    # Update flow state
                    flow_state.update(
                        packet_length=features.packet_length,
                        timestamp=timestamp,
                        is_forward=flow_key.is_forward,
                        tcp_flags=tcp_flags,
                        tcp_window=tcp_window
                    )
                    
                    # Calculate flow statistics
                    flow_stats = PacketParser.calculate_flow_statistics(flow_state, timestamp)
                    
                    # Update features with flow statistics (30+ features total)
                    features.flow_duration = flow_stats['flow_duration']
                    features.total_fwd_packets = flow_stats['total_fwd_packets']
                    features.total_bwd_packets = flow_stats['total_bwd_packets']
                    features.total_length_fwd_packets = flow_stats['total_length_fwd_packets']
                    features.total_length_bwd_packets = flow_stats['total_length_bwd_packets']
                    features.packet_length_mean = flow_stats['packet_length_mean']
                    features.packet_length_std = flow_stats['packet_length_std']
                    features.packet_length_min = flow_stats['packet_length_min']
                    features.packet_length_max = flow_stats['packet_length_max']
                    features.packet_length_variance = flow_stats['packet_length_variance']
                    features.fwd_packet_length_mean = flow_stats['fwd_packet_length_mean']
                    features.flow_bytes_per_second = flow_stats['flow_bytes_per_second']
                    features.flow_packets_per_second = flow_stats['flow_packets_per_second']
                    features.fwd_packets_per_second = flow_stats['fwd_packets_per_second']
                    features.bwd_packets_per_second = flow_stats['bwd_packets_per_second']
                    features.flow_inter_arrival_time_mean = flow_stats['flow_inter_arrival_time_mean']
                    features.flow_inter_arrival_time_std = flow_stats['flow_inter_arrival_time_std']
                    features.fwd_inter_arrival_time_mean = flow_stats['fwd_inter_arrival_time_mean']
                    features.bwd_inter_arrival_time_mean = flow_stats['bwd_inter_arrival_time_mean']
                    features.active_mean = flow_stats['active_mean']
                    features.active_std = flow_stats['active_std']
                    features.idle_mean = flow_stats['idle_mean']
                    features.idle_std = flow_stats['idle_std']
                    features.tcp_window_size_mean = flow_stats['tcp_window_size_mean']
                    features.tcp_flags_count = flow_stats['tcp_flags_count']
                    features.flow_bytes_total = flow_stats['flow_bytes_total']
        
        except Exception as e:
            # If parsing fails, return basic features
            features.label = "PARSING_ERROR"
        
        return features
