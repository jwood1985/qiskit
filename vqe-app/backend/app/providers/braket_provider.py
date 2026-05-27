"""AWS Braket provider via qiskit-braket-provider."""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Iterator

from .base import Provider, ProviderField
from .registry import register

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


class BraketProvider:
    slug = "braket"
    display_name = "AWS Braket"
    settings_schema: list[ProviderField] = [
        ProviderField(
            name="access_key_id",
            label="Access key ID",
            secret=False,
            required=True,
            help="AWS access key with Braket permissions.",
        ),
        ProviderField(
            name="token",
            label="Secret access key",
            secret=True,
            required=True,
        ),
        ProviderField(
            name="region",
            label="Region",
            secret=False,
            required=False,
            default="us-east-1",
        ),
        ProviderField(
            name="device",
            label="Device",
            secret=False,
            required=False,
            default="SV1",
            help="On-demand simulator (SV1) or a QPU ARN.",
        ),
    ]

    def probe(self, secret: dict[str, Any]) -> tuple[bool, str]:
        try:
            from qiskit_braket_provider import BraketProvider as _BraketProvider

            with _aws_env(secret):
                backends = _BraketProvider().backends()
        except Exception as exc:  # pragma: no cover — network/auth failure
            logger.exception("Braket probe failed")
            return False, f"Probe failed: {exc}"
        if not backends:
            return False, "Authenticated but no Braket devices visible."
        return True, "Backends available: " + ", ".join(b.name for b in backends[:3])

    def make_estimator(self, secret: dict[str, Any]) -> Any:
        from qiskit.primitives import BackendEstimator
        from qiskit_braket_provider import BraketProvider as _BraketProvider

        device_name = (secret.get("extra") or {}).get("device", "SV1")
        with _aws_env(secret):
            backend = _BraketProvider().get_backend(device_name)
        return BackendEstimator(backend=backend)

    def inspect_backend(self, estimator: Any) -> dict[str, Any]:
        """See GAPS.md §1.2 — the qiskit-braket shim hides the underlying
        Braket QuantumTask metadata, so we report only what we can."""
        try:
            backend = estimator._backend  # type: ignore[attr-defined]
        except Exception:
            return {"provider": self.slug, "backend": "unknown"}
        return {
            "provider": self.slug,
            "backend": getattr(backend, "name", "unknown"),
            "calibration_snapshot": "device.properties (point-in-time)",
        }


register(BraketProvider())
