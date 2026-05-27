"""VQE driver.

Each classical-optimizer iteration submits one parametrised circuit
evaluation to the quantum provider, polls the job lifecycle to
completion, and reports the expectation value back to SciPy COBYLA.

OpenTelemetry span hierarchy::

    vqe.run                 (one per /api/vqe/run call)
    └── vqe.iteration       (one per minimize() step)
        └── quantum.job     (one per circuit evaluation)

The ``quantum.job`` span carries normalised attributes describing the
job: provider job id, backend name, queue/execution time, shot count,
error-mitigation method, calibration snapshot. Trace context flows
automatically through nested ``start_as_current_span`` blocks. The
classical→quantum boundary itself is not propagated into the provider's
server-side telemetry — see GAPS.md §2.1.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
from scipy.optimize import minimize

from ..models import AnsatzName, JobSnapshotPayload, Molecule, VQEIteration
from ..providers.base import JobSnapshot, Provider
from ..telemetry import get_meter, get_tracer
from .ansatz import build_ansatz
from .hamiltonian import build_problem

logger = logging.getLogger(__name__)


@dataclass
class VQEResult:
    iterations: list[VQEIteration]
    final_energy: float
    nuclear_repulsion: float
    hf_energy: float


def _snapshot_to_payload(snap: JobSnapshot) -> JobSnapshotPayload:
    return JobSnapshotPayload(
        state=snap.state,
        raw_state=snap.raw_state,
        queue_time_s=snap.queue_time_s,
        execution_time_s=snap.execution_time_s,
        shots=snap.shots,
        backend=snap.backend,
        error_mitigation=snap.error_mitigation,
        calibration=snap.calibration,
    )


def run_vqe(
    *,
    molecule: Molecule,
    provider_slug: str,
    provider: Provider,
    ansatz_kind: AnsatzName,
    max_iter: int,
    estimator_factory: Callable[[Any], Any],
    on_iteration: Callable[[VQEIteration], None] | None = None,
    on_job_event: Callable[[JobSnapshotPayload], None] | None = None,
    use_real_hardware: bool = False,
    poll_interval_s: float = 0.5,
) -> VQEResult:
    tracer = get_tracer()
    meter = get_meter()
    iter_counter = meter.create_counter(
        "vqe.optimizer.iterations",
        description="Number of classical optimizer iterations executed.",
    )
    energy_gauge = meter.create_gauge(
        "vqe.optimizer.current_energy",
        description="Most recent VQE energy estimate (Hartree).",
    )
    job_queue_hist = meter.create_histogram(
        "vqe.quantum.queue_time_s",
        description="Queue time per parametrised circuit evaluation.",
    )
    job_exec_hist = meter.create_histogram(
        "vqe.quantum.execution_time_s",
        description="Execution time per parametrised circuit evaluation.",
    )

    with tracer.start_as_current_span("vqe.run") as run_span:
        run_span.set_attribute("vqe.molecule", molecule.value)
        run_span.set_attribute("vqe.provider", provider_slug)
        run_span.set_attribute("vqe.ansatz", ansatz_kind.value)
        run_span.set_attribute("vqe.max_iter", max_iter)
        run_span.set_attribute("vqe.use_real_hardware", use_real_hardware)

        problem = build_problem(molecule)
        ansatz = build_ansatz(problem, ansatz_kind)

        run_span.set_attribute("vqe.num_qubits", problem.qubit_op.num_qubits)
        run_span.set_attribute("vqe.num_parameters", ansatz.num_parameters)
        run_span.set_attribute("vqe.hf_energy", problem.hf_energy)

        estimator = estimator_factory(ansatz)
        backend_meta = provider.inspect_backend(estimator)
        for k, v in backend_meta.items():
            if v is not None:
                run_span.set_attribute(f"vqe.backend.{k}", str(v))

        iterations: list[VQEIteration] = []

        def _evaluate_circuit(params: np.ndarray) -> float:
            with tracer.start_as_current_span("quantum.job") as job_span:
                # Submit
                job = estimator.run([ansatz], [problem.qubit_op], [params.tolist()])
                try:
                    job_id = job.job_id()
                except Exception:
                    job_id = f"local-{id(job):x}"
                job_span.set_attribute("quantum.job.id", job_id)
                for k, v in backend_meta.items():
                    if v is not None:
                        job_span.set_attribute(f"quantum.backend.{k}", str(v))

                # Poll lifecycle
                last_state: str | None = None
                snap = provider.snapshot_job(job)
                while True:
                    if snap.state != last_state:
                        job_span.add_event(
                            f"job.{snap.state}",
                            attributes={
                                "raw_state": snap.raw_state or "",
                                "queue_time_s": snap.queue_time_s or 0.0,
                                "execution_time_s": snap.execution_time_s or 0.0,
                            },
                        )
                        if on_job_event:
                            on_job_event(_snapshot_to_payload(snap))
                        last_state = snap.state
                    if snap.state in ("completed", "failed"):
                        break
                    time.sleep(poll_interval_s)
                    snap = provider.snapshot_job(job)

                # Final span attrs from terminal snapshot.
                if snap.queue_time_s is not None:
                    job_span.set_attribute("quantum.job.queue_time_s", snap.queue_time_s)
                    job_queue_hist.record(snap.queue_time_s)
                if snap.execution_time_s is not None:
                    job_span.set_attribute(
                        "quantum.job.execution_time_s", snap.execution_time_s
                    )
                    job_exec_hist.record(snap.execution_time_s)
                if snap.shots is not None:
                    job_span.set_attribute("quantum.job.shots", snap.shots)
                if snap.error_mitigation:
                    for k, v in snap.error_mitigation.items():
                        job_span.set_attribute(f"quantum.mitigation.{k}", str(v))

                if snap.state == "failed":
                    raise RuntimeError(
                        f"Quantum job {job_id} failed "
                        f"(provider state {snap.raw_state!r})"
                    )

            return float(job.result().values[0])

        def objective(params: np.ndarray) -> float:
            idx = len(iterations) + 1
            attrs = {
                "molecule": molecule.value,
                "provider": provider_slug,
                "ansatz": ansatz_kind.value,
            }
            with tracer.start_as_current_span("vqe.iteration") as it_span:
                it_span.set_attribute("vqe.iteration.idx", idx)
                t0 = time.perf_counter()
                value = _evaluate_circuit(params)
                elapsed = time.perf_counter() - t0
                it_span.set_attribute("vqe.iteration.energy", value)
                it_span.set_attribute("vqe.iteration.elapsed_s", elapsed)

            iteration = VQEIteration(iteration=idx, energy=value)
            iterations.append(iteration)
            iter_counter.add(1, attrs)
            energy_gauge.set(value, attrs)
            if on_iteration:
                on_iteration(iteration)
            return value

        x0 = np.zeros(ansatz.num_parameters)
        result = minimize(
            objective,
            x0,
            method="COBYLA",
            options={"maxiter": max_iter, "rhobeg": 0.1},
        )

        final = float(result.fun)
        run_span.set_attribute("vqe.final_energy", final)
        return VQEResult(
            iterations=iterations,
            final_energy=final,
            nuclear_repulsion=problem.nuclear_repulsion,
            hf_energy=problem.hf_energy,
        )
