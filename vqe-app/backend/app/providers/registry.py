"""Provider registry.

Each concrete provider registers itself at import time. Lookup is by
slug; iteration returns providers in registration order so the UI list
is stable.
"""
from __future__ import annotations

from typing import Iterable

from .base import Provider


class UnknownProvider(LookupError):
    pass


_providers: dict[str, Provider] = {}


def register(provider: Provider) -> Provider:
    """Register a provider. Idempotent on same-slug re-registration so
    that test suites that re-import modules don't blow up."""
    _providers[provider.slug] = provider
    return provider


def get(slug: str) -> Provider:
    try:
        return _providers[slug]
    except KeyError as exc:
        raise UnknownProvider(slug) from exc


def all_providers() -> Iterable[Provider]:
    return list(_providers.values())


def reset_for_tests() -> None:
    """Clear the registry — test helper only."""
    _providers.clear()
