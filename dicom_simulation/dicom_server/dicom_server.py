#!/usr/bin/env python3
"""DICOM server daemon with CLI control, logging, and status web UI/API."""

from __future__ import annotations

import argparse
import atexit
import contextlib
import json
import logging
import logging.handlers
import os
import signal
import sys
import threading
import time
from collections import deque
from datetime import datetime
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from socketserver import ThreadingMixIn
from typing import Dict, List, Optional
from urllib.parse import parse_qs, urlparse

from pynetdicom import AE, evt, AllStoragePresentationContexts, debug_logger
from pynetdicom.sop_class import XRayAngiographicImageStorage
from pydicom.uid import (
    ExplicitVRLittleEndian,
    ExplicitVRBigEndian,
    ImplicitVRLittleEndian,
    JPEGBaseline,
)

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 4790
DEFAULT_API_HOST = "127.0.0.1"
DEFAULT_API_PORT = 8081
DEFAULT_HEARTBEAT = 5
DEFAULT_CONFIG_FILENAME = "dicom_server_config.json"
DEFAULT_AE_TITLE = "ORTHANC"
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 3
LOG_TAIL_DEFAULT = 200
LOG_TAIL_MAX = 2000


def detect_default_base_dir() -> Path:
    preferred = Path("/opt/dicom_server")
    if preferred.exists():
        return preferred
    return Path(__file__).resolve().parent


@dataclass
class ServerConfig:
    """Runtime configuration for the DICOM server daemon."""

    config_path: Path
    base_dir: Path
    dicom_host: str = DEFAULT_HOST
    dicom_port: int = DEFAULT_PORT
    api_host: str = DEFAULT_API_HOST
    api_port: int = DEFAULT_API_PORT
    heartbeat_interval: int = DEFAULT_HEARTBEAT
    log_file: Path | str = ""
    pid_file: Path | str = ""
    log_max_bytes: int = LOG_MAX_BYTES
    log_backup_count: int = LOG_BACKUP_COUNT
    log_tail_lines: int = LOG_TAIL_DEFAULT
    ae_title: str = DEFAULT_AE_TITLE

    def __post_init__(self) -> None:
        self.config_path = self.config_path.expanduser().resolve()
        self.base_dir = self._resolve_directory(self.base_dir)
        self.heartbeat_interval = max(1, int(self.heartbeat_interval))
        self.log_tail_lines = max(1, int(self.log_tail_lines))
        self.log_max_bytes = max(1024, int(self.log_max_bytes))
        self.log_backup_count = max(1, int(self.log_backup_count))
        self.ae_title = str(self.ae_title or DEFAULT_AE_TITLE)

        if not self.log_file:
            self.log_file = self.base_dir / "logs" / "dicom_server.log"
        self.set_log_file(self.log_file)

        if not self.pid_file:
            self.pid_file = self.base_dir / "run" / "dicom_server.pid"
        self.set_pid_file(self.pid_file)

    def _resolve_directory(self, path: Path | str) -> Path:
        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            candidate = self.config_path.parent / candidate
        return candidate.resolve()

    def set_log_file(self, value: Path | str) -> None:
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = self.base_dir / path
        self.log_file = path.resolve()

    def set_pid_file(self, value: Path | str) -> None:
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = self.base_dir / path
        self.pid_file = path.resolve()

    def ensure_directories(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)

    def apply_cli_overrides(self, args: argparse.Namespace) -> None:
        if getattr(args, "dicom_host", None):
            self.dicom_host = args.dicom_host
        if getattr(args, "dicom_port", None):
            self.dicom_port = int(args.dicom_port)
        if getattr(args, "api_host", None):
            self.api_host = args.api_host
        if getattr(args, "api_port", None):
            self.api_port = int(args.api_port)
        if getattr(args, "heartbeat_interval", None):
            self.heartbeat_interval = max(1, int(args.heartbeat_interval))
        if getattr(args, "log_file", None):
            self.set_log_file(args.log_file)
        if getattr(args, "pid_file", None):
            self.set_pid_file(args.pid_file)
        if getattr(args, "log_max_bytes", None):
            self.log_max_bytes = max(1024, int(args.log_max_bytes))
        if getattr(args, "log_backup_count", None):
            self.log_backup_count = max(1, int(args.log_backup_count))
        if getattr(args, "log_tail_lines", None):
            self.log_tail_lines = max(1, int(args.log_tail_lines))
        if getattr(args, "ae_title", None):
            self.ae_title = str(args.ae_title)

    def as_dict(self) -> Dict[str, object]:
        return {
            "config_path": str(self.config_path),
            "base_dir": str(self.base_dir),
            "dicom_host": self.dicom_host,
            "dicom_port": self.dicom_port,
            "api_host": self.api_host,
            "api_port": self.api_port,
            "heartbeat_interval": self.heartbeat_interval,
            "log_file": str(self.log_file),
            "pid_file": str(self.pid_file),
            "log_max_bytes": self.log_max_bytes,
            "log_backup_count": self.log_backup_count,
            "log_tail_lines": self.log_tail_lines,
            "ae_title": self.ae_title,
        }


@dataclass
class ClientStats:
    """Aggregated statistics for an initiating DICOM client."""

    key: str
    ip: str
    ae_title: str
    implementation_version: Optional[str] = None
    implementation_class_uid: Optional[str] = None
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None
    total_sessions: int = 0
    active_sessions: int = 0
    last_remote_port: Optional[int] = None
    recent_sessions: deque = field(default_factory=lambda: deque(maxlen=50))
    ae_titles: set[str] = field(default_factory=set)
    implementation_versions: set[str] = field(default_factory=set)
    implementation_class_uids: set[str] = field(default_factory=set)

    def to_payload(self) -> Dict[str, object]:
        sessions: List[Dict[str, object]] = []
        for entry in list(self.recent_sessions):
            sessions.append(
                {
                    "started_at": entry.get("started_at"),
                    "ended_at": entry.get("ended_at"),
                    "duration_seconds": entry.get("duration_seconds"),
                    "remote_port": entry.get("remote_port"),
                }
            )

        known_titles = sorted(self.ae_titles)
        known_versions = sorted(self.implementation_versions)
        known_class_uids = sorted(self.implementation_class_uids)

        return {
            "ip": self.ip,
            "ae_title": self.ae_title,
            "implementation_version": self.implementation_version,
            "implementation_class_uid": self.implementation_class_uid,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "total_sessions": self.total_sessions,
            "active_sessions": self.active_sessions,
            "last_remote_port": self.last_remote_port,
            "recent_sessions": sessions,
            "known_ae_titles": known_titles,
            "known_implementation_versions": known_versions,
            "known_implementation_class_uids": known_class_uids,
        }

    def note_identity(
        self,
        ae_title: Optional[str] = None,
        implementation_version: Optional[str] = None,
        implementation_class_uid: Optional[str] = None,
    ) -> None:
        if ae_title:
            normalized = ae_title.strip()
            if normalized and normalized.upper() != "UNKNOWN":
                self.ae_title = normalized
                self.ae_titles.add(normalized)
        if implementation_version:
            normalized_version = implementation_version.strip()
            if normalized_version:
                self.implementation_version = normalized_version
                self.implementation_versions.add(normalized_version)
        if implementation_class_uid:
            normalized_uid = implementation_class_uid.strip()
            if normalized_uid:
                self.implementation_class_uid = normalized_uid
                self.implementation_class_uids.add(normalized_uid)


def load_config(path_str: Optional[str]) -> ServerConfig:
    default_base = detect_default_base_dir()
    config_path = (
        Path(path_str).expanduser()
        if path_str
        else default_base / DEFAULT_CONFIG_FILENAME
    )

    data: Dict[str, object] = {}
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(
                f"Failed to parse configuration file {config_path}: {exc}",
                file=sys.stderr,
            )
            data = {}
    base_dir_value = data.get("base_dir") if data else None
    if base_dir_value:
        base_dir = Path(str(base_dir_value))
    elif config_path.exists():
        base_dir = config_path.parent
    else:
        base_dir = default_base

    def read_int(key: str, default: int) -> int:
        value = data.get(key) if data else None
        if value is None:
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    config = ServerConfig(
        config_path=config_path,
        base_dir=base_dir,
        dicom_host=str(data.get("dicom_host", DEFAULT_HOST)) if data else DEFAULT_HOST,
        dicom_port=read_int("dicom_port", DEFAULT_PORT),
        api_host=str(data.get("api_host", DEFAULT_API_HOST)) if data else DEFAULT_API_HOST,
        api_port=read_int("api_port", DEFAULT_API_PORT),
        heartbeat_interval=read_int("heartbeat_interval", DEFAULT_HEARTBEAT),
        log_file=str(data.get("log_file", "")) if data else "",
        pid_file=str(data.get("pid_file", "")) if data else "",
        log_max_bytes=read_int("log_max_bytes", LOG_MAX_BYTES),
        log_backup_count=read_int("log_backup_count", LOG_BACKUP_COUNT),
        log_tail_lines=read_int("log_tail_lines", LOG_TAIL_DEFAULT),
        ae_title=str(data.get("ae_title", DEFAULT_AE_TITLE)) if data else DEFAULT_AE_TITLE,
    )
    return config


