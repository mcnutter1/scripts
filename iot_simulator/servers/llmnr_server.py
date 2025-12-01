#!/usr/bin/env python3
"""
LLMNR (Link-Local Multicast Name Resolution) Server
Implements Microsoft's LLMNR protocol on UDP port 5355
Allows Windows systems to resolve the printer hostname
"""
import sys
import os
import socket
import struct
import threading
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core_logger import get_logger
from shared import parse_args

logger = get_logger("llmnr_server")

# Global config variables
HOSTNAME = ""
IP = ""

# LLMNR multicast group
LLMNR_MULTICAST_GROUP = '224.0.0.252'
LLMNR_PORT = 5355


class LLMNRServer:
    """LLMNR server for Windows hostname resolution"""
    
    def __init__(self):
        self.sock = None
        self.running = False
        
    def start(self):
        """Start the LLMNR server"""
        try:
            # Create UDP socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Bind to the LLMNR port
            self.sock.bind(('', LLMNR_PORT))
            
            # Join multicast group
            mreq = struct.pack("4sl", socket.inet_aton(LLMNR_MULTICAST_GROUP), socket.INADDR_ANY)
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            
            logger.info(f"LLMNR server listening on port {LLMNR_PORT}")
            print(f"LLMNR server listening on UDP port {LLMNR_PORT} (Windows hostname resolution)")
            
            self.running = True
            
            # Listen for LLMNR queries
            while self.running:
                try:
                    data, addr = self.sock.recvfrom(512)
                    # Handle in separate thread
                    thread = threading.Thread(target=self.handle_query, args=(data, addr))
                    thread.daemon = True
                    thread.start()
                    
                except Exception as e:
                    if self.running:
                        logger.error(f"Error receiving LLMNR packet: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to start LLMNR server: {e}")
            raise
        finally:
            if self.sock:
                self.sock.close()
    
    def handle_query(self, data, addr):
        """Handle incoming LLMNR query"""
        try:
            if len(data) < 12:
                return
                
            # Parse DNS-like query
            transaction_id = data[0:2]
            flags = struct.unpack('>H', data[2:4])[0]
            
            # Check if it's a query (QR bit = 0)
            if flags & 0x8000:
                return  # It's a response, ignore
            
            # Extract the queried name
            query_name = self.parse_dns_name(data, 12)
            
            if not query_name:
                return
                
            # Convert to lowercase for comparison
            query_name_lower = query_name.lower()
            hostname_lower = HOSTNAME.lower()
            
            # Check if query matches our hostname
            if query_name_lower == hostname_lower or query_name_lower == hostname_lower + '.local':
                logger.info(f"LLMNR query for {query_name} from {addr[0]} - responding with {IP}")
                print(f"[LLMNR] Query for '{query_name}' from {addr[0]} - responding")
                self.send_response(transaction_id, query_name, addr)
            
        except Exception as e:
            logger.error(f"Error handling LLMNR query: {e}")
    
    def parse_dns_name(self, data, offset):
        """Parse DNS name from packet"""
        try:
            labels = []
            pos = offset
            
            while pos < len(data):
                length = data[pos]
                if length == 0:
                    break
                if length > 63:  # Compression pointer
                    break
                    
                pos += 1
                if pos + length > len(data):
                    break
                    
                label = data[pos:pos+length].decode('utf-8', errors='ignore')
                labels.append(label)
                pos += length
            
            return '.'.join(labels) if labels else None
            
        except Exception as e:
            logger.error(f"Error parsing DNS name: {e}")
            return None
    
    def encode_dns_name(self, name):
        """Encode a DNS name"""
        encoded = b''
        for label in name.split('.'):
            if label:
                encoded += bytes([len(label)]) + label.encode('utf-8')
        encoded += b'\x00'
        return encoded
    
    def send_response(self, transaction_id, query_name, addr):
        """Send LLMNR response"""
        try:
            # Build LLMNR response
            # Transaction ID (2 bytes)
            response = transaction_id
            
            # Flags: Response (1), Opcode (0), AA (1), TC (0), RD (0), RA (0), Z (0), RCODE (0)
            # QR=1, Opcode=0, AA=1, TC=0, RD=0, RA=0, Z=0, RCODE=0
            flags = 0x8400  # 1000 0100 0000 0000
            response += struct.pack('>H', flags)
            
            # Questions (1)
            response += struct.pack('>H', 1)
            
            # Answers (1)
            response += struct.pack('>H', 1)
            
            # Authority RRs (0)
            response += struct.pack('>H', 0)
            
            # Additional RRs (0)
            response += struct.pack('>H', 0)
            
            # Question section
            response += self.encode_dns_name(query_name)
            response += struct.pack('>H', 1)  # Type A
            response += struct.pack('>H', 1)  # Class IN
            
            # Answer section
            response += self.encode_dns_name(query_name)
            response += struct.pack('>H', 1)  # Type A
            response += struct.pack('>H', 1)  # Class IN
            response += struct.pack('>I', 30)  # TTL (30 seconds)
            response += struct.pack('>H', 4)  # Data length (4 bytes for IPv4)
            
            # IP address
            ip_parts = [int(x) for x in IP.split('.')]
            response += bytes(ip_parts)
            
            # Send unicast response
            self.sock.sendto(response, addr)
            logger.info(f"Sent LLMNR response to {addr[0]}")
            
        except Exception as e:
            logger.error(f"Error sending LLMNR response: {e}")
    
    def stop(self):
        """Stop the server"""
        self.running = False
        if self.sock:
            self.sock.close()


def run(port=5355):
    """Start the LLMNR server"""
    server = LLMNRServer()
    server.start()


if __name__ == "__main__":
    port, config = parse_args()
    
    # Load global config
    HOSTNAME = config.get('hostname', 'HPLJ')
    IP = config.get('ip', '192.168.1.100')
    
    logger.info(f"Starting LLMNR server for {HOSTNAME} ({IP})")
    
    run(port)
