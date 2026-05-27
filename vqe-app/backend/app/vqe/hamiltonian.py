"""Electronic-structure Hamiltonian construction.

For each supported molecule we run a closed-shell Hartree–Fock with PySCF
in the STO-3G basis, freeze chemically inert core orbitals where useful,
and Jordan–Wigner map the resulting second-quantised operator. This keeps
qubit counts small enough for VQE on near-term hardware while remaining a
chemically meaningful benchmark.

LiH: 4 electrons, 6 spatial orbitals. We freeze the Li 1s core, leaving
an active space of (2 electrons, 5 orbitals) → 10 qubits before tapering.

H2: 2 electrons, 2 spatial orbitals — used as-is → 4 qubits.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..models import Molecule

# Equilibrium geometries (Å). LiH bond length is the standard 1.5957;
# H2 uses 0.735.
_GEOMETRY = {
    Molecule.LIH: "Li 0.0 0.0 0.0; H 0.0 0.0 1.5957",
    Molecule.H2: "H 0.0 0.0 0.0; H 0.0 0.0 0.735",
}


@dataclass
class ChemistryProblem:
    """Bundle of objects needed downstream by the ansatz + runner."""

    qubit_op: Any  # SparsePauliOp
    num_particles: tuple[int, int]
    num_spatial_orbitals: int
    nuclear_repulsion: float
    hf_energy: float
    problem: Any  # qiskit_nature ElectronicStructureProblem


def build_problem(molecule: Molecule) -> ChemistryProblem:
    """Build a Jordan–Wigner mapped qubit Hamiltonian for ``molecule``.

    Imports are deferred so that test environments without PySCF /
    qiskit-nature can still import the package.
    """
    from qiskit_nature.second_q.drivers import PySCFDriver
    from qiskit_nature.second_q.mappers import JordanWignerMapper
    from qiskit_nature.second_q.transformers import FreezeCoreTransformer

    driver = PySCFDriver(atom=_GEOMETRY[molecule], basis="sto3g")
    problem = driver.run()

    if molecule is Molecule.LIH:
        # Freezing the Li 1s core is standard practice for LiH VQE
        # benchmarks: it removes the deepest-energy orbital that
        # contributes negligibly to the chemistry of bond formation.
        problem = FreezeCoreTransformer(freeze_core=True).transform(problem)

    mapper = JordanWignerMapper()
    second_q_op = problem.hamiltonian.second_q_op()
    qubit_op = mapper.map(second_q_op)

    return ChemistryProblem(
        qubit_op=qubit_op,
        num_particles=problem.num_particles,
        num_spatial_orbitals=problem.num_spatial_orbitals,
        nuclear_repulsion=problem.nuclear_repulsion_energy,
        hf_energy=problem.reference_energy,
        problem=problem,
    )