def configure_logging(config: ServerConfig, console: bool = False) -> logging.Logger:
    config.ensure_directories()
    logger = logging.getLogger("dicom_server")
    logger.setLevel(logging.INFO)

    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        with contextlib.suppress(Exception):
            handler.close()

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(process)d %(threadName)s %(message)s"
    )
    file_handler = logging.handlers.RotatingFileHandler(
        config.log_file,
        maxBytes=config.log_max_bytes,
        backupCount=config.log_backup_count,
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    logger.propagate = False
    return logger


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class DICOMServer:
    def __init__(self, config: ServerConfig) -> None:
        self.config = config
        self.logger = configure_logging(config)
        self._stop_event = threading.Event()
        self.httpd: Optional[ThreadedHTTPServer] = None
        self._api_thread: Optional[threading.Thread] = None
        self.start_time: Optional[float] = None
        self._dicom_ae: Optional[AE] = None
        self._dicom_server: Optional[threading.Thread] = None
        self._connections_lock = threading.Lock()
        self._active_connections = 0
        self._total_connections = 0
        self._dicom_debug_configured = False
        self._patient_lock = threading.Lock()
        self._patient_records: deque[Dict[str, object]] = deque(maxlen=200)
        self._total_c_store = 0
        self._unique_patients: set[str] = set()
        self._client_stats: Dict[str, ClientStats] = {}
        self._session_index: Dict[str, str] = {}
        self._session_entries: Dict[str, Dict[str, object]] = {}
        self._assoc_session_map: Dict[int, str] = {}
        self._peer_session_map: Dict[str, List[str]] = {}
        self._connection_history: deque[Dict[str, object]] = deque(maxlen=720)
        self._max_concurrent_connections = 0
        self._last_snapshot_time = 0.0

    def _create_request_handler(self):
        server_ref = self

        class RequestHandler(BaseHTTPRequestHandler):
            server_version = "DICOMSimulator/1.0"
            sys_version = ""

            def do_GET(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                path = parsed.path or "/"
                params = parse_qs(parsed.query or "")

                if path in {"/", "/index.html", "/admin"}:
                    html = server_ref._render_dashboard()
                    self._write_html(html)
                    return

                if path in {"/status", "/api/status"}:
                    payload = server_ref.status_payload()
                    self._write_json(payload)
                    return

                if path in {"/api/patients", "/patients"}:
                    limit = None
                    if "limit" in params:
                        try:
                            limit = int(params["limit"][0])
                        except (TypeError, ValueError, IndexError):
                            limit = None
                    payload = server_ref.patients_payload(limit)
                    self._write_json(payload)
                    return

                if path in {"/logs", "/api/logs"}:
                    lines = server_ref.config.log_tail_lines
                    if "lines" in params:
                        try:
                            requested = int(params["lines"][0])
                            if requested > 0:
                                lines = min(requested, LOG_TAIL_MAX)
                        except (TypeError, ValueError, IndexError):
                            pass
                    log_lines = server_ref.tail_logs(lines)
                    fmt = (params.get("format") or ["json"])[0].lower()
                    if fmt in {"text", "plain"}:
                        self._write_text("\n".join(log_lines))
                    else:
                        payload = {
                            "log_file": str(server_ref.config.log_file),
                            "line_count": len(log_lines),
                            "lines": log_lines,
                        }
                        self._write_json(payload)
                    return

                if path == "/healthz":
                    self._write_text("ok")
                    return

                self.send_error(HTTPStatus.NOT_FOUND, "Unknown endpoint")

            def log_message(self, format: str, *args) -> None:  # noqa: A003
                server_ref.logger.debug(
                    "HTTP %s - %s", self.address_string(), format % args
                )

            def _write_json(
                self, payload: Dict[str, object], status: HTTPStatus = HTTPStatus.OK
            ) -> None:
                encoded = json.dumps(payload, indent=2).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def _write_text(self, content: str, status: HTTPStatus = HTTPStatus.OK) -> None:
                encoded = content.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

            def _write_html(self, content: str, status: HTTPStatus = HTTPStatus.OK) -> None:
                encoded = content.encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(encoded)))
                self.end_headers()
                self.wfile.write(encoded)

        return RequestHandler

    @staticmethod
    def _current_time_iso() -> str:
        return datetime.utcnow().isoformat(timespec="seconds") + "Z"

    @staticmethod
    def _decode_assoc_value(value: Optional[object]) -> Optional[str]:
        if value is None:
            return None
        if isinstance(value, bytes):
            try:
                decoded = value.decode("utf-8", errors="ignore")
            except Exception:
                return None
            decoded = decoded.strip()
            return decoded or None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _peer_key(peer: Optional[object]) -> Optional[str]:
        if isinstance(peer, (list, tuple)) and len(peer) >= 2:
            return f"{peer[0]}:{peer[1]}"
        if peer is None:
            return None
        return str(peer)

    @staticmethod
    def _peer_host_port(peer: Optional[object]) -> tuple[Optional[str], Optional[int]]:
        host = None
        port = None
        if isinstance(peer, (list, tuple)) and len(peer) >= 2:
            host, port = peer[0], peer[1]
        elif isinstance(peer, str):
            host = peer
        elif hasattr(peer, "host"):
            host = getattr(peer, "host")
        if isinstance(host, bytes):
            try:
                host = host.decode("utf-8", errors="ignore")
            except Exception:
                host = None
        if host is not None:
            host = str(host).strip()
            if not host:
                host = None
        normalized_port = None
        if port is not None:
            try:
                normalized_port = int(port)
            except (TypeError, ValueError):
                normalized_port = None
        return host, normalized_port

    @staticmethod
    def _client_key(peer_host: Optional[str]) -> str:
        host = (peer_host or "").strip()
        if host:
            return host
        return "unknown"

    def _capture_snapshot_locked(self, force: bool = False) -> None:
        now = time.time()
        if not force and now - self._last_snapshot_time < 5:
            return
        snapshot = {
            "timestamp": self._current_time_iso(),
            "active": self._active_connections,
            "total": self._total_connections,
            "max": self._max_concurrent_connections,
        }
        self._connection_history.append(snapshot)
        self._last_snapshot_time = now

    def _register_peer_session(
        self,
        session_id: str,
        assoc,
        peer_key: Optional[str],
    ) -> None:
        if assoc is not None:
            self._assoc_session_map[id(assoc)] = session_id
        if peer_key:
            bucket = self._peer_session_map.setdefault(peer_key, [])
            bucket.append(session_id)

    def _release_peer_session(self, assoc, peer_key: Optional[str]) -> Optional[str]:
        session_id = None
        if assoc is not None:
            session_id = self._assoc_session_map.pop(id(assoc), None)
        if session_id is None and peer_key:
            bucket = self._peer_session_map.get(peer_key)
            if bucket:
                session_id = bucket.pop(0)
                if not bucket:
                    self._peer_session_map.pop(peer_key, None)
        return session_id

    def run(self, console: bool = False) -> None:
        self.logger = configure_logging(self.config, console=console)
        self.start_time = time.time()
        self.logger.info(
            "Starting DICOM server on %s:%s with status API at %s:%s",
            self.config.dicom_host,
            self.config.dicom_port,
            self.config.api_host,
            self.config.api_port,
        )

        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        self._start_dicom_service()
        self._start_api_server()

        try:
            self._main_loop()
        finally:
            self._shutdown_dicom_service()
            self._shutdown_api_server()
            self.logger.info("DICOM server stopped")


    def _render_dashboard(self) -> str:
        default_log_lines = self.config.log_tail_lines
        default_patient_limit = 50
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Orthanc DICOM Server</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
:root {{
  --bg: #0f141a;
  --bg-panel: #1c232c;
  --accent: #01a8ff;
  --accent-muted: #47c1ff;
  --text: #e6edf7;
  --text-muted: #9aa5b5;
  --border: #27303d;
  --status-ok: #17c964;
  --status-warn: #f5a524;
  --status-bad: #f31260;
  font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background-color: var(--bg); color: var(--text); }}
