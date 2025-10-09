# DICOM Server Simulator

Simulated Orthanc-style DICOM storage provider that exposes a REST/HTML dashboard for monitoring activity when paired with the test clients in this repository.

## Features
- Listens for DICOM associations using `pynetdicom==2.0.2`
- Tracks client metadata, session history, and storage statistics
- Serves a rich dashboard with live connection charts and recent patient activity
- Provides JSON APIs for integration or automation

## Requirements
Install the Python dependencies into a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration
Edit `dicom_server_config.json` (copy from `dicom_server_config.example.json`) to override ports, logging, and AE title. The default dashboard binds to `http://127.0.0.1:8081`.

## Running
```bash
python dicom_server.py --config dicom_server_config.json
```

Key options:
- `--dicom-port` – override the DICOM listener port (default 4790)
- `--api-port` – set the REST/dashboard port (default 8081)
- `--heartbeat-interval` – adjust heartbeat logging frequency

## REST Endpoints
- `GET /api/status` – server and client telemetry
- `GET /api/patients?limit=N` – recent patient records
- `GET /api/logs?lines=N` – log tail in text or JSON
- `GET /healthz` – readiness probe

## Development Notes
- Unit tests are not bundled; run integration tests by exercising the client sender and verifying the dashboard updates in real time.
- Python 3.10+ recommended for best compatibility.
