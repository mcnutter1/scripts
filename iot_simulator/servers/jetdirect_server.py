#!/usr/bin/env python3
"""
HP JetDirect Server Simulator
Implements HP JetDirect protocol on port 9100 for raw printing
Fully accepts and logs print jobs to files
"""
import sys
import os
import socket
import threading
from datetime import datetime
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core_logger import get_logger
from shared import parse_args

logger = get_logger("jetdirect_server")

# Print jobs directory
PRINT_JOBS_DIR = os.path.join(os.path.dirname(__file__), '..', 'print_jobs')
PRINT_LOG_FILE = os.path.join(PRINT_JOBS_DIR, 'print_log.json')

# Global config variables
SYSTEM_NAME = ""
IP = ""
MAC = ""
HOSTNAME = ""
SERIAL = ""
MODEL = ""
PAGE_COUNT = 0

# PJL (Printer Job Language) responses
PJL_INFO_ID = """@PJL INFO ID
{model}
END
"""

PJL_INFO_STATUS = """@PJL INFO STATUS
CODE=10001
DISPLAY="Ready"
ONLINE=TRUE
END
"""

PJL_INFO_CONFIG = """@PJL INFO CONFIG
IN TRAYS [1 ENUMERATED]
        TRAY1 [2 MEDIASIZE]
                LETTER
                LEGAL
                A4
        INTRAY1 LETTER

OUT TRAYS [3 ENUMERATED]
        UPPER
        MAIN
        LOWER
        
MEMORY={memory}
PAGE COUNT={pagecount}
END
"""

PJL_INFO_PAGECOUNT = """@PJL INFO PAGECOUNT
{pagecount}
END
"""

PJL_USTATUS_DEVICE = """@PJL USTATUS DEVICE
CODE=10001
DISPLAY="Ready"
ONLINE=TRUE
END
"""

PJL_USTATUS_JOB = """@PJL USTATUS JOB
START={job_id}
END
"""

