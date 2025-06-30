#!/usr/bin/env python3
import json
import logging
import configparser
from confluent_kafka import Producer
from typing import Optional, Callable

class KafkaProducerClient:
    def __init__(self, config_file: str = "config/kafka_config.ini"):
        self.config = configparser.ConfigParser()
        self.config.read(config_file)
        
        # Kafka configuration
        self.bootstrap_servers = self.config.get('kafka', 'bootstrap_servers', fallback='localhost:9092')
        self.topic = self.config.get('kafka', 'topic', fallback='network-flows')
        self.client_id = self.config.get('kafka', 'client_id', fallback='packet-capture-python')
        
        # Producer configuration
        producer_config = {
            'bootstrap.servers': self.bootstrap_servers,
            'client.id': self.client_id,
            'batch.size': self.config.getint('producer', 'batch_size', fallback=16384),
            'linger.ms': self.config.getint('producer', 'linger_ms', fallback=10),
            'compression.type': self.config.get('producer', 'compression_type', fallback='lz4'),
            'acks': self.config.getint('producer', 'acks', fallback=1),
            'retries': self.config.getint('producer', 'retries', fallback=3),
            'max.in.flight.requests.per.connection': self.config.getint('producer', 'max_in_flight_requests', fallback=5),
            'buffer.memory': self.config.getint('performance', 'buffer_memory', fallback=33554432),
            'send.buffer.bytes': self.config.getint('performance', 'send_buffer_bytes', fallback=131072),
            'receive.buffer.bytes': self.config.getint('performance', 'receive_buffer_bytes', fallback=65536)
        }
        
        self.producer = Producer(producer_config)
        self.message_count = 0
        self.error_count = 0
        
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        self.logger.info(f"Kafka producer initialized for topic: {self.topic}")
    
    def delivery_callback(self, err, msg):
        """Callback for message delivery reports"""
        if err is not None:
            self.error_count += 1
            self.logger.error(f'Message delivery failed: {err}')
        else:
            self.message_count += 1
            if self.message_count % 1000 == 0:
                self.logger.info(f'Delivered {self.message_count} messages to {msg.topic()}')
    
    def send_message(self, message_data: dict, key: Optional[str] = None) -> bool:
        """Send message to Kafka topic"""
        try:
            # Convert message to JSON
            json_message = json.dumps(message_data, default=str)
            
            # Generate key if not provided (use src_ip:src_port)
            if key is None:
                key = f"{message_data.get('src_ip', 'unknown')}:{message_data.get('src_port', 0)}"
            
            # Send message
            self.producer.produce(
                topic=self.topic,
                value=json_message,
                key=key,
                callback=self.delivery_callback
            )
            
            # Poll for delivery reports
            self.producer.poll(0)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send message: {e}")
            return False
    
    def flush(self, timeout: float = 10.0):
        """Flush pending messages"""
        self.logger.info("Flushing pending messages...")
        self.producer.flush(timeout)
    
    def close(self):
        """Close producer and clean up"""
        self.flush()
        self.logger.info(f"Producer closed. Messages sent: {self.message_count}, Errors: {self.error_count}")
    
    def get_stats(self) -> dict:
        """Get producer statistics"""
        return {
            'messages_sent': self.message_count,
            'errors': self.error_count,
            'topic': self.topic,
            'bootstrap_servers': self.bootstrap_servers
        }
