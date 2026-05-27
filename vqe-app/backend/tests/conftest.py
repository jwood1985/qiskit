"""Pytest fixtures.

The backend depends on heavy quantum libraries (qiskit, qiskit-nature,
amazon-braket-sdk) that we do NOT exercise in these unit tests — the
tests cover the FastAPI surface and stub out anything that would require
real provider credentials or a quantum simulator. Module imports are
deferred via fixtures so collection works on minimal environments.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest


def _install_qiskit_stubs() -> None:
    """Provide tiny stubs for the optional quantum packages so importing
    ``app.providers`` and ``app.vqe`` succeeds without the real wheels.
    The endpoints we test never invoke the real entrypoints.
    """
    fake_modules = [
        "qiskit",
        "qiskit.primitives",
        "qiskit.circuit",
        "qiskit.circuit.library",
        "qiskit_nature",
        "qiskit_nature.second_q",
        "qiskit_nature.second_q.drivers",
        "qiskit_nature.second_q.mappers",
        "qiskit_nature.second_q.transformers",
        "qiskit_nature.second_q.circuit",
        "qiskit_nature.second_q.circuit.library",
        "qiskit_ibm_runtime",
        "qiskit_braket_provider",
        "pyscf",
    ]
    for name in fake_modules:
        if name not in sys.modules:
            sys.modules[name] = types.ModuleType(name)

    # Minimal callables the modules reference at import time.
    sys.modules["qiskit.circuit.library"].EfficientSU2 = lambda *a, **k: None
    sys.modules["qiskit.primitives"].BackendEstimator = lambda *a, **k: None
    sys.modules["qiskit_nature.second_q.drivers"].PySCFDriver = lambda *a, **k: None
    sys.modules["qiskit_nature.second_q.mappers"].JordanWignerMapper = lambda *a, **k: None
    sys.modules["qiskit_nature.second_q.transformers"].FreezeCoreTransformer = lambda *a, **k: None
    sys.modules["qiskit_nature.second_q.circuit.library"].HartreeFock = lambda *a, **k: None
    sys.modules["qiskit_nature.second_q.circuit.library"].UCCSD = lambda *a, **k: None
    sys.modules["qiskit_ibm_runtime"].QiskitRuntimeService = lambda *a, **k: None
    sys.modules["qiskit_ibm_runtime"].EstimatorV2 = lambda *a, **k: None
    sys.modules["qiskit_ibm_runtime"].Session = lambda *a, **k: None

    class _BraketProvider:  # pragma: no cover — never actually instantiated
        def backends(self) -> list:
            return []

        def get_backend(self, _name: str) -> None:
            return None

    sys.modules["qiskit_braket_provider"].BraketProvider = _BraketProvider


_install_qiskit_stubs()


@pytest.fixture(autouse=True)
def isolated_secrets_store(tmp_path, monkeypatch):
    """Point the secrets store at a temp dir per test."""
    monkeypatch.setenv("VQE_APP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("VQE_APP_SECRET", "unit-test-secret")

    # Reset module-level singletons.
    from app import config as config_mod
    from app import secrets_store as store_mod
    from app import telemetry as telemetry_mod

    config_mod._config = None
    store_mod._store = None
    telemetry_mod._initialised = True  # skip exporter setup in tests

    yield

    config_mod._config = None
    store_mod._store = None


@pytest.fixture()
def client():
    """FastAPI test client. Imported lazily so the stub fixtures apply
    before app modules are imported."""
    from fastapi.testclient import TestClient

    from app.main import create_app

    return TestClient(create_app())


# Make ``backend/`` importable as ``app``.
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_ROOT))
