#!/usr/bin/env python3
"""
HP Printer SNMP Server Simulator
Responds to SNMP queries with printer-specific OIDs
"""
import sys
import os
import socket
import struct
from datetime import datetime
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core_logger import get_logger
from shared import parse_args

logger = get_logger("snmp_server")

# Global config variables
SYSTEM_NAME = ""
IP = ""
MAC = ""
HOSTNAME = ""
SERIAL = ""
MODEL = ""
FIRMWARE = ""
LOCATION = ""
CONTACT = ""
PAGE_COUNT = 0
TONER_LEVEL = 0
TONER_CAPACITY = 0

# SNMP BER encoding types
INTEGER = 0x02
OCTET_STRING = 0x04
NULL = 0x05
OBJECT_IDENTIFIER = 0x06
SEQUENCE = 0x30
GET_REQUEST = 0xa0
GET_NEXT_REQUEST = 0xa1
GET_RESPONSE = 0xa2

# Common OIDs for HP printers
OID_MAP = {
    # System group (1.3.6.1.2.1.1)
    '1.3.6.1.2.1.1.1.0': lambda: (OCTET_STRING, f"HP {MODEL} {FIRMWARE}"),  # sysDescr
    '1.3.6.1.2.1.1.2.0': lambda: (OBJECT_IDENTIFIER, '1.3.6.1.4.1.11.2.3.9.1'),  # sysObjectID (HP)
    '1.3.6.1.2.1.1.3.0': lambda: (INTEGER, 123456789),  # sysUpTime
    '1.3.6.1.2.1.1.4.0': lambda: (OCTET_STRING, CONTACT),  # sysContact
    '1.3.6.1.2.1.1.5.0': lambda: (OCTET_STRING, HOSTNAME),  # sysName
    '1.3.6.1.2.1.1.6.0': lambda: (OCTET_STRING, LOCATION),  # sysLocation
    '1.3.6.1.2.1.1.7.0': lambda: (INTEGER, 72),  # sysServices
    
    # Interfaces (1.3.6.1.2.1.2)
    '1.3.6.1.2.1.2.1.0': lambda: (INTEGER, 1),  # ifNumber
    '1.3.6.1.2.1.2.2.1.1.1': lambda: (INTEGER, 1),  # ifIndex
    '1.3.6.1.2.1.2.2.1.2.1': lambda: (OCTET_STRING, "Ethernet"),  # ifDescr
    '1.3.6.1.2.1.2.2.1.3.1': lambda: (INTEGER, 6),  # ifType (ethernet-csmacd)
    '1.3.6.1.2.1.2.2.1.6.1': lambda: (OCTET_STRING, bytes.fromhex(MAC.replace(':', ''))),  # ifPhysAddress
    '1.3.6.1.2.1.2.2.1.8.1': lambda: (INTEGER, 1),  # ifOperStatus (up)
    
    # HR Device (1.3.6.1.2.1.25)
    '1.3.6.1.2.1.25.3.2.1.2.1': lambda: (OCTET_STRING, f"HP {MODEL}"),  # hrDeviceDescr
    '1.3.6.1.2.1.25.3.2.1.3.1': lambda: (OBJECT_IDENTIFIER, '1.3.6.1.2.1.25.3.1.5'),  # hrDeviceID (printer)
    '1.3.6.1.2.1.25.3.2.1.5.1': lambda: (INTEGER, 5),  # hrDeviceStatus (running)
    '1.3.6.1.2.1.25.3.5.1.1.1': lambda: (INTEGER, 1),  # hrPrinterStatus (idle)
    '1.3.6.1.2.1.25.3.5.1.2.1': lambda: (OCTET_STRING, b'\x00\x00'),  # hrPrinterDetectedErrorState
    
    # Printer MIB (1.3.6.1.2.1.43)
    '1.3.6.1.2.1.43.5.1.1.1.1': lambda: (INTEGER, 5),  # prtGeneralConfigChanges
    '1.3.6.1.2.1.43.5.1.1.2.1': lambda: (INTEGER, 5),  # prtGeneralCurrentLocalization
    '1.3.6.1.2.1.43.5.1.1.3.1': lambda: (INTEGER, 1),  # prtGeneralReset (notResetting)
    '1.3.6.1.2.1.43.5.1.1.16.1': lambda: (OCTET_STRING, SERIAL),  # prtGeneralSerialNumber
    '1.3.6.1.2.1.43.8.2.1.9.1.1': lambda: (INTEGER, 3),  # prtInputCurrentLevel (tray status)
    '1.3.6.1.2.1.43.9.2.1.2.1.1': lambda: (INTEGER, 0),  # prtOutputStatus (none/other)
    '1.3.6.1.2.1.43.10.2.1.4.1.1': lambda: (INTEGER, PAGE_COUNT),  # prtMarkerLifeCount (page count)
    '1.3.6.1.2.1.43.10.2.1.5.1.1': lambda: (INTEGER, 600),  # prtMarkerCounterUnit
    '1.3.6.1.2.1.43.11.1.1.6.1.1': lambda: (INTEGER, TONER_LEVEL),  # prtMarkerSuppliesLevel
    '1.3.6.1.2.1.43.11.1.1.8.1.1': lambda: (INTEGER, TONER_CAPACITY),  # prtMarkerSuppliesMaxCapacity
    '1.3.6.1.2.1.43.11.1.1.9.1.1': lambda: (INTEGER, 3),  # prtMarkerSuppliesClass (supplyThatIsConsumed)
    
    # HP Enterprise OIDs (1.3.6.1.4.1.11)
    '1.3.6.1.4.1.11.2.3.9.4.2.1.1.3.3.0': lambda: (OCTET_STRING, MODEL),  # Model
    '1.3.6.1.4.1.11.2.3.9.4.2.1.1.3.6.0': lambda: (OCTET_STRING, SERIAL),  # Serial
    '1.3.6.1.4.1.11.2.3.9.4.2.1.3.5.1.0': lambda: (INTEGER, TONER_LEVEL),  # Black toner level
    '1.3.6.1.4.1.11.2.3.9.4.2.1.4.1.2.1.0': lambda: (INTEGER, PAGE_COUNT),  # Total pages
    '1.3.6.1.4.1.11.2.3.9.4.2.1.4.1.2.6.0': lambda: (INTEGER, 0),  # Jam events
    '1.3.6.1.4.1.11.2.3.9.4.2.1.1.6.5.0': lambda: (OCTET_STRING, FIRMWARE),  # Firmware version
}


