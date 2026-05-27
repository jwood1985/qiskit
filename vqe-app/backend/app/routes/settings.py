"""Settings router — persists provider credentials, redacts on read."""
from __future__ import annotations

import logging

from fastapi import APIRouter

from ..models import ProviderSecret, ProviderView, SettingsPayload, SettingsView
from ..secrets_store import get_store, redact

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/settings", tags=["settings"])

_PROVIDERS = ("qiskit", "braket", "dynatrace")


def _view(record: dict | None) -> ProviderView:
    if not record:
        return ProviderView(configured=False)
    return ProviderView(
        configured=bool(record.get("token")),
        token_fingerprint=redact(record.get("token")),
        extra=record.get("extra"),
    )


@router.get("", response_model=SettingsView)
def read_settings() -> SettingsView:
    store = get_store()
    data = store.get_all()
    return SettingsView(
        qiskit=_view(data.get("qiskit")),
        braket=_view(data.get("braket")),
        dynatrace=_view(data.get("dynatrace")),
    )


@router.put("", response_model=SettingsView)
def update_settings(payload: SettingsPayload) -> SettingsView:
    store = get_store()
    incoming = {
        "qiskit": payload.qiskit,
        "braket": payload.braket,
        "dynatrace": payload.dynatrace,
    }
    for name, value in incoming.items():
        if value is None:
            continue
        record: dict = {}
        if value.token is not None:
            record["token"] = value.token
        if value.extra is not None:
            record["extra"] = value.extra
        if record:
            # Merge with existing so the user can update a field at a time.
            existing = store.get(name) or {}
            existing.update(record)
            store.set(name, existing)
            logger.info("Updated settings for provider %s", name)
    return read_settings()
