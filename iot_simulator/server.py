import os
import sys
import signal
import time
import json
import subprocess
import importlib.util
from core_logger import get_logger

#sudo setcap 'cap_net_bind_service=+ep' /usr/bin/python3.11#

logger = get_logger("daemon")

# Get the directory where the script is run from
BASE_DIR = os.path.abspath(os.getcwd())
LOGS_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

PID_FILE = os.path.join(BASE_DIR, "my_daemon.pid")
PROCESS_PID_FILE = os.path.join(BASE_DIR, "my_daemon_subprocesses.pid")
CONFIG_FILE = "config.json"
processes = []

def load_config():
    with open(CONFIG_FILE) as f:
        return json.load(f)

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

def start():
    config = load_config()
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

    config = load_config()
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

def restart():
    stop()
    time.sleep(1)
    start()

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("start", "stop", "restart"):
        print("Usage: python server.py [start|stop|restart]")
        sys.exit(1)

    action = sys.argv[1]
    if action == "start":
        start()
    elif action == "stop":
        stop()
    elif action == "restart":
        restart()
