"""Qiskit IBM Runtime adapter.

Uses :class:`qiskit_ibm_runtime.QiskitRuntimeService` to discover the
least-busy backend the user has access to, then constructs a Runtime
:class:`Estimator` against it. Credentials come from the encrypted
secrets store.
"""
from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


def _service(secret: dict[str, Any]) -> Any:
    from qiskit_ibm_runtime import QiskitRuntimeService

    token = secret["token"]
    extra = secret.get("extra") or {}
    instance = extra.get("instance")  # e.g. "ibm-q/open/main"
    channel = extra.get("channel", "ibm_quantum")
    kwargs: dict[str, Any] = {"channel": channel, "token": token}
    if instance:
        kwargs["instance"] = instance
    return QiskitRuntimeService(**kwargs)


def probe(secret: dict[str, Any]) -> tuple[bool, str]:
    try:
        service = _service(secret)
        backends = service.backends(simulator=False, operational=True)
        if not backends:
            return False, "Authenticated but no operational backends visible."
        names = ", ".join(b.name for b in backends[:3])
        return True, f"Backends available: {names}"
    except Exception as exc:  # pragma: no cover — network/auth failure
        logger.exception("Qiskit Runtime probe failed")
        return False, f"Probe failed: {exc}"


def estimator_factory(secret: dict[str, Any]) -> Callable[[Any], Any]:
    from qiskit_ibm_runtime import EstimatorV2, Session

    service = _service(secret)
    backend = service.least_busy(simulator=False, operational=True)

    def make_estimator(_ansatz: Any) -> Any:
        session = Session(service=service, backend=backend)
        return EstimatorV2(session=session)

    return make_estimator
