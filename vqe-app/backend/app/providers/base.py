"""Quantum-provider interface.

Strict boundary: adding a new provider (Azure, IonQ, …) requires only
implementing the :class:`Provider` protocol and registering the
implementation. No other module in this codebase references provider
names directly — they look them up by slug through
:mod:`app.providers.registry`.

The protocol is deliberately small. Each provider:

* declares its identity (``slug``, ``display_name``);
* declares the form fields needed to configure it (``settings_schema``)
  so the UI can render the right form without provider-specific code;
* probes its credentials cheaply (``probe``);
* builds a Qiskit-style ``Estimator`` primitive bound to its backend
  (``make_estimator``);
* exposes backend metadata for telemetry (``inspect_backend``).

Phases C and D extend ``make_estimator`` with a ``simulator`` keyword
and introduce a job-handle abstraction respectively.
"""
from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel


class ProviderField(BaseModel):
    """A single configuration field a provider needs."""

    name: str
    label: str
    secret: bool = False
    required: bool = False
    default: str | None = None
    help: str | None = None


@runtime_checkable
class Provider(Protocol):
    slug: str
    display_name: str
    settings_schema: list[ProviderField]

    def probe(self, secret: dict[str, Any]) -> tuple[bool, str]:
        """Return ``(ready, detail)`` after a cheap probe of credentials."""

    def make_estimator(self, secret: dict[str, Any], *, simulator: bool) -> Any:
        """Build a Qiskit Estimator primitive bound to this provider.

        ``simulator=True`` is the development default and must work
        without credentials (Aer / Braket LocalSimulator). ``False``
        opts into real hardware and may require valid tokens in
        ``secret``.
        """

    def inspect_backend(self, estimator: Any) -> dict[str, Any]:
        """Return a JSON-serialisable snapshot of backend metadata
        (calibration, supported error-mitigation options, etc.) for
        attachment to OpenTelemetry spans."""
