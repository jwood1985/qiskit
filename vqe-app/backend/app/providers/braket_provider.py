"""AWS Braket provider via qiskit-braket-provider."""
from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import Any, Iterator

from .base import JobSnapshot, JobState, Provider, ProviderField
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

    def make_estimator(self, secret: dict[str, Any], *, simulator: bool) -> Any:
        from qiskit.primitives import BackendEstimator

        if simulator:
            # qiskit_braket_provider's BraketLocalBackend wraps
            # braket.devices.LocalSimulator. No AWS creds, no quota.
            from qiskit_braket_provider import BraketLocalBackend

            return BackendEstimator(backend=BraketLocalBackend())

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

    # See GAPS.md §4.1 for the Braket state vocabulary we map from.
    _STATE_MAP: dict[str, JobState] = {
        "INITIALIZING": "submitted",
        "CREATED": "submitted",
        "QUEUED": "queued",
        "RUNNING": "running",
        "COMPLETED": "completed",
        "DONE": "completed",
        "FAILED": "failed",
        "CANCELLED": "failed",
    }

    def snapshot_job(self, job: Any) -> JobSnapshot:
        """Limited by GAPS.md §1.2 — the qiskit-braket shim hides queue
        / execution timings on QuantumTask. We surface state and (when
        we can reach it) the backend name."""
        raw = "UNKNOWN"
        try:
            status = job.status()
            raw = status.name if hasattr(status, "name") else str(status)
        except Exception:  # pragma: no cover
            pass
        state = self._STATE_MAP.get(raw, "running")

        backend = None
        try:
            backend = job.backend().name  # type: ignore[attr-defined]
        except Exception:
            pass

        return JobSnapshot(state=state, raw_state=raw, backend=backend)


register(BraketProvider())
