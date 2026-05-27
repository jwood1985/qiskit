"""Pytest fixtures.

Heavy quantum libraries (qiskit, qiskit-nature, amazon-braket-sdk) are
stubbed at the module level so the FastAPI surface can be tested without
real provider credentials. The provider registry is snapshotted per
test so registration leaks between tests cannot occur.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest


def _install_qiskit_stubs() -> None:
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

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_ROOT))


@pytest.fixture(autouse=True)
def isolated_secrets_store(tmp_path, monkeypatch):
    """Point the secrets store at a temp dir per test."""
    monkeypatch.setenv("VQE_APP_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("VQE_APP_SECRET", "unit-test-secret")

    from app import config as config_mod
    from app import secrets_store as store_mod
    from app import telemetry as telemetry_mod

    config_mod._config = None
    store_mod._store = None
    telemetry_mod._initialised = True  # skip exporter setup in tests

    yield

    config_mod._config = None
    store_mod._store = None


@pytest.fixture(autouse=True)
def snapshot_provider_registry():
    """Restore the provider registry after each test so a test that
    registers a stub provider does not leak it to its neighbours."""
    from app.providers import registry

    snapshot = dict(registry._providers)
    yield
    registry._providers.clear()
    registry._providers.update(snapshot)


@pytest.fixture()
def client():
    from fastapi.testclient import TestClient

    from app.main import create_app

    return TestClient(create_app())
