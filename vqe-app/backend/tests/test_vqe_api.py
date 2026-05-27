"""Coverage for /api/vqe."""
from __future__ import annotations

import time

from app.models import VQEIteration
from app.vqe.runner import VQEResult


def _wait_for(client, run_id: str, target_state: str, timeout: float = 5.0) -> dict:
    deadline = time.time() + timeout
    body: dict = {}
    while time.time() < deadline:
        response = client.get(f"/api/vqe/runs/{run_id}")
        body = response.json()
        if body["state"] == target_state:
            return body
        time.sleep(0.05)
    raise AssertionError(f"run {run_id} never reached state {target_state}: {body}")


def test_run_requires_provider_credentials(client):
    response = client.post(
        "/api/vqe/run",
        json={"molecule": "LiH", "provider": "qiskit", "ansatz": "UCCSD"},
    )
    assert response.status_code == 202
    body = response.json()
    final = _wait_for(client, body["id"], "failed")
    assert "not configured" in final["error"].lower()


def test_run_rejects_unknown_provider(client):
    response = client.post(
        "/api/vqe/run",
        json={"molecule": "LiH", "provider": "no-such-provider", "ansatz": "UCCSD"},
    )
    assert response.status_code == 400


def test_run_drives_runner_and_returns_energy(client, monkeypatch):
    client.put(
        "/api/settings",
        json={"providers": {"qiskit": {"token": "tok-runner-test-9999"}}},
    )

    def fake_runner(*, molecule, provider, ansatz_kind, max_iter, estimator_factory, on_iteration):
        for i in range(1, 4):
            on_iteration(VQEIteration(iteration=i, energy=-7.86 + 0.01 * (3 - i)))
        return VQEResult(
            iterations=[],
            final_energy=-7.882,
            nuclear_repulsion=0.992,
            hf_energy=-7.85,
        )

    monkeypatch.setattr("app.routes.vqe._runner_factory", lambda: fake_runner)
    monkeypatch.setattr(
        "app.providers.qiskit_provider.QiskitProvider.make_estimator",
        lambda self, secret: None,
    )

    response = client.post(
        "/api/vqe/run",
        json={"molecule": "LiH", "provider": "qiskit", "ansatz": "UCCSD", "max_iter": 5},
    )
    assert response.status_code == 202
    run_id = response.json()["id"]

    final = _wait_for(client, run_id, "succeeded")
    assert final["final_energy"] == -7.882
    assert len(final["iterations"]) == 3
    assert [it["iteration"] for it in final["iterations"]] == [1, 2, 3]


def test_runner_exception_marks_run_failed(client, monkeypatch):
    client.put(
        "/api/settings",
        json={"providers": {"qiskit": {"token": "tok-failure-1111"}}},
    )
    monkeypatch.setattr(
        "app.providers.qiskit_provider.QiskitProvider.make_estimator",
        lambda self, secret: None,
    )

    def boom(**_kwargs):
        raise RuntimeError("optimizer exploded")

    monkeypatch.setattr("app.routes.vqe._runner_factory", lambda: boom)

    run_id = client.post(
        "/api/vqe/run",
        json={"molecule": "H2", "provider": "qiskit", "ansatz": "EfficientSU2"},
    ).json()["id"]
    final = _wait_for(client, run_id, "failed")
    assert "optimizer exploded" in final["error"]


def test_get_unknown_run_returns_404(client):
    response = client.get("/api/vqe/runs/does-not-exist")
    assert response.status_code == 404


def test_run_request_validates_molecule(client):
    response = client.post(
        "/api/vqe/run",
        json={"molecule": "NaCl", "provider": "qiskit"},
    )
    assert response.status_code == 422
