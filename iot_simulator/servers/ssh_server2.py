import socket
import threading
import paramiko
import sys
import os
import argparse
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core_logger import get_logger

# Fake server fingerprint (OpenSSH lookalike)
paramiko.transport._CLIENT_ID = b'SSH-2.0-OpenSSH_7.4 Siemens MULTIX-CX (4.8.21)'

logger = get_logger("ssh_server")

HOST_KEY = paramiko.RSAKey.generate(2048)
VALID_USER = "admin"
VALID_PASS = "multix2025"

WELCOME = (
    "\nMULTIX-CX Siemens Healthineers Console\n"
    "Firmware v4.8.21 (Build 2025-05-05)\n"
    "Type 'help' to list available commands.\n"
)

COMMANDS = {
    "help": "Available commands: status, dicom show, exit",
    "status": "System Status: OPERATIONAL\nTube Temp: 36.8°C\nLast Exposure: 2025-05-04 12:14",
    "dicom show": "AET: MULTIXCX\nRemote AET: PACS_SERVER\nRemote IP: 10.1.10.55\nPort: 104",
    "exit": "Goodbye."
}

class Server(paramiko.ServerInterface):
    def check_auth_password(self, username, password):
        if username == VALID_USER and password == VALID_PASS:
            logger.info(f"SSH login successful: {username}:{password}")
            return paramiko.AUTH_SUCCESSFUL
        logger.warning(f"SSH login failed: {username}:{password}")
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return "password"

    def check_channel_request(self, kind, chanid):
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_shell_request(self, channel):
        return True

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True

def handle_client(client, addr):
    logger.info(f"New SSH connection from {addr}")
    transport = paramiko.Transport(client)
    transport.add_server_key(HOST_KEY)
    server = Server()
    try:
        transport.start_server(server=server)
    except paramiko.SSHException as e:
        logger.error(f"SSH negotiation failed: {e}")
        return

    chan = transport.accept(10)
    if chan is None:
        logger.error("SSH channel never opened.")
        return

    try:
        chan.send(WELCOME + "\n> ")
        while True:
            data = chan.recv(1024).decode().strip()
            if not data:
                break
            logger.info(f"Command from {addr}: {data}")
            if data in COMMANDS:
                chan.send(COMMANDS[data] + "\n")
                if data == "exit":
                    break
            else:
                chan.send("Unknown command.\n")
            chan.send("> ")
    except Exception as e:
        logger.error(f"SSH session error: {e}")
    finally:
        chan.close()
        transport.close()
        logger.info(f"SSH session from {addr} closed")

def run(port):
    logger.info(f"SSH server starting on port {port}")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", port))
    sock.listen(100)
    logger.info(f"Listening for SSH on port {port}")
    print(f"[INFO] SSH server is running on port {port}")

    while True:
        client, addr = sock.accept()
        threading.Thread(
            target=handle_client,
            args=(client, addr),  # ✅ pass both client socket and client address
            daemon=True
        ).start()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=2222)
    parser.add_argument("--globals", type=str)
    args = parser.parse_args()
    run(args.port)
