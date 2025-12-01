import os
import sys
import signal
import time
import json
import subprocess
import importlib.util
import argparse
from core_logger import get_logger

#sudo setcap 'cap_net_bind_service=+ep' /usr/bin/python3.11#

logger = get_logger("daemon")

# Get the directory where the script is run from
BASE_DIR = os.path.abspath(os.getcwd())
LOGS_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

PID_FILE = os.path.join(BASE_DIR, "my_daemon.pid")
PROCESS_PID_FILE = os.path.join(BASE_DIR, "my_daemon_subprocesses.pid")
CONFIG_FILE = "config.json"  # Default config file
processes = []

def load_config(config_file=None):
    """Load configuration from specified file or default"""
    config_path = config_file if config_file else CONFIG_FILE
    if not os.path.exists(config_path):
        logger.error(f"Configuration file not found: {config_path}")
        print(f"[ERROR] Configuration file not found: {config_path}")
        sys.exit(1)
    
    try:
        with open(config_path) as f:
            config = json.load(f)
            logger.info(f"Loaded configuration from: {config_path}")
            print(f"[INFO] Using configuration: {config_path}")
            return config
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in config file: {e}")
        print(f"[ERROR] Invalid JSON in config file: {e}")
        sys.exit(1)

def load_and_run_servers(includes, json_config):
    for entry in includes:
        path = entry["path"]
        port = str(entry.get("port", ""))  # Optional
        globals_arg = json.dumps(json_config)
        try:
            logger.info(f"Starting subprocess: {path} with port {port}")
            print(f"[INFO] Starting subprocess: {path} on port {port}")

            cmd = [sys.executable, path]
            if port:
                cmd += ["--port", port]
            cmd += ["--globals", globals_arg]
            out_path = os.path.join(LOGS_DIR, f'{os.path.basename(path)}.out')
            err_path = os.path.join(LOGS_DIR, f'{os.path.basename(path)}.err')
            p = subprocess.Popen(
                cmd,
                stdout=open(out_path, 'a'),
                stderr=open(err_path, 'a'),
                stdin=open(os.devnull, 'r')
            )

            logger.info(f"{path} started as PID {p.pid}")
            processes.append(p)

        except Exception as e:
            logger.exception(f"Failed to start {path}: {e}")
            print(f"[ERROR] Failed to start {path}: {e}")

def start(config_file=None):
    config = load_config(config_file)
    servers = config.get("servers", [])
    json_config = config.get("globals", {})

    if os.path.exists(PID_FILE):
        print("Daemon already running.")
        sys.exit(1)

    pid = os.fork()
    if pid > 0:
        with open(PID_FILE, 'w') as f:
            f.write(str(pid))
        print(f"Daemon started with PID {pid}")
        sys.exit(0)

    os.setsid()
    os.umask(0)
    sys.stdout.flush()
    sys.stderr.flush()

    config = load_config(config_file)
    servers = config.get("servers", [])
    load_and_run_servers(servers, json_config)
    write_process_pids()
    # Wait for children
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        stop_processes()
        sys.exit(0)

def write_process_pids():
    with open(PROCESS_PID_FILE, "w") as f:
        for p in processes:
            f.write(str(p.pid) + "\n")

def stop_processes():
    for p in processes:
        p.terminate()
    for p in processes:
        p.wait()

def stop():
    if not os.path.exists(PID_FILE):
        print("Daemon not running.")
        return

    # Kill subprocesses first
    if os.path.exists(PROCESS_PID_FILE):
        with open(PROCESS_PID_FILE, 'r') as f:
            pids = [int(line.strip()) for line in f if line.strip()]
        for pid in pids:
            try:
                print(f"Stopping subprocess PID {pid}")
                os.kill(pid, signal.SIGTERM)
            except ProcessLookupError:
                print(f"Subprocess PID {pid} already exited.")
        os.remove(PROCESS_PID_FILE)

    # Then kill the main daemon
    with open(PID_FILE, 'r') as f:
        pid = int(f.read())
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass

    os.remove(PID_FILE)
    print("Daemon stopped.")

def restart(config_file=None):
    stop()
    time.sleep(1)
    start(config_file)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='IoT Device Simulator Daemon',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start with default config.json
  python server.py start
  
  # Start with custom config file
  python server.py start --config config_hp_printer.json
  
  # Stop the daemon
  python server.py stop
  
  # Restart with different config
  python server.py restart --config config_hp_printer.json
        """
    )
    
    parser.add_argument(
        'action',
        choices=['start', 'stop', 'restart', 'status'],
        help='Action to perform: start, stop, restart, or status'
    )
    
    parser.add_argument(
        '--config',
        '-c',
        type=str,
        default=None,
        help='Path to configuration file (default: config.json)'
    )
    
    return parser.parse_args()

def status():
    """Check daemon status"""
    if os.path.exists(PID_FILE):
        with open(PID_FILE, 'r') as f:
            pid = int(f.read())
        
        # Check if process is actually running
        try:
            os.kill(pid, 0)
            print(f"Daemon is running with PID {pid}")
            
            # Check subprocesses
            if os.path.exists(PROCESS_PID_FILE):
                with open(PROCESS_PID_FILE, 'r') as f:
                    pids = [int(line.strip()) for line in f if line.strip()]
                print(f"Running {len(pids)} subprocess(es):")
                for pid in pids:
                    try:
                        os.kill(pid, 0)
                        print(f"  - PID {pid}: Running")
                    except ProcessLookupError:
                        print(f"  - PID {pid}: Not running")
        except ProcessLookupError:
            print(f"Daemon PID {pid} not running (stale PID file)")
            print("Run 'stop' to clean up, then 'start' again")
    else:
        print("Daemon is not running.")

if __name__ == "__main__":
    args = parse_arguments()
    
    action = args.action
    config_file = args.config
    
    if action == "start":
        start(config_file)
    elif action == "stop":
        stop()
    elif action == "restart":
        restart(config_file)
    elif action == "status":
        status()
