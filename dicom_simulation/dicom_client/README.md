# DICOM Client Simulator

Simple load generator that sends randomized study data to the companion DICOM server using `pynetdicom==2.0.2`.

## Requirements
Create and activate a virtual environment, then install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage
1. Update the variables at the bottom of `dicom_client.py` to point at the server instance:
   - `dicom_folder` – directory containing sample `.DCM` files
   - `pacs_ip`, `pacs_port` – host and port for the target server
   - `pacs_ae_title` – server AE title (defaults to `ORTHANC`)
2. Run the script:

```bash
python dicom_client.py
```

The client randomizes patient metadata and reuses the configured DICOM images to produce traffic.

## Notes
- The AE title, implementation class UID, and version string are set near the top of the script; adjust if your testing scenario requires unique identifiers.
- Enable `pynetdicom` debug output by leaving `debug_logger()` enabled, or comment the call out for quieter logs.