class SNMPSimulator:
    def __init__(self, port=161):
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
    def start(self):
        try:
            self.sock.bind(('', self.port))
            logger.info(f"SNMP server listening on port {self.port}")
            print(f"SNMP server listening on port {self.port}")
            
            while True:
                try:
                    data, addr = self.sock.recvfrom(4096)
                    logger.info(f"Received SNMP request from {addr[0]}:{addr[1]}")
                    response = self.process_snmp_request(data)
                    if response:
                        self.sock.sendto(response, addr)
                        logger.info(f"Sent SNMP response to {addr[0]}:{addr[1]}")
                except Exception as e:
                    logger.error(f"Error processing SNMP request: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to start SNMP server: {e}")
            raise
        finally:
            self.sock.close()
    
    def process_snmp_request(self, data):
        """Process SNMP request and generate response"""
        try:
            # Basic SNMP packet parsing
            if len(data) < 10:
                return None
                
            # Extract OID from request (simplified parsing)
            oid = self.extract_oid(data)
            if not oid:
                logger.warning("Could not extract OID from request")
                return None
                
            logger.info(f"Requested OID: {oid}")
            
            # Look up OID in map
            if oid in OID_MAP:
                value_type, value = OID_MAP[oid]()
                logger.info(f"Responding with value for OID {oid}: {value}")
                return self.create_snmp_response(data, oid, value_type, value)
            else:
                # Try to find next OID for GetNext requests
                logger.warning(f"OID {oid} not found in map")
                return self.create_error_response(data)
                
        except Exception as e:
            logger.error(f"Error processing SNMP request: {e}")
            return None
    
    def extract_oid(self, data):
        """Extract OID from SNMP request packet"""
        try:
            # Look for OID pattern in the data
            # This is a simplified extraction - real SNMP would use full BER decoding
            pos = 0
            while pos < len(data) - 2:
                if data[pos] == OBJECT_IDENTIFIER:
                    oid_len = data[pos + 1]
                    if pos + 2 + oid_len <= len(data):
                        oid_bytes = data[pos + 2:pos + 2 + oid_len]
                        oid = self.decode_oid(oid_bytes)
                        if oid and oid.startswith('1.3.6.1'):
                            return oid
                pos += 1
            return None
        except:
            return None
    
    def decode_oid(self, oid_bytes):
        """Decode BER-encoded OID"""
        try:
            if len(oid_bytes) < 1:
                return None
                
            # First byte encodes first two nodes
            first_byte = oid_bytes[0]
            first = first_byte // 40
            second = first_byte % 40
            oid = [str(first), str(second)]
            
            # Decode remaining subidentifiers
            i = 1
            while i < len(oid_bytes):
                subid = 0
                while True:
                    if i >= len(oid_bytes):
                        break
                    byte = oid_bytes[i]
                    subid = (subid << 7) | (byte & 0x7F)
                    i += 1
                    if not (byte & 0x80):
                        break
                oid.append(str(subid))
                
            return '.'.join(oid)
        except:
            return None
    
    def create_snmp_response(self, request, oid, value_type, value):
        """Create SNMP GetResponse packet"""
        try:
            # This is a simplified SNMP response generator
            # A real implementation would properly encode all SNMP fields
            
            # Encode OID
            oid_encoded = self.encode_oid(oid)
            
            # Encode value
            if value_type == OCTET_STRING:
                if isinstance(value, bytes):
                    value_encoded = self.encode_bytes(OCTET_STRING, value)
                else:
                    value_encoded = self.encode_string(value)
            elif value_type == INTEGER:
                value_encoded = self.encode_integer(value)
            elif value_type == OBJECT_IDENTIFIER:
                value_encoded = self.encode_oid(value)
            else:
                value_encoded = b'\x05\x00'  # NULL
            
            # Build varbind
            varbind = oid_encoded + value_encoded
            varbind = bytes([SEQUENCE, len(varbind)]) + varbind
            
            # Build varbind list
            varbind_list = bytes([SEQUENCE, len(varbind)]) + varbind
            
            # Request ID, Error Status, Error Index (simplified - use from request)
            pdu_header = b'\x02\x01\x01\x02\x01\x00\x02\x01\x00'  # Simplified
            
            # Build PDU
            pdu_content = pdu_header + varbind_list
            pdu = bytes([GET_RESPONSE, len(pdu_content)]) + pdu_content
            
            # Community string (public)
            community = b'\x04\x06public'
            
            # Version (SNMPv1 = 0)
            version = b'\x02\x01\x00'
            
            # Build message
            message_content = version + community + pdu
            message = bytes([SEQUENCE, len(message_content)]) + message_content
            
            return message
            
        except Exception as e:
            logger.error(f"Error creating SNMP response: {e}")
            return None
    
    def create_error_response(self, request):
        """Create SNMP error response for unknown OID"""
        # Simplified error response - noSuchName
        return None
    
    def encode_oid(self, oid_str):
        """Encode OID string to BER format"""
        parts = [int(x) for x in oid_str.split('.')]
        if len(parts) < 2:
            return b''
        
        # First byte encodes first two nodes
        result = [parts[0] * 40 + parts[1]]
        
        # Encode remaining subidentifiers
        for subid in parts[2:]:
            if subid < 128:
                result.append(subid)
            else:
                # Multi-byte encoding
                encoded = []
                while subid > 0:
                    encoded.insert(0, (subid & 0x7F) | (0x80 if encoded else 0))
                    subid >>= 7
                result.extend(encoded)
        
        oid_bytes = bytes(result)
        return bytes([OBJECT_IDENTIFIER, len(oid_bytes)]) + oid_bytes
    
    def encode_string(self, s):
        """Encode string to BER format"""
        s_bytes = s.encode('utf-8')
        return bytes([OCTET_STRING, len(s_bytes)]) + s_bytes
    
    def encode_bytes(self, tag, data):
        """Encode bytes with tag"""
        return bytes([tag, len(data)]) + data
    
    def encode_integer(self, value):
        """Encode integer to BER format"""
        # Convert to bytes
        if value == 0:
            int_bytes = b'\x00'
        else:
            # Handle positive integers
            int_bytes = []
            temp = abs(value)
            while temp > 0:
                int_bytes.insert(0, temp & 0xFF)
                temp >>= 8
            
            # Add sign byte if necessary
            if int_bytes[0] & 0x80:
                int_bytes.insert(0, 0)
            
            int_bytes = bytes(int_bytes)
        
        return bytes([INTEGER, len(int_bytes)]) + int_bytes


def run(port=161):
    """Start the SNMP server"""
    server = SNMPSimulator(port)
    server.start()


if __name__ == "__main__":
    port, config = parse_args()
    
    # Load global config
    SYSTEM_NAME = config.get('system_name', 'HP LaserJet')
    IP = config.get('ip', '192.168.1.100')
    MAC = config.get('mac', '00:00:00:00:00:00')
    HOSTNAME = config.get('hostname', 'HPLJ')
    SERIAL = config.get('serial', 'UNKNOWN')
    MODEL = config.get('model', 'HP LaserJet')
    FIRMWARE = config.get('firmware', '1.0.0')
    LOCATION = config.get('location', 'Office')
    CONTACT = config.get('contact', 'Admin')
    PAGE_COUNT = config.get('page_count', 0)
    TONER_LEVEL = config.get('toner_level', 100)
    TONER_CAPACITY = config.get('toner_capacity', 10000)
    
    logger.info(f"Starting SNMP server for {MODEL} (S/N: {SERIAL})")
    
    run(port)
