"""Qiskit IBM Runtime provider."""
from __future__ import annotations

import logging
from typing import Any

from .base import JobSnapshot, JobState, Provider, ProviderField
from .registry import register

logger = logging.getLogger(__name__)


class QiskitProvider:
    slug = "qiskit"
    display_name = "Qiskit IBM Runtime"
    settings_schema: list[ProviderField] = [
        ProviderField(
            name="token",
            label="API token",
            secret=True,
            required=True,
            help="Paste your IBM Quantum / IBM Cloud API token.",
        ),
        ProviderField(
            name="instance",
            label="Instance (hub/group/project)",
            secret=False,
            required=False,
            help="Example: ibm-q/open/main",
        ),
        ProviderField(
            name="channel",
            label="Channel",
            secret=False,
            required=False,
            default="ibm_quantum",
        ),
    ]

    def _service(self, secret: dict[str, Any]) -> Any:
        from qiskit_ibm_runtime import QiskitRuntimeService

        extra = secret.get("extra") or {}
        kwargs: dict[str, Any] = {
            "channel": extra.get("channel", "ibm_quantum"),
            "token": secret["token"],
        }
        if extra.get("instance"):
            kwargs["instance"] = extra["instance"]
        return QiskitRuntimeService(**kwargs)

    def probe(self, secret: dict[str, Any]) -> tuple[bool, str]:
        try:
            backends = self._service(secret).backends(simulator=False, operational=True)
        except Exception as exc:  # pragma: no cover — network/auth failure
            logger.exception("Qiskit Runtime probe failed")
            return False, f"Probe failed: {exc}"
        if not backends:
            return False, "Authenticated but no operational backends visible."
        return True, "Backends available: " + ", ".join(b.name for b in backends[:3])

    def make_estimator(self, secret: dict[str, Any], *, simulator: bool) -> Any:
        if simulator:
            # Local AerSimulator wrapped in BackendEstimator. No
            # credentials needed; this is the dev/test default.
            from qiskit.primitives import BackendEstimator
            from qiskit_aer import AerSimulator

            return BackendEstimator(backend=AerSimulator())

        from qiskit_ibm_runtime import EstimatorV2, Session

        service = self._service(secret)
        backend = service.least_busy(simulator=False, operational=True)
        session = Session(service=service, backend=backend)
        return EstimatorV2(session=session)

    def inspect_backend(self, estimator: Any) -> dict[str, Any]:
        """See GAPS.md §1.3 — this is a point-in-time snapshot, not a
        per-job calibration."""
        try:
            backend = estimator.session.backend()  # type: ignore[attr-defined]
        except Exception:
            return {"provider": self.slug, "backend": "unknown"}
        return {
            "provider": self.slug,
            "backend": getattr(backend, "name", "unknown"),
            "num_qubits": getattr(backend, "num_qubits", None),
            "calibration_snapshot": "backend.target (point-in-time)",
        }

    # Native QiskitJobStatus → canonical state. See GAPS.md §4.1.
    _STATE_MAP: dict[str, JobState] = {
        "INITIALIZING": "submitted",
        "QUEUED": "queued",
        "VALIDATING": "queued",
        "RUNNING": "running",
        "DONE": "completed",
        "COMPLETED": "completed",
        "ERROR": "failed",
        "CANCELLED": "failed",
        "FAILED": "failed",
    }

    def snapshot_job(self, job: Any) -> JobSnapshot:
        raw = "UNKNOWN"
        try:
            status = job.status()
            raw = status.name if hasattr(status, "name") else str(status)
        except Exception:  # pragma: no cover — defensive
            pass
        state = self._STATE_MAP.get(raw, "running")

        queue_time = exec_time = None
        try:
            metrics = job.metrics() or {}
            ts = metrics.get("timestamps", {}) or {}
            if ts.get("running") and ts.get("created"):
                queue_time = float(ts["running"]) - float(ts["created"])
            if ts.get("finished") and ts.get("running"):
                exec_time = float(ts["finished"]) - float(ts["running"])
        except Exception:  # pragma: no cover — metrics not always available
            pass

        # Backend name from the job object when available.
        backend = None
        try:
            backend = job.backend().name  # type: ignore[attr-defined]
        except Exception:
            pass

        return JobSnapshot(
            state=state,
            raw_state=raw,
            queue_time_s=queue_time,
            execution_time_s=exec_time,
            backend=backend,
        )


register(QiskitProvider())
