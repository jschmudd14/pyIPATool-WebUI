"""Lightweight keychain-compatible storage for account credentials."""
from __future__ import annotations

import base64
import json
import threading
from pathlib import Path
from typing import Dict


class FileKeychain:
    """Stores opaque blobs keyed by string identifiers on disk."""

    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._lock = threading.RLock()
        self._data: Dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = self._path.read_text(encoding="utf-8")
        except Exception:
            return
        if not raw.strip():
            return
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return
        if isinstance(payload, dict):
            self._data = {str(k): str(v) for k, v in payload.items()}

    def _persist(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self._data, indent=2, sort_keys=True)
        self._path.write_text(payload, encoding="utf-8")

    def get(self, key: str) -> bytes:
        with self._lock:
            encoded = self._data.get(key)
            if encoded is None:
                raise KeyError(key)
            return base64.b64decode(encoded.encode("ascii"))

    def set(self, key: str, data: bytes) -> None:
        with self._lock:
            self._data[key] = base64.b64encode(data).decode("ascii")
            self._persist()

    def remove(self, key: str) -> None:
        with self._lock:
            if key in self._data:
                del self._data[key]
                self._persist()
