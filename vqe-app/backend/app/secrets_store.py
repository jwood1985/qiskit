"""Fernet-encrypted on-disk key/value store for provider credentials.

We persist a JSON document to ``~/.vqe-app/secrets.enc`` using
:class:`cryptography.fernet.Fernet`. The encryption key lives in
``~/.vqe-app/secret.key`` with ``0600`` permissions, generated on first
use. Setting ``VQE_APP_SECRET`` in the environment lets the operator pin
the key (e.g. for shared / containerised deployments) instead of relying
on the auto-generated file.
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import threading
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from .config import get_config

logger = logging.getLogger(__name__)


class SecretsStore:
    """Thread-safe Fernet-backed key/value store."""

    def __init__(self, data_dir: Path, master_secret: str | None = None) -> None:
        self._lock = threading.Lock()
        self._cipher_path = data_dir / "secrets.enc"
        self._key_path = data_dir / "secret.key"
        self._fernet = Fernet(self._load_or_create_key(master_secret))

    def _load_or_create_key(self, master_secret: str | None) -> bytes:
        if master_secret:
            # Derive a stable Fernet key from the supplied secret.
            digest = hashlib.sha256(master_secret.encode("utf-8")).digest()
            return base64.urlsafe_b64encode(digest)
        if self._key_path.exists():
            return self._key_path.read_bytes()
        key = Fernet.generate_key()
        self._key_path.write_bytes(key)
        os.chmod(self._key_path, 0o600)
        return key

    def _read(self) -> dict[str, Any]:
        if not self._cipher_path.exists():
            return {}
        try:
            data = self._fernet.decrypt(self._cipher_path.read_bytes())
        except InvalidToken:
            logger.error(
                "Could not decrypt secrets store at %s — key mismatch.",
                self._cipher_path,
            )
            raise
        return json.loads(data.decode("utf-8"))

    def _write(self, payload: dict[str, Any]) -> None:
        blob = self._fernet.encrypt(json.dumps(payload).encode("utf-8"))
        # Write atomically so a crash mid-write doesn't corrupt the store.
        tmp = self._cipher_path.with_suffix(".enc.tmp")
        tmp.write_bytes(blob)
        os.chmod(tmp, 0o600)
        os.replace(tmp, self._cipher_path)

    def get_all(self) -> dict[str, Any]:
        with self._lock:
            return self._read()

    def get(self, key: str) -> dict[str, Any] | None:
        return self.get_all().get(key)

    def set(self, key: str, value: dict[str, Any]) -> None:
        with self._lock:
            payload = self._read()
            payload[key] = value
            self._write(payload)

    def delete(self, key: str) -> None:
        with self._lock:
            payload = self._read()
            payload.pop(key, None)
            self._write(payload)


_store: SecretsStore | None = None


def get_store() -> SecretsStore:
    global _store
    if _store is None:
        cfg = get_config()
        _store = SecretsStore(cfg.data_dir, cfg.secret)
    return _store


def reset_store_for_tests(store: SecretsStore) -> None:
    """Replace the module-level singleton — tests only."""
    global _store
    _store = store


def redact(token: str | None) -> str | None:
    """Return a UI-safe fingerprint of a token (last four chars)."""
    if not token:
        return None
    if len(token) <= 4:
        return "••••"
    return f"••••{token[-4:]}"