class JetDirectHandler:
    """Handles individual JetDirect client connections"""
    
    def __init__(self, client_socket, client_address):
        self.socket = client_socket
        self.address = client_address
        self.job_id = 0
        
    def handle(self):
        """Handle client connection"""
        try:
            logger.info(f"New JetDirect connection from {self.address[0]}:{self.address[1]}")
            print(f"[JetDirect] Connection from {self.address[0]}:{self.address[1]}")
            
            buffer = b""
            job_data = b""
            in_job = False
            
            while True:
                try:
                    data = self.socket.recv(4096)
                    if not data:
                        break
                    
                    buffer += data
                    
                    # Check for PJL commands
                    if b'@PJL' in buffer or b'\x1b%-12345X@PJL' in buffer:
                        # Extract and process PJL commands
                        response = self.process_pjl_commands(buffer)
                        if response:
                            self.socket.sendall(response.encode('utf-8'))
                            logger.info(f"Sent PJL response to {self.address[0]}")
                        
                        # Check for job start
                        if b'@PJL ENTER LANGUAGE' in buffer or b'@PJL JOB' in buffer:
                            in_job = True
                            self.job_id += 1
                            logger.info(f"Print job {self.job_id} started from {self.address[0]}")
                    
                    # Collect job data
                    if in_job:
                        job_data += data
                        
                        # Check for job end
                        if b'\x1b%-12345X' in data and len(job_data) > 100:
                            # Job complete
                            logger.info(f"Print job {self.job_id} completed: {len(job_data)} bytes received")
                            print(f"[JetDirect] Print job {self.job_id}: {len(job_data)} bytes")
                            
                            # Simulate printing
                            self.simulate_print_job(job_data)
                            
                            # Reset for next job
                            in_job = False
                            job_data = b""
                            buffer = b""
                    
                    # Clear buffer if too large
                    if len(buffer) > 100000:
                        buffer = buffer[-10000:]
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"Error receiving data: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Error handling JetDirect connection: {e}")
        finally:
            logger.info(f"Closing connection from {self.address[0]}:{self.address[1]}")
            self.socket.close()
    
    def process_pjl_commands(self, data):
        """Process PJL commands and return appropriate response"""
        try:
            # Convert to string for easier processing
            data_str = data.decode('utf-8', errors='ignore')
            
            # Extract PJL commands
            if '@PJL INFO ID' in data_str:
                logger.info("PJL INFO ID request")
                return PJL_INFO_ID.format(model=MODEL)
                
            elif '@PJL INFO STATUS' in data_str:
                logger.info("PJL INFO STATUS request")
                return PJL_INFO_STATUS
                
            elif '@PJL INFO CONFIG' in data_str:
                logger.info("PJL INFO CONFIG request")
                return PJL_INFO_CONFIG.format(memory="64MB", pagecount=PAGE_COUNT)
                
            elif '@PJL INFO PAGECOUNT' in data_str:
                logger.info("PJL INFO PAGECOUNT request")
                return PJL_INFO_PAGECOUNT.format(pagecount=PAGE_COUNT)
                
            elif '@PJL USTATUS DEVICE' in data_str:
                logger.info("PJL USTATUS DEVICE request")
                return PJL_USTATUS_DEVICE
                
            elif '@PJL USTATUS JOB' in data_str:
                logger.info("PJL USTATUS JOB request")
                return PJL_USTATUS_JOB.format(job_id=self.job_id)
                
            elif '@PJL ECHO' in data_str:
                # Echo back
                echo_text = data_str.split('@PJL ECHO')[1].split('\n')[0].strip()
                logger.info(f"PJL ECHO: {echo_text}")
                return f"@PJL ECHO {echo_text}\n"
            
            return None
            
        except Exception as e:
            logger.error(f"Error processing PJL commands: {e}")
            return None
    
    def simulate_print_job(self, job_data):
        """Simulate processing a print job and save to file"""
        global PAGE_COUNT
        
        # Try to detect document type
        doc_type = "Unknown"
        pages_estimated = 1
        
        if b'%PDF' in job_data:
            doc_type = "PDF"
            # Count pages in PDF (simplified)
            pages_estimated = job_data.count(b'/Page')
        elif b'%!PS-Adobe' in job_data:
            doc_type = "PostScript"
            pages_estimated = job_data.count(b'%%Page:')
        elif b'PCL' in job_data or b'\x1b' in job_data[:100]:
            doc_type = "PCL"
            # Estimate pages from form feeds
            pages_estimated = max(1, job_data.count(b'\x0c'))
        
        logger.info(f"Job type: {doc_type}, Estimated pages: {pages_estimated}, Size: {len(job_data)} bytes")
        print(f"[JetDirect] Printing {doc_type} document ({pages_estimated} pages, {len(job_data)} bytes)")
        
        # Update page count
        PAGE_COUNT += pages_estimated
        
        # Save print job to file
        try:
            # Create print jobs directory if it doesn't exist
            os.makedirs(PRINT_JOBS_DIR, exist_ok=True)
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            ext = {'PDF': 'pdf', 'PostScript': 'ps', 'PCL': 'pcl'}.get(doc_type, 'prn')
            filename = f"job_{self.job_id}_{timestamp}.{ext}"
            filepath = os.path.join(PRINT_JOBS_DIR, filename)
            
            # Save job data
            with open(filepath, 'wb') as f:
                f.write(job_data)
            
            logger.info(f"Print job saved to {filepath}")
            print(f"[JetDirect] Job saved: {filename}")
            
            # Log to print log
            log_entry = {
                'job_id': self.job_id,
                'timestamp': datetime.now().isoformat(),
                'source_ip': self.address[0],
                'source_port': self.address[1],
                'document_type': doc_type,
                'pages': pages_estimated,
                'size_bytes': len(job_data),
                'filename': filename,
                'status': 'completed'
            }
            
            # Append to log file
            log_entries = []
            if os.path.exists(PRINT_LOG_FILE):
                try:
                    with open(PRINT_LOG_FILE, 'r') as f:
                        log_entries = json.load(f)
                except:
                    log_entries = []
            
            log_entries.append(log_entry)
            
            with open(PRINT_LOG_FILE, 'w') as f:
                json.dump(log_entries, f, indent=2)
            
            print(f"[JetDirect] Print log updated: {len(log_entries)} total jobs")
            
        except Exception as e:
            logger.error(f"Error saving print job: {e}")
            print(f"[JetDirect] Error saving job: {e}")


class JetDirectServer:
    """Main JetDirect server"""
    
    def __init__(self, port=9100):
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
    def start(self):
        """Start the JetDirect server"""
        try:
            self.sock.bind(('', self.port))
            self.sock.listen(5)
            logger.info(f"JetDirect server listening on port {self.port}")
            print(f"HP JetDirect server listening on port {self.port}")
            
            while True:
                try:
                    client_sock, client_addr = self.sock.accept()
                    # Handle each connection in a new thread
                    handler = JetDirectHandler(client_sock, client_addr)
                    thread = threading.Thread(target=handler.handle)
                    thread.daemon = True
                    thread.start()
                    
                except Exception as e:
                    logger.error(f"Error accepting connection: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to start JetDirect server: {e}")
            raise
        finally:
            self.sock.close()


def run(port=9100):
    """Start the JetDirect server"""
    server = JetDirectServer(port)
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
    PAGE_COUNT = config.get('page_count', 0)
    
    logger.info(f"Starting JetDirect server for {MODEL} (S/N: {SERIAL})")
    
    run(port)
