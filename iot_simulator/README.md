# IoT Simulator Daemon

Utility service that orchestrates multiple simulated IoT device servers defined in `config.json`. Each child process runs independently while the daemon manages lifecycle, logging, and PID tracking.

## Requirements
The simulator only relies on the Python standard library. No additional packages are required, but you can install the (empty) requirements file to stay consistent with other projects:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration
- `config.json` describes which server scripts to launch and any shared globals passed via `--globals` JSON payload.
- Individual simulated devices live under the `servers/` directory (each script must accept optional `--port` and `--globals` arguments).

## Usage
Run the controller from this directory:

```bash
python server.py start
```

Available commands:
- `python server.py start` – daemonizes and launches configured server scripts
- `python server.py stop` – stops child processes and removes PID files
- `python server.py restart` – convenience wrapper for stop/start

Runtime artifacts:
- `my_daemon.pid` – PID for the master process
- `my_daemon_subprocesses.pid` – list of spawned child PIDs
- `logs/` – STDOUT/STDERR captures for each child (auto-created)
- `daemon.log` – rotating log produced by `core_logger`

## Development Tips
- When modifying device scripts under `servers/`, confirm they accept the expected CLI arguments; otherwise the controller will fail to spawn them.
- Tail the files in `logs/` to observe per-device activity or runtime errors.
