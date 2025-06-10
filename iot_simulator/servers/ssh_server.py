import socket
import threading
import paramiko
import sys
import os
import argparse
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core_logger import get_logger
import paramiko.transport
paramiko.transport._CLIENT_ID = b'SSH-2.0-OpenSSH_7.4 Siemens MULTIX-CX (4.8.21)'



logger = get_logger("ssh_server")

HOST_KEY = paramiko.RSAKey.generate(2048)  # in production, use static key

# Simulated credentials
VALID_USER = "admin"
VALID_PASS = "multix2025"

WELCOME_MSG = """
MULTIX-CX Siemens Healthineers Console
Firmware v4.8.21 (Build 2025-05-05)
Type 'help' to list available commands.
"""

COMMANDS = {
    "status": "System Status: OPERATIONAL\nTube Temp: 36.8°C\nLast Exposure: 2025-05-04 12:14",
    "dicom show": "AET: MULTIXCX\nRemote AET: PACS_SERVER\nRemote IP: 10.1.10.55\nPort: 104",
    "help": "Available commands: status, dicom show, exit",
    "exit": "Goodbye."
}

class Server(paramiko.ServerInterface):
    def __init__(self):
        self.event = threading.Event()

    def check_auth_password(self, username, password):
        if username == VALID_USER and password == VALID_PASS:
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return "password"

    def check_channel_request(self, kind, chanid):
        return paramiko.OPEN_SUCCEEDED if kind == 'session' else paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

def handle_connection(client_socket, client_addr):
    transport = paramiko.Transport(client_socket)
    transport.add_server_key(HOST_KEY)
    server = Server()

    try:
        transport.start_server(server=server)
    except paramiko.SSHException as e:
        logger.error(f"SSH negotiation failed from {client_addr}: {e}")
        return

    chan = transport.accept(20)
    if chan is None:
        logger.error(f"SSH channel was never opened for {client_addr}")
        return

    logger.info(f"SSH session started with {client_addr}")
    try:
        chan.send(WELCOME_MSG + "\n> ")

        while True:
            command = ""
            while not command.endswith("\n"):
                try:
                    chunk = chan.recv(1024)
                    if not chunk:
                        logger.info(f"SSH client disconnected: {client_addr}")
                        raise ConnectionResetError("Client closed connection")
                    command += chunk.decode("utf-8", errors="ignore")
                except Exception as recv_err:
                    logger.warning(f"Recv error from {client_addr}: {recv_err}")
                    raise

            command = command.strip()
            logger.info(f"SSH command from {client_addr}: '{command}'")

            if command in COMMANDS:
                chan.sendall(COMMANDS[command] + "\n")
                if command == "exit":
                    break
            else:
                chan.sendall("Unknown command.\n")
            chan.sendall("> ")

    except Exception as e:
        logger.warning(f"SSH session error from {client_addr}: {e}")
    finally:
        try:
            chan.close()
        except Exception:
            pass
        transport.close()
        logger.info(f"SSH session closed for {client_addr}")

def run(port=2222):
    logger.info("Starting Siemens MULTIX SSH interface...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", port))
    sock.listen(100)
    logger.info("SSH server listening on port 22")
    print("[INFO] SSH server started on port 22 (simulated Siemens console)")

    while True:
        client, addr = sock.accept()
        logger.info(f"Incoming SSH connection from {addr}")
        threading.Thread(target=handle_connection, args=(client,), daemon=True).start()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=2222)
    args = parser.parse_args()
    run(args.port)
