"""
logger.py
Utilitário de logging centralizado para todas as automações.
Cada run é registrado em logs/<automation_name>.jsonl
"""

import json
import os
from datetime import datetime, timezone
from typing import Any

LOGS_DIR = "/tmp/logs" if os.environ.get("VERCEL") else "logs"

class AutomationLogger:
    def __init__(self, name: str):
        self.name = name
        self.run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.log_file = os.path.join(LOGS_DIR, f"{name}.jsonl")
        self.events: list[dict] = []
        self.start_time = datetime.now(timezone.utc)
        os.makedirs(LOGS_DIR, exist_ok=True)

    def info(self, message: str, data: dict | None = None):
        self._log("INFO", message, data)

    def warning(self, message: str, data: dict | None = None):
        self._log("WARNING", message, data)

    def error(self, message: str, data: dict | None = None):
        self._log("ERROR", message, data)

    def _log(self, level: str, message: str, data: dict | None = None):
        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "msg": message,
        }
        if data:
            event["data"] = data
        self.events.append(event)
        print(f"  [{level}] {message}")

    def finish(self, status: str = "success", summary: dict | None = None):
        """Finaliza o run e persiste no arquivo de log."""
        duration_s = round((datetime.now(timezone.utc) - self.start_time).total_seconds(), 1)
        record = {
            "run_id": self.run_id,
            "automation": self.name,
            "started_at": self.start_time.isoformat(),
            "duration_s": duration_s,
            "status": status,
            "summary": summary or {},
            "events": self.events,
        }
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"\n  Log salvo: {self.log_file} (run {self.run_id}, {duration_s}s, {status})")
