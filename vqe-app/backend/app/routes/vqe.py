"""VQE router — start runs, poll status."""
from __future__ import annotations

import logging
import threading
import uuid
from typing import Callable

from fastapi import APIRouter, HTTPException

from ..models import VQEIteration, VQERunRequest, VQERunStatus
from ..providers import build_estimator_factory
from ..providers.base import ProviderConfigError
from ..vqe.runner import run_vqe

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/vqe", tags=["vqe"])

# In-memory run registry. A single backend instance is assumed; for a
# multi-replica deployment this would move to Redis or a database.
_runs: dict[str, VQERunStatus] = {}
_runs_lock = threading.Lock()


def _set(run_id: str, **fields) -> None:
    with _runs_lock:
        current = _runs[run_id]
        _runs[run_id] = current.model_copy(update=fields)


def _runner_factory() -> Callable:
    """Indirection so tests can monkeypatch the runner without importing
    qiskit-nature."""
    return run_vqe


def _execute(run_id: str, req: VQERunRequest) -> None:
    try:
        estimator_factory = build_estimator_factory(req.provider)
    except ProviderConfigError as exc:
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
        )
        _set(run_id, state="succeeded", final_energy=result.final_energy)
    except Exception as exc:
        logger.exception("VQE run %s failed", run_id)
        _set(run_id, state="failed", error=str(exc))


@router.post("/run", response_model=VQERunStatus, status_code=202)
def start_run(req: VQERunRequest) -> VQERunStatus:
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
