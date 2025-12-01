#!/usr/bin/env python3
"""
WS-Discovery Server for Windows Printer Discovery
Implements Web Services Discovery protocol on UDP port 3702
This enables Windows 'Add Printer' wizard to discover the printer
"""
import sys
import os
import socket
import struct
import threading
import uuid
from datetime import datetime
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core_logger import get_logger
from shared import parse_args

logger = get_logger("ws_discovery")

# Global config variables
SYSTEM_NAME = ""
IP = ""
MAC = ""
HOSTNAME = ""
SERIAL = ""
MODEL = ""
UUID = ""

# WS-Discovery multicast group
WSD_MULTICAST_GROUP = '239.255.255.250'
WSD_PORT = 3702

# WS-Discovery XML templates
PROBE_MATCH_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" 
               xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing" 
               xmlns:wsd="http://schemas.xmlsoap.org/ws/2005/04/discovery" 
               xmlns:wsdp="http://schemas.xmlsoap.org/ws/2006/02/devprof"
               xmlns:pnpx="http://schemas.microsoft.com/windows/pnpx/2005/10">
  <soap:Header>
    <wsa:To>http://schemas.xmlsoap.org/ws/2004/08/addressing/role/anonymous</wsa:To>
    <wsa:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/ProbeMatches</wsa:Action>
    <wsa:MessageID>urn:uuid:{message_id}</wsa:MessageID>
    <wsa:RelatesTo>{relates_to}</wsa:RelatesTo>
  </soap:Header>
  <soap:Body>
    <wsd:ProbeMatches>
      <wsd:ProbeMatch>
        <wsa:EndpointReference>
          <wsa:Address>urn:uuid:{device_uuid}</wsa:Address>
        </wsa:EndpointReference>
        <wsd:Types>wsdp:Device pnpx:PrintDevice</wsd:Types>
        <wsd:Scopes>ldap:///ou=printer,o=hp</wsd:Scopes>
        <wsd:XAddrs>http://{ip}:5357/WSDPrinter</wsd:XAddrs>
        <wsd:MetadataVersion>1</wsd:MetadataVersion>
      </wsd:ProbeMatch>
    </wsd:ProbeMatches>
  </soap:Body>
</soap:Envelope>"""

RESOLVE_MATCH_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" 
               xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing" 
               xmlns:wsd="http://schemas.xmlsoap.org/ws/2005/04/discovery" 
               xmlns:wsdp="http://schemas.xmlsoap.org/ws/2006/02/devprof"
               xmlns:pnpx="http://schemas.microsoft.com/windows/pnpx/2005/10">
  <soap:Header>
    <wsa:To>http://schemas.xmlsoap.org/ws/2004/08/addressing/role/anonymous</wsa:To>
    <wsa:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/ResolveMatches</wsa:Action>
    <wsa:MessageID>urn:uuid:{message_id}</wsa:MessageID>
    <wsa:RelatesTo>{relates_to}</wsa:RelatesTo>
  </soap:Header>
  <soap:Body>
    <wsd:ResolveMatches>
      <wsd:ResolveMatch>
        <wsa:EndpointReference>
          <wsa:Address>urn:uuid:{device_uuid}</wsa:Address>
        </wsa:EndpointReference>
        <wsd:Types>wsdp:Device pnpx:PrintDevice</wsd:Types>
        <wsd:Scopes>ldap:///ou=printer,o=hp</wsd:Scopes>
        <wsd:XAddrs>http://{ip}:5357/WSDPrinter</wsd:XAddrs>
        <wsd:MetadataVersion>1</wsd:MetadataVersion>
      </wsd:ResolveMatch>
    </wsd:ResolveMatches>
  </soap:Body>
</soap:Envelope>"""

HELLO_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" 
               xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing" 
               xmlns:wsd="http://schemas.xmlsoap.org/ws/2005/04/discovery" 
               xmlns:wsdp="http://schemas.xmlsoap.org/ws/2006/02/devprof"
               xmlns:pnpx="http://schemas.microsoft.com/windows/pnpx/2005/10">
  <soap:Header>
    <wsa:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</wsa:To>
    <wsa:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Hello</wsa:Action>
    <wsa:MessageID>urn:uuid:{message_id}</wsa:MessageID>
  </soap:Header>
  <soap:Body>
    <wsd:Hello>
      <wsa:EndpointReference>
        <wsa:Address>urn:uuid:{device_uuid}</wsa:Address>
      </wsa:EndpointReference>
      <wsd:Types>wsdp:Device pnpx:PrintDevice</wsd:Types>
      <wsd:Scopes>ldap:///ou=printer,o=hp</wsd:Scopes>
      <wsd:XAddrs>http://{ip}:5357/WSDPrinter</wsd:XAddrs>
      <wsd:MetadataVersion>1</wsd:MetadataVersion>
    </wsd:Hello>
  </soap:Body>