.topbar {{
  background: linear-gradient(135deg, #003f6b, #012136);
  padding: 1.5rem 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--border);
}}
.topbar h1 {{ margin: 0; font-size: 1.6rem; letter-spacing: 0.08em; text-transform: uppercase; }}
.topbar .meta {{ font-size: 0.9rem; color: var(--text-muted); text-align: right; }}
.container {{ padding: 2rem; max-width: 1200px; margin: 0 auto; }}
.card-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 1rem; margin-bottom: 2rem; }}
.card {{
  background-color: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1rem 1.2rem;
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.25);
}}
.card h2 {{ margin: 0 0 0.4rem 0; font-size: 0.85rem; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.08em; }}
.card .value {{ font-size: 1.6rem; font-weight: 600; }}
.card .sub {{ font-size: 0.85rem; color: var(--text-muted); margin-top: 0.3rem; }}
.status-label {{
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-weight: 600;
  border-radius: 99px;
  padding: 0.25rem 0.75rem;
  background-color: rgba(23, 201, 100, 0.14);
  color: var(--status-ok);
}}
.status-label.offline {{ background-color: rgba(243, 18, 96, 0.12); color: var(--status-bad); }}
.status-label.warn {{ background-color: rgba(245, 165, 36, 0.12); color: var(--status-warn); }}
.panel {{
  background-color: var(--bg-panel);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 1.5rem;
  margin-bottom: 2rem;
  box-shadow: 0 14px 34px rgba(0,0,0,0.35);
}}
.panel-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }}
.panel-header h2 {{ margin: 0; font-size: 1.1rem; letter-spacing: 0.05em; text-transform: uppercase; color: var(--text-muted); }}
.panel-controls {{ display: flex; gap: 1rem; align-items: center; }}
label {{ font-size: 0.85rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.08em; }}
input, select {{
  background-color: rgba(255,255,255,0.06);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 0.4rem 0.6rem;
}}
input:focus, select:focus {{ outline: 2px solid var(--accent); border-color: var(--accent); }}
button {{
  background: linear-gradient(135deg, var(--accent), var(--accent-muted));
  border: none;
  color: #0b1620;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 0.45rem 1.2rem;
  border-radius: 4px;
  cursor: pointer;
  box-shadow: 0 6px 14px rgba(1, 168, 255, 0.35);
}}
button:hover {{ filter: brightness(1.1); }}
table {{ width: 100%; border-collapse: collapse; font-size: 0.92rem; }}
thead tr {{ background-color: rgba(255,255,255,0.05); text-transform: uppercase; letter-spacing: 0.06em; font-size: 0.75rem; color: var(--text-muted); }}
th, td {{ padding: 0.65rem 0.75rem; border-bottom: 1px solid var(--border); text-align: left; }}
tbody tr:hover {{ background-color: rgba(71, 193, 255, 0.08); }}
tbody tr td.modality {{ font-weight: 600; color: var(--accent-muted); }}
.empty-state {{ text-align: center; padding: 2rem 0; color: var(--text-muted); }}
.table-wrapper {{ overflow-x: auto; }}
#connections-chart {{
  width: 100%;
  height: 240px;
  background-color: rgba(0,0,0,0.35);
  border: 1px solid var(--border);
  border-radius: 8px;
  display: block;
}}
.chart-meta {{
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  margin-top: 0.75rem;
  color: var(--text-muted);
  font-size: 0.85rem;
  flex-wrap: wrap;
}}
.chart-meta span {{
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}}
.pill {{
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  background-color: rgba(255,255,255,0.08);
  font-size: 0.78rem;
  color: var(--text);
}}
pre {{
  background-color: rgba(0,0,0,0.45);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 1rem;
  max-height: 360px;
  overflow-y: auto;
  font-family: "SFMono-Regular", Consolas, Monaco, 'Courier New', monospace;
  font-size: 0.85rem;
}}
.footer {{ text-align: center; padding: 1.5rem 0; color: var(--text-muted); font-size: 0.8rem; border-top: 1px solid var(--border); margin-top: 3rem; opacity: 0.85; }}
.badge {{ padding: 0.18rem 0.5rem; border-radius: 99px; background-color: rgba(255,255,255,0.07); font-size: 0.75rem; margin-left: 0.4rem; }}
.grid-two {{ display: grid; gap: 1.5rem; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); }}
a {{ color: var(--accent); text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
<header class="topbar">
  <div>
    <h1>Orthanc DICOM Server</h1>
    <div class="meta">Application Entity: <strong id="meta-ae">{self.config.ae_title}</strong></div>
  </div>
  <div class="meta" id="meta-updated">Updating…</div>
</header>
<main class="container">
  <section class="card-grid">
    <div class="card">
      <h2>Server Status</h2>
      <div class="value" id="card-status"><span class="status-label offline">Offline</span></div>
      <div class="sub" id="card-uptime">Uptime —</div>
    </div>
    <div class="card">
      <h2>Active Associations</h2>
      <div class="value" id="card-active">0</div>
      <div class="sub" id="card-total">0 total</div>
    </div>
    <div class="card">
      <h2>Stored Objects</h2>
      <div class="value" id="card-cstore">0</div>
      <div class="sub" id="card-unique">0 unique patients</div>
    </div>
    <div class="card">
      <h2>HTTP API</h2>
      <div class="value" id="card-api"><span class="status-label warn">Checking…</span></div>
      <div class="sub">Listening on <span id="card-endpoint"></span></div>
    </div>
    <div class="card">
      <h2>Max Concurrent</h2>
      <div class="value" id="card-max">0</div>
      <div class="sub" id="card-max-info">Peak 0 observed</div>
    </div>
    <div class="card">
      <h2>Unique Clients</h2>
      <div class="value" id="card-clients">0</div>
      <div class="sub" id="card-clients-active">0 active IPs</div>
    </div>
  </section>

  <section class="panel" id="connections-panel">
    <div class="panel-header">
      <h2>Connection Timeline</h2>
      <div class="panel-controls">
        <span id="connections-chart-summary">Awaiting activity…</span>
      </div>
    </div>
    <canvas id="connections-chart" width="960" height="240"></canvas>
    <div class="chart-meta">
      <span id="connections-chart-range">Range —</span>
      <span id="connections-chart-max">Max —</span>
    </div>
  </section>

  <section class="panel" id="clients-panel">
    <div class="panel-header">
      <h2>DICOM Clients</h2>
      <div class="panel-controls">
        <span class="badge" id="clients-badge">No clients yet</span>
      </div>
    </div>
    <div class="table-wrapper">
      <table id="clients-table">
        <thead>
          <tr>
            <th>Last Seen</th>
            <th>Client IP</th>
            <th>AE Title</th>
            <th>Version</th>
            <th>Sessions</th>
            <th>Recent Activity</th>
          </tr>
        </thead>
        <tbody>
          <tr class="empty-state"><td colspan="6">No DICOM clients connected yet.</td></tr>
        </tbody>
      </table>
    </div>
  </section>

  <section class="panel" id="patients-panel">
    <div class="panel-header">
      <h2>Recent Patients</h2>
      <div class="panel-controls">
        <label for="patient-limit">Rows</label>
        <input type="number" id="patient-limit" min="1" max="200" value="{default_patient_limit}">
        <button id="refresh-patients">Refresh</button>
      </div>
    </div>
    <div class="table-wrapper">
      <table id="patients-table">
        <thead>
          <tr>
            <th>Received</th>
            <th>Patient Name</th>
            <th>Patient ID</th>
            <th>Modality</th>
            <th>Study Description</th>
            <th>Body Part</th>
            <th>SOP Instance UID</th>
          </tr>
        </thead>
        <tbody>
          <tr class="empty-state"><td colspan="7">Awaiting C-STORE traffic…</td></tr>
        </tbody>
      </table>
    </div>
  </section>

  <section class="panel">
    <div class="panel-header">
      <h2>Server Logs</h2>
      <div class="panel-controls">
        <label for="log-lines">Lines</label>
        <input type="number" id="log-lines" min="1" max="{LOG_TAIL_MAX}" value="{default_log_lines}">
        <button id="refresh-logs">Refresh</button>
      </div>
    </div>
    <pre id="logs">Loading log buffer…</pre>
  </section>

  <section class="panel">
    <div class="panel-header">
      <h2>REST API Endpoints</h2>
    </div>
    <div class="grid-two">
      <div>
        <strong>Status</strong><span class="badge">GET</span><br>
        <code>/api/status</code>
      </div>
      <div>
        <strong>Patients</strong><span class="badge">GET</span><br>
        <code>/api/patients?limit=N</code>
      </div>
      <div>
        <strong>Logs</strong><span class="badge">GET</span><br>
        <code>/api/logs?format=json&amp;lines=N</code>
      </div>
      <div>
        <strong>Health</strong><span class="badge">GET</span><br>
        <code>/healthz</code>
      </div>
    </div>
  </section>
</main>
<div class="footer">Orthanc DICOM Server &mdash; simulated interface for demonstration purposes</div>

<script>
const STATUS_ENDPOINT = '/api/status';
const PATIENTS_ENDPOINT = '/api/patients';
const LOGS_ENDPOINT = '/api/logs';
const DEFAULT_PATIENT_LIMIT = {default_patient_limit};
const DEFAULT_LOG_LINES = {default_log_lines};

function formatUptime(seconds) {{
  if (!Number.isFinite(seconds)) return 'Uptime —';
  const units = [
    {{ label: 'd', value: 86400 }},
    {{ label: 'h', value: 3600 }},
    {{ label: 'm', value: 60 }},
    {{ label: 's', value: 1 }}
  ];
  let remaining = Math.max(0, Math.floor(seconds));
  const parts = [];
  for (const unit of units) {{
    const amount = Math.floor(remaining / unit.value);
    if (amount > 0 || unit.label === 's') {{
      parts.push(amount + unit.label);
      remaining -= amount * unit.value;
    }}
  }}
  return 'Uptime ' + parts.slice(0, 3).join(' ');
}}

function formatDuration(seconds) {{
  if (!Number.isFinite(seconds) || seconds <= 0) return '—';
  const units = [
    {{ label: 'h', value: 3600 }},
    {{ label: 'm', value: 60 }},
    {{ label: 's', value: 1 }},
  ];
  let remaining = Math.floor(seconds);
  const parts = [];
  for (const unit of units) {{
    const amount = Math.floor(remaining / unit.value);
    if (amount > 0 || (unit.label === 's' && parts.length === 0)) {{
      parts.push(amount + unit.label);
      remaining -= amount * unit.value;
    }}
    if (parts.length === 2) break;
  }}
  return parts.join(' ');
}}

function formatTimestamp(isoString) {{
  if (!isoString) return '—';
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return isoString;
  return date.toLocaleString();
}}

function describeRecentSession(sessions) {{
  if (!Array.isArray(sessions) || sessions.length === 0) return 'No session history yet.';
  const session = sessions.find((item) => item && item.started_at);
  if (!session) return 'No session history yet.';
  const started = formatTimestamp(session.started_at);
  if (!session.ended_at) {{
    const duration = formatDuration(session.duration_seconds);
    if (duration === '—') {{
      return `Active since ${{started}}`;
    }}
    return `Active since ${{started}} • ${{duration}}`;
  }}
  const ended = formatTimestamp(session.ended_at);
  const duration = formatDuration(session.duration_seconds);
  if (duration === '—') {{
    return `Ended ${{ended}}`;
  }}
  return `Ended ${{ended}} (${{duration}})`;
}}

function updateStatusCards(data) {{
  const statusLabel = document.getElementById('card-status');
  const uptimeLabel = document.getElementById('card-uptime');
  const activeLabel = document.getElementById('card-active');
  const totalLabel = document.getElementById('card-total');
  const cstoreLabel = document.getElementById('card-cstore');
  const uniqueLabel = document.getElementById('card-unique');
  const apiLabel = document.getElementById('card-api');
  const endpointLabel = document.getElementById('card-endpoint');
  const metaUpdated = document.getElementById('meta-updated');
  const maxLabel = document.getElementById('card-max');
  const maxInfo = document.getElementById('card-max-info');
  const clientsLabel = document.getElementById('card-clients');
  const clientsActiveLabel = document.getElementById('card-clients-active');
  const clientsBadge = document.getElementById('clients-badge');

  const online = data?.dicom_online;
  const apiOnline = data?.api_online;

  statusLabel.innerHTML = online
    ? '<span class="status-label">Online</span>'
    : '<span class="status-label offline">Offline</span>';

  apiLabel.innerHTML = apiOnline
    ? '<span class="status-label">Listening</span>'
    : '<span class="status-label warn">Unavailable</span>';

  uptimeLabel.textContent = formatUptime(data?.uptime_seconds ?? 0);
  activeLabel.textContent = data?.dicom_active_connections ?? 0;
  totalLabel.textContent = `${{data?.dicom_total_connections ?? 0}} total associations`;
  cstoreLabel.textContent = data?.total_c_store ?? 0;
  uniqueLabel.textContent = `${{data?.unique_patients ?? 0}} unique patients`;
  endpointLabel.textContent = `http://${{data?.api_host ?? '0.0.0.0'}}:${{data?.api_port ?? ''}}`;
  const maxConcurrent = data?.dicom_max_concurrent_connections ?? 0;
  const activeConnections = data?.dicom_active_connections ?? 0;
  if (maxLabel) maxLabel.textContent = maxConcurrent;
  if (maxInfo) maxInfo.textContent = `Current ${{activeConnections}} active`;

  const clients = Array.isArray(data?.clients) ? data.clients : [];
  const totalClients = data?.known_client_count ?? clients.length;
  const activeClients = data?.active_client_count ?? clients.filter((client) => (client?.active_sessions ?? 0) > 0).length;
  if (clientsLabel) {{
    clientsLabel.textContent = totalClients;
  }}
  if (clientsActiveLabel) {{
    const activeSuffix = activeClients === 1 ? 'IP' : 'IPs';
    clientsActiveLabel.textContent = `${{activeClients}} active ${{activeSuffix}}`;
  }}
  if (clientsBadge) {{
    if (totalClients === 0) {{
      clientsBadge.textContent = 'No clients yet';
    }} else {{
      const uniqueSuffix = totalClients === 1 ? 'unique IP' : 'unique IPs';
      const activeSuffix = activeClients === 1 ? 'active IP' : 'active IPs';
      clientsBadge.textContent = `${{activeClients}} ${{activeSuffix}} of ${{totalClients}} ${{uniqueSuffix}}`;
    }}
  }}

  renderClientsTable(clients);
  renderConnectionTimeline(data?.connection_history || []);
  metaUpdated.textContent = 'Updated ' + new Date().toLocaleTimeString();
}}

function renderPatientsTable(records) {{
  const tbody = document.querySelector('#patients-table tbody');
  tbody.innerHTML = '';
  if (!Array.isArray(records) || records.length === 0) {{
    const row = document.createElement('tr');
    row.className = 'empty-state';
    const cell = document.createElement('td');
    cell.colSpan = 7;
    cell.textContent = 'No patient records available.';
    row.appendChild(cell);
    tbody.appendChild(row);
    return;
  }}

  for (const record of records) {{
    const row = document.createElement('tr');
    const cells = [
      record.received_at,
      record.patient_name,
      record.patient_id,
      record.modality,
      record.study_description,
      record.body_part,
      record.sop_instance_uid,
    ];
    cells.forEach((value, index) => {{
      const cell = document.createElement('td');
      if (index === 3) cell.className = 'modality';
      cell.textContent = value || '—';
      row.appendChild(cell);
    }});
    tbody.appendChild(row);
  }}
}}

function renderClientsTable(clients) {{
  const tbody = document.querySelector('#clients-table tbody');
  if (!tbody) return;
  tbody.innerHTML = '';
  if (!Array.isArray(clients) || clients.length === 0) {{
    const row = document.createElement('tr');
    row.className = 'empty-state';
    const cell = document.createElement('td');
    cell.colSpan = 6;
    cell.textContent = 'No DICOM clients connected yet.';
    row.appendChild(cell);
    tbody.appendChild(row);
    return;
  }}

  const sorted = [...clients].sort((a, b) => {{
    const activeA = a?.active_sessions ?? 0;
    const activeB = b?.active_sessions ?? 0;
    if (activeA !== activeB) return activeB - activeA;
    const totalA = a?.total_sessions ?? 0;
    const totalB = b?.total_sessions ?? 0;
    if (totalA !== totalB) return totalB - totalA;
    const ipA = (a?.ip ?? '').toString();
    const ipB = (b?.ip ?? '').toString();
    return ipA.localeCompare(ipB);
  }});

  for (const client of sorted) {{
    const row = document.createElement('tr');

    const lastSeenCell = document.createElement('td');
    lastSeenCell.textContent = formatTimestamp(client?.last_seen);
    row.appendChild(lastSeenCell);

    const clientCell = document.createElement('td');
    let clientText = client?.ip || '—';
    if (client?.last_remote_port) {{
      clientText += `:${{client.last_remote_port}}`;
    }}
    clientCell.textContent = clientText;
    row.appendChild(clientCell);

    const aeCell = document.createElement('td');
    const aeTitles = Array.isArray(client?.known_ae_titles)
      ? client.known_ae_titles.filter((title) => title && title.toUpperCase() !== 'UNKNOWN')
      : [];
    let aeDisplay = client?.ae_title || '—';
    if (aeTitles.length === 1) {{
      aeDisplay = aeTitles[0];
    }} else if (aeTitles.length > 1) {{
      aeDisplay = `${{aeTitles[0]}} (+${{aeTitles.length - 1}} more)`;
      aeCell.title = aeTitles.join(', ');
    }}
    if (typeof aeDisplay === 'string' && aeDisplay.toUpperCase() === 'UNKNOWN') {{
      aeDisplay = '—';
    }}
    aeCell.textContent = aeDisplay;
    if (!aeCell.title && client?.ae_title && client.ae_title.toUpperCase() !== 'UNKNOWN') {{
      aeCell.title = client.ae_title;
    }}
    row.appendChild(aeCell);

    const versionCell = document.createElement('td');
    const versions = Array.isArray(client?.known_implementation_versions)
      ? client.known_implementation_versions.filter((item) => item && item.toUpperCase() !== 'UNKNOWN')
      : [];
    let versionDisplay = client?.implementation_version || '—';
    if (versions.length === 1) {{
      versionDisplay = versions[0];
    }} else if (versions.length > 1) {{
      versionDisplay = `${{versions[0]}} (+${{versions.length - 1}} more)`;
    }}
    if (typeof versionDisplay === 'string' && versionDisplay.toUpperCase() === 'UNKNOWN') {{
      versionDisplay = '—';
    }}
    versionCell.textContent = versionDisplay;
    const uidList = Array.isArray(client?.known_implementation_class_uids)
      ? client.known_implementation_class_uids.filter((item) => item && item.toUpperCase() !== 'UNKNOWN')
      : [];
    if (uidList.length === 0 && client?.implementation_class_uid && client.implementation_class_uid.toUpperCase() !== 'UNKNOWN') {{
      uidList.push(client.implementation_class_uid);
    }}
    const uniqueUidList = Array.from(new Set(uidList));
    if (uniqueUidList.length > 0) {{
      const uidLabel = uniqueUidList.length === 1 ? 'Implementation UID' : 'Implementation UIDs';
      versionCell.title = `${{uidLabel}}: ${{uniqueUidList.join(', ')}}`;
    }}
    row.appendChild(versionCell);

    const sessionsCell = document.createElement('td');
    const active = client?.active_sessions ?? 0;
    const total = client?.total_sessions ?? 0;
    const pill = document.createElement('span');
    pill.className = 'pill';
    pill.textContent = `${{active}} active`;
    sessionsCell.appendChild(pill);
    sessionsCell.appendChild(document.createTextNode(` / ${{total}} total`));
    row.appendChild(sessionsCell);

    const recentCell = document.createElement('td');
    recentCell.textContent = describeRecentSession(client?.recent_sessions);
    row.appendChild(recentCell);

    tbody.appendChild(row);
  }}
}}

function renderConnectionTimeline(history) {{
  const canvas = document.getElementById('connections-chart');
  const summaryEl = document.getElementById('connections-chart-summary');
  const rangeEl = document.getElementById('connections-chart-range');
  const maxEl = document.getElementById('connections-chart-max');
  if (!canvas || !summaryEl || !rangeEl || !maxEl) return;

  const ctx = canvas.getContext('2d');
  if (!ctx) return;

  const rect = canvas.getBoundingClientRect();
  const width = Math.max(rect.width || canvas.width || 960, 320);
  const height = Math.max(rect.height || canvas.height || 240, 200);
  const dpr = window.devicePixelRatio || 1;

  if (canvas.width !== width * dpr || canvas.height !== height * dpr) {{
    canvas.width = width * dpr;
    canvas.height = height * dpr;
  }}
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, width, height);

  const points = Array.isArray(history)
    ? history
        .map((item) => {{
          const ts = item?.timestamp ? new Date(item.timestamp).getTime() : null;
          if (!Number.isFinite(ts)) return null;
          const active = Number.isFinite(item.active)
            ? item.active
            : Number(item.active_connections ?? item.active ?? 0);
          const total = Number.isFinite(item.total)
            ? item.total
            : Number(item.total_connections ?? item.total ?? 0);
          const max = Number.isFinite(item.max)
            ? item.max
            : Number(item.max_concurrent ?? item.max ?? active);
          return {{ ts, active, total, max, label: item.timestamp }};
        }})
        .filter(Boolean)
    : [];

  if (points.length === 0) {{
    summaryEl.textContent = 'Awaiting activity…';
    rangeEl.textContent = 'Range —';
    maxEl.textContent = 'Max —';
    ctx.fillStyle = 'rgba(255,255,255,0.45)';
    ctx.font = '16px "Segoe UI", sans-serif';
    ctx.fillText('No connection activity recorded yet', 24, height / 2);
    return;
  }}

  points.sort((a, b) => a.ts - b.ts);
  const minTs = points[0].ts;
  const maxTs = points[points.length - 1].ts;
  const span = Math.max(1, maxTs - minTs);
  const maxActive = points.reduce(
    (acc, point) => Math.max(acc, Number.isFinite(point.active) ? point.active : 0),
    0
  );
  const observedMax = points.reduce(
    (acc, point) => Math.max(acc, Number.isFinite(point.max) ? point.max : 0),
    maxActive
  );
  const baseline = Math.max(1, observedMax);

  const margin = {{ left: 54, right: 24, top: 24, bottom: 32 }};
  const plotWidth = Math.max(1, width - margin.left - margin.right);
  const plotHeight = Math.max(1, height - margin.top - margin.bottom);

  ctx.strokeStyle = 'rgba(255,255,255,0.18)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(margin.left, margin.top);
  ctx.lineTo(margin.left, height - margin.bottom);
  ctx.lineTo(width - margin.right, height - margin.bottom);
  ctx.stroke();

  const bands = 4;
  for (let i = 0; i <= bands; i += 1) {{
    const value = (baseline / bands) * i;
    const y = height - margin.bottom - (plotHeight * (value / baseline));
    ctx.strokeStyle = 'rgba(255,255,255,0.08)';
    ctx.beginPath();
    ctx.moveTo(margin.left, y);
    ctx.lineTo(width - margin.right, y);
    ctx.stroke();
    if (i > 0) {{
      ctx.fillStyle = 'rgba(255,255,255,0.42)';
      ctx.font = '12px "Segoe UI", sans-serif';
      ctx.fillText(String(Math.round(value)), 12, y + 4);
    }}
  }}

  for (const point of points) {{
    const relative = span === 0 ? 0 : (point.ts - minTs) / span;
    const activeValue = Number.isFinite(point.active) ? point.active : 0;
    point.x = margin.left + plotWidth * relative;
    point.y = height - margin.bottom - plotHeight * (activeValue / baseline);
  }}

  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);
  for (let i = 1; i < points.length; i += 1) {{
    ctx.lineTo(points[i].x, points[i].y);
  }}
  ctx.lineTo(points[points.length - 1].x, height - margin.bottom);
  ctx.lineTo(points[0].x, height - margin.bottom);
  ctx.closePath();
  ctx.fillStyle = 'rgba(1, 168, 255, 0.18)';
  ctx.fill();

  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);
  for (let i = 1; i < points.length; i += 1) {{
    ctx.lineTo(points[i].x, points[i].y);
  }}
  ctx.strokeStyle = '#47c1ff';
  ctx.lineWidth = 2;
  ctx.stroke();

  const last = points[points.length - 1];
  ctx.fillStyle = '#47c1ff';
  ctx.beginPath();
  ctx.arc(last.x, last.y, 4, 0, Math.PI * 2);
  ctx.fill();

  const lastActive = Number.isFinite(last.active) ? last.active : 0;
  const lastTotal = Number.isFinite(last.total) ? last.total : 0;
  const peak = Math.max(observedMax, lastActive);
  const peakDisplay = Number.isFinite(peak) ? Math.round(peak) : 0;
  summaryEl.textContent = `Active ${{lastActive}} connections • Total ${{lastTotal}} associations`;
  if (minTs === maxTs) {{
    rangeEl.textContent = `Range ${{new Date(minTs).toLocaleString()}}`;
  }} else {{
    rangeEl.textContent = `Range ${{new Date(minTs).toLocaleString()}} — ${{new Date(maxTs).toLocaleString()}}`;
  }}
  maxEl.textContent = `Peak ${{peakDisplay}}`;
}}

