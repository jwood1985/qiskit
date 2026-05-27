"""VQE driver.

Wraps a Qiskit ``Estimator`` primitive in a SciPy COBYLA loop and emits
OpenTelemetry signals at each classical-optimizer iteration.

The runner is intentionally provider-agnostic: it takes an ``estimator``
instance (constructed by :mod:`app.providers`) so the same code path
serves Qiskit Runtime and qiskit-braket-provider backends.
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
from scipy.optimize import minimize

from ..models import AnsatzName, Molecule, ProviderName, VQEIteration
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


def run_vqe(
    *,
    molecule: Molecule,
    provider: ProviderName,
    ansatz_kind: AnsatzName,
    max_iter: int,
    estimator_factory: Callable[[Any], Any],
    on_iteration: Callable[[VQEIteration], None] | None = None,
) -> VQEResult:
    """Run VQE end-to-end.

    ``estimator_factory`` receives the constructed ansatz circuit and
    returns a Qiskit Estimator primitive bound to the desired backend.
    Splitting it out keeps the chemistry/optimizer code free of provider
    plumbing (and trivially mockable in tests).
    """
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

    with tracer.start_as_current_span("vqe.run") as span:
        span.set_attribute("vqe.molecule", molecule.value)
        span.set_attribute("vqe.provider", provider.value)
        span.set_attribute("vqe.ansatz", ansatz_kind.value)
        span.set_attribute("vqe.max_iter", max_iter)

        problem = build_problem(molecule)
        ansatz = build_ansatz(problem, ansatz_kind)

        span.set_attribute("vqe.num_qubits", problem.qubit_op.num_qubits)
        span.set_attribute("vqe.num_parameters", ansatz.num_parameters)
        span.set_attribute("vqe.hf_energy", problem.hf_energy)

        estimator = estimator_factory(ansatz)

        iterations: list[VQEIteration] = []

        def objective(params: np.ndarray) -> float:
            t0 = time.perf_counter()
            job = estimator.run([ansatz], [problem.qubit_op], [params.tolist()])
            value = float(job.result().values[0])
            elapsed = time.perf_counter() - t0

            idx = len(iterations) + 1
            iteration = VQEIteration(iteration=idx, energy=value)
            iterations.append(iteration)

            attrs = {
                "molecule": molecule.value,
                "provider": provider.value,
                "ansatz": ansatz_kind.value,
            }
            iter_counter.add(1, attrs)
            energy_gauge.set(value, attrs)
            span.add_event(
                "iteration",
                attributes={
                    "iteration": idx,
                    "energy": value,
                    "elapsed_s": elapsed,
                },
            )
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
        span.set_attribute("vqe.final_energy", final)
        return VQEResult(
            iterations=iterations,
            final_energy=final,
            nuclear_repulsion=problem.nuclear_repulsion,
            hf_energy=problem.hf_energy,
        )
