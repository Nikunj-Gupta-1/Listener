#!/usr/bin/env python3
import signal
import sys
import time
import logging
from src.dpdk.packet_capture import DPDKPacketCapture
from src.packet_parser import PacketParser
from src.kafka_producer import KafkaProducerClient
from src.json_converter import JSONConverter

class NetworkCaptureApplication:
    def __init__(self):
        self.capture = DPDKPacketCapture()
        self.kafka_producer = KafkaProducerClient()
        self.running = True
        self.start_time = time.time()
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down gracefully...")
        self.running = False
    
    def packet_callback(self, packet_data: bytes, timestamp: float):
        """Process captured packets"""
        try:
            # Parse packet into features
            features = PacketParser.parse_packet(packet_data, timestamp)
            
            # Convert to dictionary for Kafka
            feature_dict = JSONConverter.features_to_dict(features)
            
            # Send to Kafka
            success = self.kafka_producer.send_message(feature_dict)
            
            if not success:
                self.logger.warning("Failed to send packet to Kafka")
                
        except Exception as e:
            self.logger.error(f"Error processing packet: {e}")
    
    def run(self):
        """Main application loop"""
        self.logger.info("Starting DPDK Network Capture Application")
        
        try:
            # Initialize DPDK packet capture
            if not self.capture.initialize():
                self.logger.error("Failed to initialize DPDK packet capture")
                return False
            
            # Start packet capture
            self.capture.start_capture(self.packet_callback)
            
        except Exception as e:
            self.logger.error(f"Application error: {e}")
            return False
        finally:
            self.cleanup()
        
        return True
    
    def cleanup(self):
        """Clean up resources"""
        self.logger.info("Cleaning up resources...")
        
        # Stop capture
        if self.capture:
            self.capture.stop_capture()
        
        # Close Kafka producer
        if self.kafka_producer:
            self.kafka_producer.close()
        
        # Print final statistics
        self.print_final_stats()
    
    def print_final_stats(self):
        """Print final application statistics"""
        runtime = time.time() - self.start_time
        capture_stats = self.capture.get_stats()
        kafka_stats = self.kafka_producer.get_stats()
        
        self.logger.info("=== Final Statistics ===")
        self.logger.info(f"Runtime: {runtime:.2f} seconds")
        self.logger.info(f"Packets captured: {capture_stats['total_packets']}")
        self.logger.info(f"Messages sent: {kafka_stats['messages_sent']}")
        self.logger.info(f"Kafka errors: {kafka_stats['errors']}")
        
        if runtime > 0:
            pps = capture_stats['total_packets'] / runtime
            self.logger.info(f"Average packets per second: {pps:.2f}")

def main():
    """Main entry point"""
    app = NetworkCaptureApplication()
    success = app.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