async function refreshStatus() {{
  try {{
    const response = await fetch(STATUS_ENDPOINT, {{ headers: {{ 'Accept': 'application/json' }} }});
    if (!response.ok) throw new Error('Status ' + response.status);
    const data = await response.json();
    updateStatusCards(data);
  }} catch (error) {{
    console.error('Status refresh failed', error);
  }}
}}

async function refreshPatients() {{
  const limitInput = document.getElementById('patient-limit');
  let limit = parseInt(limitInput.value, 10);
  if (!Number.isFinite(limit) || limit <= 0) {{
    limit = DEFAULT_PATIENT_LIMIT;
    limitInput.value = limit;
  }}
  try {{
    const response = await fetch(`${{PATIENTS_ENDPOINT}}?limit=${{limit}}`, {{ headers: {{ 'Accept': 'application/json' }} }});
    if (!response.ok) throw new Error('Status ' + response.status);
    const data = await response.json();
    renderPatientsTable(data.records || []);
  }} catch (error) {{
    console.error('Patient refresh failed', error);
  }}
}}

async function refreshLogs() {{
  const logsEl = document.getElementById('logs');
  const linesInput = document.getElementById('log-lines');
  let lines = parseInt(linesInput.value, 10);
  if (!Number.isFinite(lines) || lines <= 0) {{
    lines = DEFAULT_LOG_LINES;
    linesInput.value = lines;
  }}
  try {{
    const response = await fetch(`${{LOGS_ENDPOINT}}?format=text&lines=${{lines}}`, {{ headers: {{ 'Accept': 'text/plain' }} }});
    if (!response.ok) throw new Error('Status ' + response.status);
    const text = await response.text();
    logsEl.textContent = text || '(log buffer empty)';
  }} catch (error) {{
    logsEl.textContent = 'Error retrieving logs: ' + error.message;
  }}
}}

