"""Disk-based JSON cache with TTL. Keys are SHA-256 hashes of raw strings."""

import hashlib
import json
import logging
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class DiskCache:
    def __init__(self, cache_dir: Path, ttl_seconds: int = 86400):
        self._dir = cache_dir
        self._ttl = ttl_seconds
        self._dir.mkdir(parents=True, exist_ok=True)

    def _make_key(self, raw: str) -> str:
        return hashlib.sha256(raw.encode()).hexdigest()

    def _path(self, key: str) -> Path:
        return self._dir / f"{key}.json"

    def get(self, raw_key: str) -> Optional[Any]:
        key = self._make_key(raw_key)
        path = self._path(key)
        if not path.exists():
            return None
        age = time.time() - path.stat().st_mtime
        if age > self._ttl:
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.debug("Cache read failed for key %s: %s", raw_key, exc)
            return None

    def set(self, raw_key: str, value: Any) -> None:
        key = self._make_key(raw_key)
        path = self._path(key)
        try:
            path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        except OSError as exc:
            logger.debug("Cache write failed for key %s: %s", raw_key, exc)

    def invalidate(self, raw_key: str) -> None:
        key = self._make_key(raw_key)
        path = self._path(key)
        if path.exists():
            path.unlink()

    def clear_expired(self) -> int:
        now = time.time()
        count = 0
        for path in self._dir.glob("*.json"):
            if now - path.stat().st_mtime > self._ttl:
                path.unlink()
                count += 1
        return count
