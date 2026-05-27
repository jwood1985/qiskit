"""Providers router — report configured + connection status per provider."""
from __future__ import annotations

import logging

from fastapi import APIRouter

from ..models import ProviderName, ProviderStatus
from ..providers import check_provider

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/providers", tags=["providers"])


@router.get("", response_model=list[ProviderStatus])
def list_providers() -> list[ProviderStatus]:
    statuses: list[ProviderStatus] = []
    for name in ProviderName:
        try:
            configured, ready, detail = check_provider(name)
        except Exception as exc:  # pragma: no cover — defensive
            logger.exception("Provider check raised for %s", name)
            configured, ready, detail = False, False, f"Internal error: {exc}"
        statuses.append(
            ProviderStatus(
                name=name,
                configured=configured,
                ready=ready,
                detail=detail,
            )
        )
    return statuses