document.getElementById('refresh-logs').addEventListener('click', refreshLogs);
document.getElementById('refresh-patients').addEventListener('click', () => {{
  refreshPatients();
}});

refreshStatus();
refreshPatients();
refreshLogs();
setInterval(refreshStatus, 8000);
setInterval(refreshPatients, 12000);
setInterval(refreshLogs, 20000);
</script>
</body>
</html>
"""

    def _main_loop(self) -> None:
        heartbeat_interval = self.config.heartbeat_interval
        while not self._stop_event.wait(timeout=heartbeat_interval):
            uptime = time.time() - (self.start_time or time.time())
            self.logger.info("Heartbeat - uptime %.1fs", uptime)

    def _start_api_server(self) -> None:
        handler = self._create_request_handler()
        try:
            self.httpd = ThreadedHTTPServer(
                (self.config.api_host, self.config.api_port), handler
            )
        except OSError as exc:
            self.logger.error(
                "Failed to start status API on %s:%s - %s",
                self.config.api_host,
                self.config.api_port,
                exc,
            )
            self.httpd = None
            return

        self._api_thread = threading.Thread(
            target=self.httpd.serve_forever, name="StatusAPI", daemon=True
        )
        self._api_thread.start()
        self.logger.info(
            "Status API started at http://%s:%s",
            self.config.api_host,
            self.config.api_port,
        )

    def _start_dicom_service(self) -> None:
        handlers = self._build_dicom_event_handlers()
        if not self._dicom_debug_configured:
            debug_logger()
            self._dicom_debug_configured = True
        ae_title_bytes = self.config.ae_title.encode("ascii", errors="ignore")
        self._dicom_ae = AE(ae_title=ae_title_bytes)

        transfer_syntaxes = [
            ExplicitVRLittleEndian,
            ImplicitVRLittleEndian,
            ExplicitVRBigEndian,
        ]

        for context in AllStoragePresentationContexts:
            self._dicom_ae.add_supported_context(context.abstract_syntax, transfer_syntaxes)

        # Ensure angiographic storage also supports JPEG Baseline as seen in the legacy script.
        self._dicom_ae.add_supported_context(
            XRayAngiographicImageStorage, [JPEGBaseline]
        )

        try:
            self._dicom_server = self._dicom_ae.start_server(
                (self.config.dicom_host, self.config.dicom_port),
                block=False,
                evt_handlers=handlers,
            )
        except OSError as exc:
            self.logger.error(
                "Failed to bind DICOM AE on %s:%s - %s",
                self.config.dicom_host,
                self.config.dicom_port,
                exc,
            )
            self._dicom_server = None
            self._dicom_ae = None
            return

        self.logger.info(
            "DICOM AE '%s' started on %s:%s",
            self.config.ae_title,
            self.config.dicom_host,
            self.config.dicom_port,
        )

    def _shutdown_api_server(self) -> None:
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None
        if self._api_thread:
            self._api_thread.join(timeout=5)
            self._api_thread = None

    def _shutdown_dicom_service(self) -> None:
        if self._dicom_server:
            with contextlib.suppress(Exception):
                self._dicom_server.shutdown()
            with contextlib.suppress(Exception):
                self._dicom_server.join(timeout=5)
            self._dicom_server = None
        if self._dicom_ae:
            with contextlib.suppress(Exception):
                self._dicom_ae.shutdown()
            self._dicom_ae = None

    def status_payload(self) -> Dict[str, object]:
        uptime = None
        if self.start_time:
            uptime = time.time() - self.start_time
        with self._connections_lock:
            self._capture_snapshot_locked(force=False)
            clients_list = list(self._client_stats.values())
            clients_payload = sorted(
                (client.to_payload() for client in clients_list),
                key=lambda item: (
                    -(item.get("active_sessions") or 0),
                    -(item.get("total_sessions") or 0),
                    item.get("ip") or "",
                ),
            )
            active_client_count = sum(
                1 for client in clients_payload if (client.get("active_sessions") or 0) > 0
            )
            connection_history = list(self._connection_history)
            max_concurrent = self._max_concurrent_connections
        return {
            "status": "stopping" if self._stop_event.is_set() else "running",
            "pid": os.getpid(),
            "dicom_host": self.config.dicom_host,
            "dicom_port": self.config.dicom_port,
            "api_host": self.config.api_host,
            "api_port": self.config.api_port,
            "api_online": bool(self.httpd),
            "dicom_online": bool(self._dicom_server),
            "dicom_active_connections": self._active_connections,
            "dicom_total_connections": self._total_connections,
            "dicom_max_concurrent_connections": max_concurrent,
            "ae_title": self.config.ae_title,
            "total_c_store": self._total_c_store,
            "recent_patient_records": len(self._patient_records),
            "unique_patients": len(self._unique_patients),
            "uptime_seconds": uptime,
            "log_file": str(self.config.log_file),
            "pid_file": str(self.config.pid_file),
            "config": self.config.as_dict(),
            "clients": clients_payload,
            "known_client_count": len(clients_payload),
            "active_client_count": active_client_count,
            "connection_history": connection_history,
        }

    def tail_logs(self, max_lines: int) -> List[str]:
        log_path = self.config.log_file
        if not log_path.exists():
            return []
        try:
            with log_path.open("r", encoding="utf-8") as handle:
                lines = handle.readlines()
        except OSError as exc:
            self.logger.error("Failed to read log file: %s", exc)
            return []
        return [line.rstrip("\n") for line in lines[-max_lines:]]

    def patients_payload(self, limit: Optional[int] = None) -> Dict[str, object]:
        with self._patient_lock:
            records = list(self._patient_records)
            total_c_store = self._total_c_store
            unique_patients = len(self._unique_patients)

        if limit is not None and limit >= 0:
            records = records[:limit]

        return {
            "total_c_store": total_c_store,
            "unique_patients": unique_patients,
            "returned_records": len(records),
            "records": records,
        }

    def _handle_signal(self, signum, _frame) -> None:  # type: ignore[override]
        self.logger.info("Received signal %s, shutting down", signum)
        self.stop()

    def stop(self) -> None:
        self._stop_event.set()

    def _build_dicom_event_handlers(self):
        return [
            (evt.EVT_CONN_OPEN, self._handle_dicom_connection_open),
            (evt.EVT_ACCEPTED, self._handle_dicom_association_accepted),
            (evt.EVT_CONN_CLOSE, self._handle_dicom_connection_close),
            (evt.EVT_C_STORE, self._handle_c_store),
        ]

    def _handle_dicom_connection_open(self, event):
        peer = getattr(event, "address", None)
        if peer is None and hasattr(event, "assoc"):
            try:
                peer = event.assoc.get_peer_addr()
            except Exception:  # pragma: no cover - defensive
                peer = None
        assoc = getattr(event, "assoc", None)
        peer_host, peer_port = self._peer_host_port(peer)

        calling_ae = None
        impl_version = None
        impl_class_uid = None
        if assoc is not None:
            calling_ae = self._decode_assoc_value(getattr(assoc.requestor, "ae_title", None))
            impl_version = self._decode_assoc_value(
                getattr(assoc.requestor, "implementation_version_name", None)
            )
            impl_class_uid = self._decode_assoc_value(
                getattr(assoc.requestor, "implementation_class_uid", None)
            )

        now_iso = self._current_time_iso()
        session_id = f"session-{time.time_ns()}"
        peer_key = self._peer_key(peer)

        with self._connections_lock:
            self._active_connections += 1
            self._total_connections += 1
            if self._active_connections > self._max_concurrent_connections:
                self._max_concurrent_connections = self._active_connections

            client_key = self._client_key(peer_host)
            client = self._client_stats.get(client_key)
            if not client:
                client = ClientStats(
                    key=client_key,
                    ip=peer_host or "unknown",
                    ae_title=calling_ae or "UNKNOWN",
                )
                client.first_seen = now_iso
                self._client_stats[client_key] = client
            client.key = client_key

            if peer_host:
                client.ip = peer_host
            client.note_identity(calling_ae, impl_version, impl_class_uid)
            if peer_port is not None:
                client.last_remote_port = int(peer_port)
            
            client.total_sessions += 1
            client.active_sessions += 1
            client.last_seen = now_iso
            if client.first_seen is None:
                client.first_seen = now_iso

            session_entry = {
                "session_id": session_id,
                "started_at": now_iso,
                "ended_at": None,
                "duration_seconds": None,
                "remote_port": peer_port,
                "started_ts": time.time(),
            }
            client.recent_sessions.appendleft(session_entry)
            self._session_index[session_id] = client_key
            self._session_entries[session_id] = session_entry
            self._register_peer_session(session_id, assoc, peer_key)
            self._capture_snapshot_locked(force=True)

        if peer_host or peer_port:
            extra = []
            if calling_ae:
                extra.append(f"AE={calling_ae}")
            if impl_version:
                extra.append(f"impl={impl_version}")
            extra_text = f" ({', '.join(extra)})" if extra else ""
            peer_desc = f"{peer_host}:{peer_port}" if peer_host and peer_port is not None else (
                peer_host or str(peer)
            )
            self.logger.info("Accepted DICOM association from %s%s", peer_desc, extra_text)
        else:
            self.logger.info("Accepted DICOM association")

    def _handle_dicom_connection_close(self, event):
        peer = getattr(event, "address", None)
        if peer is None and hasattr(event, "assoc"):
            try:
                peer = event.assoc.get_peer_addr()
            except Exception:  # pragma: no cover - defensive
                peer = None
        assoc = getattr(event, "assoc", None)
        peer_host, peer_port = self._peer_host_port(peer)
        peer_key = self._peer_key(peer)

        with self._connections_lock:
            self._active_connections = max(0, self._active_connections - 1)
            session_id = self._release_peer_session(assoc, peer_key)
            now_iso = self._current_time_iso()
            if session_id:
                client_key = self._session_index.pop(session_id, None)
                session_entry = self._session_entries.pop(session_id, None)
                if client_key:
                    client = self._client_stats.get(client_key)
                    if client:
                        client.active_sessions = max(0, client.active_sessions - 1)
                        client.last_seen = now_iso
                    if session_entry:
                        session_entry["ended_at"] = now_iso
                        started_ts = session_entry.get("started_ts")
                        if isinstance(started_ts, (int, float)):
                            duration = max(0.0, time.time() - started_ts)
                            session_entry["duration_seconds"] = round(duration, 2)
                        session_entry.pop("started_ts", None)
                        session_entry.pop("session_id", None)
                else:
                    if session_entry:
                        session_entry.pop("started_ts", None)
                        session_entry.pop("session_id", None)
            self._capture_snapshot_locked(force=True)

        if peer_host or peer_port:
            peer_desc = f"{peer_host}:{peer_port}" if peer_host and peer_port is not None else (
                peer_host or str(peer)
            )
            self.logger.info("Closed DICOM association from %s", peer_desc)
        else:
            self.logger.info("Closed DICOM association")

    def _handle_dicom_association_accepted(self, event) -> None:
        assoc = getattr(event, "assoc", None)
        if assoc is None:
            return
        try:
            peer = assoc.get_peer_addr()
        except Exception:
            peer = None
        peer_host, peer_port = self._peer_host_port(peer)
        calling_ae = self._decode_assoc_value(getattr(assoc.requestor, "ae_title", None))
        impl_version = self._decode_assoc_value(
            getattr(assoc.requestor, "implementation_version_name", None)
        )
        impl_class_uid = self._decode_assoc_value(
            getattr(assoc.requestor, "implementation_class_uid", None)
        )
        now_iso = self._current_time_iso()
        with self._connections_lock:
            session_id = self._assoc_session_map.get(id(assoc))
            client_key = self._session_index.get(session_id) if session_id else None
            client = self._client_stats.get(client_key) if client_key else None
            new_key = self._client_key(peer_host)
            if client is None:
                client = self._client_stats.get(new_key)
            if client is None:
                client = ClientStats(
                    key=new_key,
                    ip=peer_host or "unknown",
                    ae_title=calling_ae or "UNKNOWN",
                )
                client.first_seen = now_iso
                self._client_stats[new_key] = client
            if session_id and self._session_index.get(session_id) != new_key:
                self._session_index[session_id] = new_key
            if client_key and new_key != client_key:
                # Re-key existing client so future lookups use populated AE
                self._client_stats.pop(client_key, None)
                client.key = new_key
                self._client_stats[new_key] = client
                if session_id:
                    self._session_index[session_id] = new_key
                for sid, key in list(self._session_index.items()):
                    if key == client_key:
                        self._session_index[sid] = new_key
            client.key = new_key
            if peer_host:
                client.ip = peer_host
            client.note_identity(calling_ae, impl_version, impl_class_uid)
            if peer_port is not None:
                client.last_remote_port = peer_port
            if session_id:
                entry = self._session_entries.get(session_id)
                if entry and peer_port is not None:
                    entry["remote_port"] = peer_port
            client.last_seen = now_iso
            if client.first_seen is None:
                client.first_seen = now_iso
            self._connection_history.append(
                {
                    "timestamp": now_iso,
                    "active": self._active_connections,
                    "total": self._total_connections,
                    "max": self._max_concurrent_connections,
                }
            )
            self._last_snapshot_time = time.time()

    def _handle_c_store(self, event):
        dataset = event.dataset
        dataset.file_meta = event.file_meta

        self.logger.info("Received C-STORE request")
        try:
            sop_instance = dataset.SOPInstanceUID
        except AttributeError:
            sop_instance = "<unknown>"

        patient_name = self._stringify(dataset.get("PatientName"), "Unknown")
        patient_id = self._stringify(dataset.get("PatientID"), "Unknown")
        modality = self._stringify(dataset.get("Modality"), "Unknown")
        body_part = self._stringify(dataset.get("BodyPartExamined"), "Unknown")
        study_description = self._stringify(dataset.get("StudyDescription"), "")
        series_description = self._stringify(dataset.get("SeriesDescription"), "")
        accession_number = self._stringify(dataset.get("AccessionNumber"), "")
        study_instance_uid = self._stringify(dataset.get("StudyInstanceUID"), "")
        series_instance_uid = self._stringify(dataset.get("SeriesInstanceUID"), "")
        study_date = self._stringify(dataset.get("StudyDate"), "")
        study_time = self._stringify(dataset.get("StudyTime"), "")
        institution_name = self._stringify(dataset.get("InstitutionName"), "")

        self.logger.info(
            "SOPInstanceUID=%s PatientName=%s PatientID=%s Modality=%s BodyPart=%s",
            sop_instance,
            patient_name,
            patient_id,
            modality,
            body_part,
        )

        received_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        record = {
            "received_at": received_at,
            "patient_name": patient_name,
            "patient_id": patient_id,
            "modality": modality,
            "body_part": body_part,
            "study_description": study_description,
            "series_description": series_description,
            "accession_number": accession_number,
            "study_instance_uid": study_instance_uid,
            "series_instance_uid": series_instance_uid,
            "sop_instance_uid": sop_instance,
            "study_date": study_date,
            "study_time": study_time,
            "institution_name": institution_name,
        }

        with self._patient_lock:
            self._total_c_store += 1
            if patient_id and patient_id != "Unknown":
                self._unique_patients.add(patient_id)
            self._patient_records.appendleft(record)

        return 0x0000

    @staticmethod
    def _stringify(value, default: Optional[str] = None) -> str:
        if value is None:
            return default or ""
        try:
            text = str(value)
        except Exception:  # pragma: no cover - defensive
            return default or ""
        return text if text else (default or "")


def read_pid(pid_file: Path) -> Optional[int]:
    if not pid_file.exists():
        return None
    try:
        pid_text = pid_file.read_text(encoding="utf-8").strip()
        return int(pid_text)
    except (OSError, ValueError):
        return None


def write_pid(pid_file: Path, pid: int) -> None:
    pid_file.write_text(f"{pid}\n", encoding="utf-8")


def remove_pid_file(pid_file: Path) -> None:
    with contextlib.suppress(FileNotFoundError):
        pid_file.unlink()


def is_process_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def daemonize(working_directory: Path) -> None:
    if os.fork() > 0:
        os._exit(0)

    os.setsid()

    if os.fork() > 0:
        os._exit(0)

    working_directory.mkdir(parents=True, exist_ok=True)
    os.chdir(str(working_directory))
    os.umask(0o022)

    sys.stdout.flush()
    sys.stderr.flush()
    with open(os.devnull, "rb", buffering=0) as read_null:
        os.dup2(read_null.fileno(), sys.stdin.fileno())
    with open(os.devnull, "ab", buffering=0) as write_null:
        os.dup2(write_null.fileno(), sys.stdout.fileno())
        os.dup2(write_null.fileno(), sys.stderr.fileno())


def start_daemon(args: argparse.Namespace, config: ServerConfig) -> int:
    existing_pid = read_pid(config.pid_file)
    if existing_pid and is_process_running(existing_pid):
        print(f"DICOM server already running with PID {existing_pid}")
        return 1

    config.ensure_directories()
    print(
        f"Starting DICOM server using config {config.config_path}",
        flush=True,
    )
    daemonize(config.base_dir)

    pid = os.getpid()
    write_pid(config.pid_file, pid)
    atexit.register(remove_pid_file, config.pid_file)

    server = DICOMServer(config)
    try:
        server.run()
    finally:
        remove_pid_file(config.pid_file)
    return 0


def stop_daemon(_args: argparse.Namespace, config: ServerConfig) -> int:
    pid = read_pid(config.pid_file)
    if not pid:
        print("DICOM server is not running")
        remove_pid_file(config.pid_file)
        return 1

    if not is_process_running(pid):
        print("Found stale PID file; removing")
        remove_pid_file(config.pid_file)
        return 1

    print(f"Stopping DICOM server (PID {pid})")
    try:
        os.kill(pid, signal.SIGTERM)
    except PermissionError as exc:
        print(f"Unable to signal process {pid}: {exc}. Try stopping manually.")
        return 1
    except OSError as exc:
        print(f"Failed to stop server: {exc}")
        return 1

    timeout = 15
    start = time.time()
    while time.time() - start < timeout:
        if not is_process_running(pid):
            remove_pid_file(config.pid_file)
            print("DICOM server stopped")
            return 0
        time.sleep(0.5)

    print("Timed out waiting for server to stop")
    return 1


def restart_daemon(args: argparse.Namespace, config: ServerConfig) -> int:
    stop_exit = stop_daemon(args, config)
    if stop_exit not in {0, 1}:  # treat non-standard failures as fatal
        return stop_exit
    time.sleep(1)
    return start_daemon(args, config)


def status_daemon(_args: argparse.Namespace, config: ServerConfig) -> int:
    pid = read_pid(config.pid_file)
    running = pid is not None and is_process_running(pid)
    if running:
        print(f"DICOM server is running (PID {pid})")
        print(f"Config file: {config.config_path}")
        print(
            f"Status API: http://{config.api_host}:{config.api_port} (log file {config.log_file})"
        )
        print(
            f"DICOM AE '{config.ae_title}' listening on {config.dicom_host}:{config.dicom_port}"
        )
        return 0

    print("DICOM server is not running")
    if pid and not running:
        print("Removing stale PID file")
        remove_pid_file(config.pid_file)
    return 1


def run_foreground(_args: argparse.Namespace, config: ServerConfig) -> int:
    config.ensure_directories()
    server = DICOMServer(config)
    try:
        server.run(console=True)
    except KeyboardInterrupt:
        server.stop()
    return 0


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage the DICOM server daemon")
    parser.add_argument(
        "command",
        choices=["start", "stop", "restart", "status", "foreground"],
        help="Action to perform",
    )
    parser.add_argument(
        "--config",
        dest="config_path",
        default=None,
        help="Path to configuration file (default: autodetect)",
    )
    parser.add_argument("--host", dest="dicom_host", help="Override DICOM listener host")
    parser.add_argument(
        "--port", dest="dicom_port", type=int, help="Override DICOM listener port"
    )
    parser.add_argument(
        "--api-host",
        dest="api_host",
        help="Override API host interface",
    )
    parser.add_argument(
        "--api-port", dest="api_port", type=int, help="Override API port"
    )
    parser.add_argument(
        "--heartbeat",
        dest="heartbeat_interval",
        type=int,
        help="Override heartbeat interval in seconds",
    )
    parser.add_argument(
        "--log-file",
        dest="log_file",
        help="Override log file path (relative paths resolved against base dir)",
    )
    parser.add_argument(
        "--pid-file",
        dest="pid_file",
        help="Override PID file path (relative paths resolved against base dir)",
    )
    parser.add_argument(
        "--log-max-bytes",
        dest="log_max_bytes",
        type=int,
        help="Override max log file size before rotation",
    )
    parser.add_argument(
        "--log-backup-count",
        dest="log_backup_count",
        type=int,
        help="Override number of rotated log files to keep",
    )
    parser.add_argument(
        "--log-tail-lines",
        dest="log_tail_lines",
        type=int,
        help="Override default lines returned by /logs",
    )
    parser.add_argument(
        "--ae-title",
        dest="ae_title",
        help=f"Override DICOM AE title (default: {DEFAULT_AE_TITLE})",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    config = load_config(args.config_path)
    config.apply_cli_overrides(args)

    command_map = {
        "start": start_daemon,
        "stop": stop_daemon,
        "restart": restart_daemon,
        "status": status_daemon,
        "foreground": run_foreground,
    }

    handler = command_map[args.command]
    return handler(args, config)


if __name__ == "__main__":
    sys.exit(main())
