"""Providers router — iterate the registry, no provider-specific code."""
from __future__ import annotations

import logging

from fastapi import APIRouter

from ..models import ProviderStatus
from ..providers import all_providers
from ..secrets_store import get_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/providers", tags=["providers"])


def _status_for(provider) -> ProviderStatus:
    record = get_store().get(provider.slug) or {}
    if not record.get("token"):
        return ProviderStatus(
            slug=provider.slug,
            display_name=provider.display_name,
            configured=False,
            ready=False,
            detail="Provider is not configured. Add a token in Settings.",
            schema_fields=provider.settings_schema,
        )
    try:
        ready, detail = provider.probe(record)
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("Probe raised for %s", provider.slug)
        ready, detail = False, f"Internal error: {exc}"
    return ProviderStatus(
        slug=provider.slug,
        display_name=provider.display_name,
        configured=True,
        ready=ready,
        detail=detail,
        schema_fields=provider.settings_schema,
    )


@router.get("", response_model=list[ProviderStatus])
def list_providers() -> list[ProviderStatus]:
    return [_status_for(p) for p in all_providers()]
