"""Ansatz construction.

Two flavours:

* **UCCSD** — Unitary Coupled-Cluster with Singles and Doubles, prepared
  on top of a Hartree–Fock initial state. Chemistry-standard, deeper but
  systematically improvable.
* **EfficientSU2** — Hardware-efficient ansatz suited to noisy backends.
  No chemical structure baked in; relies on the optimizer to find a good
  parameterisation.
"""
from __future__ import annotations

from typing import Any

from ..models import AnsatzName
from .hamiltonian import ChemistryProblem


def build_ansatz(problem: ChemistryProblem, kind: AnsatzName) -> Any:
    from qiskit.circuit.library import EfficientSU2
    from qiskit_nature.second_q.circuit.library import HartreeFock, UCCSD
    from qiskit_nature.second_q.mappers import JordanWignerMapper

    mapper = JordanWignerMapper()

    if kind is AnsatzName.UCCSD:
        initial_state = HartreeFock(
            problem.num_spatial_orbitals,
            problem.num_particles,
            mapper,
        )
        return UCCSD(
            problem.num_spatial_orbitals,
            problem.num_particles,
            mapper,
            initial_state=initial_state,
        )

    # Hardware-efficient: 2 repetitions is a reasonable shallow default
    # for the qubit counts we see here (4–10 qubits).
    num_qubits = problem.qubit_op.num_qubits
    return EfficientSU2(num_qubits, reps=2, entanglement="linear")
