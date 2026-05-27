"""AWS Braket adapter.

We use ``qiskit-braket-provider`` so the same Qiskit Estimator-based VQE
pipeline drives Braket QPUs / on-demand simulators. AWS authentication
follows the standard boto3 chain: the secret token is exposed as the
``AWS_ACCESS_KEY_ID`` / ``AWS_SECRET_ACCESS_KEY`` env vars when the
estimator is built, with optional session token / region in ``extra``.
"""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Callable, Iterator

logger = logging.getLogger(__name__)


@contextmanager
def _aws_env(secret: dict[str, Any]) -> Iterator[None]:
    extra = secret.get("extra") or {}
    overrides = {
        "AWS_ACCESS_KEY_ID": extra.get("access_key_id", ""),
        "AWS_SECRET_ACCESS_KEY": secret["token"],
        "AWS_SESSION_TOKEN": extra.get("session_token", ""),
        "AWS_DEFAULT_REGION": extra.get("region", "us-east-1"),
    }
    saved = {k: os.environ.get(k) for k in overrides}
    try:
        for k, v in overrides.items():
            if v:
                os.environ[k] = v
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def probe(secret: dict[str, Any]) -> tuple[bool, str]:
    try:
        from qiskit_braket_provider import BraketProvider

        with _aws_env(secret):
            provider = BraketProvider()
            backends = provider.backends()
        if not backends:
            return False, "Authenticated but no Braket devices visible."
        names = ", ".join(b.name for b in backends[:3])
        return True, f"Backends available: {names}"
    except Exception as exc:  # pragma: no cover — network/auth failure
        logger.exception("Braket probe failed")
        return False, f"Probe failed: {exc}"


def estimator_factory(secret: dict[str, Any]) -> Callable[[Any], Any]:
    from qiskit.primitives import BackendEstimator
    from qiskit_braket_provider import BraketProvider

    extra = secret.get("extra") or {}
    device_name = extra.get("device", "SV1")  # On-demand state vector sim.

    def make_estimator(_ansatz: Any) -> Any:
        with _aws_env(secret):
            provider = BraketProvider()
            backend = provider.get_backend(device_name)
        return BackendEstimator(backend=backend)

    return make_estimator
