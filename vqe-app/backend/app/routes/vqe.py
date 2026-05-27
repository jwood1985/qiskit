"""VQE router — start runs, poll status."""
from __future__ import annotations

import logging
import threading
import uuid
from typing import Any, Callable

from fastapi import APIRouter, HTTPException

from ..models import VQEIteration, VQERunRequest, VQERunStatus
from ..providers import UnknownProvider, get as get_provider
from ..secrets_store import get_store
from ..vqe.runner import run_vqe

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/vqe", tags=["vqe"])

_runs: dict[str, VQERunStatus] = {}
_runs_lock = threading.Lock()


def _set(run_id: str, **fields: Any) -> None:
    with _runs_lock:
        current = _runs[run_id]
        _runs[run_id] = current.model_copy(update=fields)


def _runner_factory() -> Callable:
    """Indirection so tests can monkeypatch the runner without importing
    qiskit-nature."""
    return run_vqe


def _build_estimator_factory(slug: str, *, use_real_hardware: bool) -> Callable[[Any], Any]:
    """Build a (ansatz) -> Estimator factory for the named provider.

    Credentials are only required when the caller opts into real
    hardware. Simulator runs work out of the box with an empty secrets
    store — that's the development default per CLAUDE.md.
    """
    provider = get_provider(slug)
    secret = get_store().get(slug) or {}
    if use_real_hardware and not secret.get("token"):
        raise RuntimeError(
            f"Real-hardware run requested but provider {slug!r} has no "
            "token configured. Add one in Settings or unset "
            "`use_real_hardware`."
        )

    def factory(_ansatz: Any) -> Any:
        return provider.make_estimator(secret, simulator=not use_real_hardware)

    return factory


def _execute(run_id: str, req: VQERunRequest) -> None:
    try:
        estimator_factory = _build_estimator_factory(
            req.provider, use_real_hardware=req.use_real_hardware
        )
    except (RuntimeError, UnknownProvider) as exc:
        logger.warning("VQE run %s aborted: %s", run_id, exc)
        _set(run_id, state="failed", error=str(exc))
        return

    def on_iteration(it: VQEIteration) -> None:
        with _runs_lock:
            current = _runs[run_id]
            _runs[run_id] = current.model_copy(
                update={"iterations": current.iterations + [it]}
            )

    try:
        _set(run_id, state="running")
        result = _runner_factory()(
            molecule=req.molecule,
            provider=req.provider,
            ansatz_kind=req.ansatz,
            max_iter=req.max_iter,
            estimator_factory=estimator_factory,
            on_iteration=on_iteration,
            use_real_hardware=req.use_real_hardware,
        )
        _set(run_id, state="succeeded", final_energy=result.final_energy)
    except Exception as exc:
        logger.exception("VQE run %s failed", run_id)
        _set(run_id, state="failed", error=str(exc))


@router.post("/run", response_model=VQERunStatus, status_code=202)
def start_run(req: VQERunRequest) -> VQERunStatus:
    try:
        get_provider(req.provider)
    except UnknownProvider:
        raise HTTPException(status_code=400, detail=f"Unknown provider {req.provider!r}")

    run_id = uuid.uuid4().hex
    status = VQERunStatus(
        id=run_id,
        state="pending",
        molecule=req.molecule,
        provider=req.provider,
        ansatz=req.ansatz,
    )
    with _runs_lock:
        _runs[run_id] = status
    thread = threading.Thread(target=_execute, args=(run_id, req), daemon=True)
    thread.start()
    return status


@router.get("/runs/{run_id}", response_model=VQERunStatus)
def get_run(run_id: str) -> VQERunStatus:
    with _runs_lock:
        status = _runs.get(run_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return status
