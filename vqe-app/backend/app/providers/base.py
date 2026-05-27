"""Provider dispatch.

Every supported provider exposes two callables:

* ``check(secret)`` — returns ``(ready, detail)`` after a cheap probe of
  the user's credentials.
* ``estimator_factory(secret)`` — returns a function that, given an
  ansatz, builds a Qiskit Estimator primitive bound to that provider.

Real credentials are required; both implementations raise
:class:`ProviderConfigError` if the relevant secret is missing.
"""
from __future__ import annotations

from typing import Any, Callable

from ..models import ProviderName
from ..secrets_store import get_store
from . import braket_provider, qiskit_provider


class ProviderConfigError(RuntimeError):
    """Raised when a provider is not configured for use."""


def _secret(name: str) -> dict[str, Any]:
    record = get_store().get(name) or {}
    if not record.get("token"):
        raise ProviderConfigError(
            f"Provider {name!r} is not configured. Add a token in Settings."
        )
    return record


def check_provider(name: ProviderName) -> tuple[bool, bool, str]:
    """Return ``(configured, ready, detail)`` for the named provider."""
    try:
        secret = _secret(name.value)
    except ProviderConfigError as exc:
        return False, False, str(exc)

    if name is ProviderName.QISKIT:
        ready, detail = qiskit_provider.probe(secret)
    elif name is ProviderName.BRAKET:
        ready, detail = braket_provider.probe(secret)
    else:  # pragma: no cover — exhaustive enum
        raise ValueError(name)

    return True, ready, detail


def build_estimator_factory(name: ProviderName) -> Callable[[Any], Any]:
    secret = _secret(name.value)
    if name is ProviderName.QISKIT:
        return qiskit_provider.estimator_factory(secret)
    if name is ProviderName.BRAKET:
        return braket_provider.estimator_factory(secret)
    raise ValueError(name)  # pragma: no cover
