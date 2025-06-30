#!/usr/bin/env python3
import json
from datetime import datetime
from src.packet_parser import NetworkFeatures

class JSONConverter:
    @staticmethod
    def features_to_dict(features: NetworkFeatures) -> dict:
        """Convert NetworkFeatures object to dictionary"""
        return {
            # Basic network information (5 features)
            'src_ip': features.src_ip,
            'dst_ip': features.dst_ip,
            'src_port': features.src_port,
            'dst_port': features.dst_port,
            'protocol': features.protocol,
            
            # Packet characteristics (4 features)
            'packet_length': features.packet_length,
            'header_length': features.header_length,
            'ttl': features.ttl,
            'tos': features.tos,
            'timestamp': features.timestamp,
            
            # TCP specific features (8 features)
            'tcp_flags': features.tcp_flags,
            'tcp_window': features.tcp_window,
            'tcp_seq': features.tcp_seq,
            'tcp_ack': features.tcp_ack,
            'tcp_flag_fin': features.tcp_flag_fin,
            'tcp_flag_syn': features.tcp_flag_syn,
            'tcp_flag_rst': features.tcp_flag_rst,
            'tcp_flag_psh': features.tcp_flag_psh,
            'tcp_flag_ack': features.tcp_flag_ack,
            'tcp_flag_urg': features.tcp_flag_urg,
            
            # Flow timing (2 features)
            'flow_duration': features.flow_duration,
            
            # Flow packet counts (4 features)
            'total_fwd_packets': features.total_fwd_packets,
            'total_bwd_packets': features.total_bwd_packets,
            'total_length_fwd_packets': features.total_length_fwd_packets,
            'total_length_bwd_packets': features.total_length_bwd_packets,
            
            # Packet length statistics (6 features)
            'packet_length_mean': features.packet_length_mean,
            'packet_length_std': features.packet_length_std,
            'packet_length_min': features.packet_length_min,
            'packet_length_max': features.packet_length_max,
            'packet_length_variance': features.packet_length_variance,
            'fwd_packet_length_mean': features.fwd_packet_length_mean,
            
            # Flow rate features (4 features)
            'flow_bytes_per_second': features.flow_bytes_per_second,
            'flow_packets_per_second': features.flow_packets_per_second,
            'fwd_packets_per_second': features.fwd_packets_per_second,
            'bwd_packets_per_second': features.bwd_packets_per_second,
            
            # Inter-arrival time features (4 features)
            'flow_inter_arrival_time_mean': features.flow_inter_arrival_time_mean,
            'flow_inter_arrival_time_std': features.flow_inter_arrival_time_std,
            'fwd_inter_arrival_time_mean': features.fwd_inter_arrival_time_mean,
            'bwd_inter_arrival_time_mean': features.bwd_inter_arrival_time_mean,
            
            # Activity features (4 features)
            'active_mean': features.active_mean,
            'active_std': features.active_std,
            'idle_mean': features.idle_mean,
            'idle_std': features.idle_std,
            
            # Additional features (3 features)
            'tcp_window_size_mean': features.tcp_window_size_mean,
            'tcp_flags_count': features.tcp_flags_count,
            'flow_bytes_total': features.flow_bytes_total,
            
            # Classification
            'label': features.label,
            
            # Metadata
            'capture_timestamp': datetime.now().isoformat(),
            'protocol_name': JSONConverter.get_protocol_name(features.protocol)
        }
    
    @staticmethod
    def features_to_json(features: NetworkFeatures) -> str:
        """Convert NetworkFeatures to JSON string"""
        feature_dict = JSONConverter.features_to_dict(features)
        return json.dumps(feature_dict, default=str)
    
    @staticmethod
    def get_protocol_name(protocol_num: int) -> str:
        """Convert protocol number to name"""
        protocol_map = {
            1: 'ICMP',
            6: 'TCP',
            17: 'UDP',
            47: 'GRE',
            50: 'ESP'
        }
        return protocol_map.get(protocol_num, f'UNKNOWN_{protocol_num}')