</soap:Envelope>"""


class WSDiscoveryServer:
    """WS-Discovery server for Windows printer discovery"""
    
    def __init__(self, interface_ip='0.0.0.0'):
        self.interface_ip = interface_ip
        self.sock = None
        self.running = False
        
    def start(self):
        """Start the WS-Discovery server"""
        try:
            # Create UDP socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Bind to the WSD port
            self.sock.bind(('', WSD_PORT))
            
            # Join multicast group
            mreq = struct.pack("4sl", socket.inet_aton(WSD_MULTICAST_GROUP), socket.INADDR_ANY)
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            
            logger.info(f"WS-Discovery server listening on port {WSD_PORT}")
            print(f"WS-Discovery server listening on UDP port {WSD_PORT} (Windows printer discovery)")
            
            # Send initial Hello message
            self.send_hello()
            
            self.running = True
            
            # Listen for discovery requests
            while self.running:
                try:
                    data, addr = self.sock.recvfrom(65535)
                    # Handle in separate thread
                    thread = threading.Thread(target=self.handle_request, args=(data, addr))
                    thread.daemon = True
                    thread.start()
                    
                except Exception as e:
                    if self.running:
                        logger.error(f"Error receiving WS-Discovery packet: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to start WS-Discovery server: {e}")
            raise
        finally:
            if self.sock:
                self.sock.close()
    
    def handle_request(self, data, addr):
        """Handle incoming WS-Discovery request"""
        try:
            data_str = data.decode('utf-8', errors='ignore')
            
            # Check for Probe request
            if 'Probe>' in data_str and ('PrintDevice' in data_str or 'Device' in data_str):
                logger.info(f"Received Probe request from {addr[0]}")
                print(f"[WS-Discovery] Probe request from {addr[0]} - responding")
                self.send_probe_match(data_str, addr)
                
            # Check for Resolve request
            elif 'Resolve>' in data_str:
                logger.info(f"Received Resolve request from {addr[0]}")
                print(f"[WS-Discovery] Resolve request from {addr[0]} - responding")
                self.send_resolve_match(data_str, addr)
                
        except Exception as e:
            logger.error(f"Error handling WS-Discovery request: {e}")
    
    def send_probe_match(self, request, addr):
        """Send ProbeMatch response"""
        try:
            # Extract MessageID from request
            relates_to = "urn:uuid:" + str(uuid.uuid4())
            if '<wsa:MessageID>' in request:
                start = request.find('<wsa:MessageID>') + len('<wsa:MessageID>')
                end = request.find('</wsa:MessageID>')
                if start > 0 and end > 0:
                    relates_to = request[start:end]
            
            # Generate response
            message_id = str(uuid.uuid4())
            response = PROBE_MATCH_TEMPLATE.format(
                message_id=message_id,
                relates_to=relates_to,
                device_uuid=UUID,
                ip=IP
            )
            
            # Send unicast response
            self.sock.sendto(response.encode('utf-8'), addr)
            logger.info(f"Sent ProbeMatch to {addr[0]}")
            
        except Exception as e:
            logger.error(f"Error sending ProbeMatch: {e}")
    
    def send_resolve_match(self, request, addr):
        """Send ResolveMatch response"""
        try:
            # Extract MessageID from request
            relates_to = "urn:uuid:" + str(uuid.uuid4())
            if '<wsa:MessageID>' in request:
                start = request.find('<wsa:MessageID>') + len('<wsa:MessageID>')
                end = request.find('</wsa:MessageID>')
                if start > 0 and end > 0:
                    relates_to = request[start:end]
            
            # Generate response
            message_id = str(uuid.uuid4())
            response = RESOLVE_MATCH_TEMPLATE.format(
                message_id=message_id,
                relates_to=relates_to,
                device_uuid=UUID,
                ip=IP
            )
            
            # Send unicast response
            self.sock.sendto(response.encode('utf-8'), addr)
            logger.info(f"Sent ResolveMatch to {addr[0]}")
            
        except Exception as e:
            logger.error(f"Error sending ResolveMatch: {e}")
    
    def send_hello(self):
        """Send Hello announcement to multicast group"""
        try:
            message_id = str(uuid.uuid4())
            hello = HELLO_TEMPLATE.format(
                message_id=message_id,
                device_uuid=UUID,
                ip=IP
            )
            
            # Send to multicast group
            self.sock.sendto(hello.encode('utf-8'), (WSD_MULTICAST_GROUP, WSD_PORT))
            logger.info("Sent WS-Discovery Hello announcement")
            print(f"[WS-Discovery] Sent Hello announcement for {MODEL}")
            
        except Exception as e:
            logger.error(f"Error sending Hello: {e}")
    
    def stop(self):
        """Stop the server"""
        self.running = False
        if self.sock:
            self.sock.close()


def run(port=3702):
    """Start the WS-Discovery server"""
    server = WSDiscoveryServer()
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
    
    # Generate or use configured UUID
    UUID = config.get('uuid', str(uuid.uuid4()))
    
    logger.info(f"Starting WS-Discovery server for {MODEL} (UUID: {UUID})")
    
    run(port)
