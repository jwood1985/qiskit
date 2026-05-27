"""Settings router — persists provider credentials, redacts on read.

Iterates the provider registry so a new provider is reflected without
edits here.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter

from ..models import ProviderView, SettingsPayload, SettingsView
from ..providers import all_providers
from ..secrets_store import get_store, redact

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/settings", tags=["settings"])

# Non-provider settings stored alongside providers in the same encrypted
# store. Dynatrace is a telemetry sink, not a quantum provider, so it
# does not live in the provider registry.
_TELEMETRY_KEYS = ("dynatrace",)


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
    data = get_store().get_all()
    providers = {p.slug: _view(data.get(p.slug)) for p in all_providers()}
    return SettingsView(
        providers=providers,
        dynatrace=_view(data.get("dynatrace")),
    )


@router.put("", response_model=SettingsView)
def update_settings(payload: SettingsPayload) -> SettingsView:
    store = get_store()
    known_slugs = {p.slug for p in all_providers()}

    if payload.providers:
        for slug, secret in payload.providers.items():
            if slug not in known_slugs:
                logger.warning("Ignoring unknown provider slug %r", slug)
                continue
            _merge(store, slug, secret)
    if payload.dynatrace is not None:
        _merge(store, "dynatrace", payload.dynatrace)

    return read_settings()


def _merge(store, key: str, secret) -> None:
    record: dict = {}
    if secret.token is not None:
        record["token"] = secret.token
    if secret.extra is not None:
        record["extra"] = secret.extra
    if not record:
        return
    existing = store.get(key) or {}
    existing.update(record)
    store.set(key, existing)
    logger.info("Updated settings for %s", key)
