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


def test_real_hardware_run_requires_credentials(client):
    response = client.post(
        "/api/vqe/run",
        json={
            "molecule": "LiH",
            "provider": "qiskit",
            "ansatz": "UCCSD",
            "use_real_hardware": True,
        },
    )
    assert response.status_code == 202
    body = response.json()
    final = _wait_for(client, body["id"], "failed")
    assert "no token configured" in final["error"].lower()


def test_simulator_run_does_not_require_credentials(client, monkeypatch):
    """Simulator is the dev default — must work with an empty secrets
    store and no UI configuration."""
    monkeypatch.setattr(
        "app.providers.qiskit_provider.QiskitProvider.make_estimator",
        lambda self, secret, *, simulator: None,
    )

    def fake_runner(*, molecule, provider_slug, provider, ansatz_kind, max_iter,
                    estimator_factory, on_iteration, on_job_event,
                    use_real_hardware):
        # Confirm the simulator switch reached the factory closure.
        estimator_factory(None)
        assert use_real_hardware is False
        return VQEResult(iterations=[], final_energy=-1.123,
                         nuclear_repulsion=0.0, hf_energy=-1.0)

    monkeypatch.setattr("app.routes.vqe._runner_factory", lambda: fake_runner)

    response = client.post(
        "/api/vqe/run",
        json={"molecule": "H2", "provider": "qiskit", "ansatz": "EfficientSU2"},
    )
    assert response.status_code == 202
    final = _wait_for(client, response.json()["id"], "succeeded")
    assert final["final_energy"] == -1.123


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

    def fake_runner(*, molecule, provider_slug, provider, ansatz_kind, max_iter,
                    estimator_factory, on_iteration, on_job_event,
                    use_real_hardware):
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
        lambda self, secret, *, simulator: None,
    )

    response = client.post(
        "/api/vqe/run",
        json={
            "molecule": "LiH",
            "provider": "qiskit",
            "ansatz": "UCCSD",
            "max_iter": 5,
            "use_real_hardware": True,
        },
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
        lambda self, secret, *, simulator: None,
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


def test_job_lifecycle_events_surface_to_run_status(client, monkeypatch):
    """The runner emits on_job_event for each state transition; those
    must reach the run record so the UI can render queue/run progress
    without blocking. This is the verification criterion for Phase D.
    """
    from app.models import JobSnapshotPayload

    def fake_runner(*, molecule, provider_slug, provider, ansatz_kind,
                    max_iter, estimator_factory, on_iteration,
                    on_job_event, use_real_hardware):
        # Walk through the canonical state vocabulary one transition at
        # a time so we can observe each one surface to the API.
        for state, queue_t, exec_t in [
            ("submitted", None, None),
            ("queued", None, None),
            ("running", 3.2, None),
            ("completed", 3.2, 1.7),
        ]:
            on_job_event(JobSnapshotPayload(
                state=state, queue_time_s=queue_t, execution_time_s=exec_t,
                backend="ibm_kyiv", shots=4096,
            ))
            time.sleep(0.02)  # let the API observer pick the change up
        return VQEResult(
            iterations=[], final_energy=-7.882,
            nuclear_repulsion=0.992, hf_energy=-7.85,
        )

    monkeypatch.setattr("app.routes.vqe._runner_factory", lambda: fake_runner)

    response = client.post(
        "/api/vqe/run",
        json={"molecule": "LiH", "provider": "qiskit", "ansatz": "UCCSD"},
    )
    final = _wait_for(client, response.json()["id"], "succeeded")
    assert final["current_job_state"] == "completed"
    assert final["last_job_snapshot"]["backend"] == "ibm_kyiv"
    assert final["last_job_snapshot"]["queue_time_s"] == 3.2
    assert final["last_job_snapshot"]["execution_time_s"] == 1.7
    assert final["last_job_snapshot"]["shots"] == 4096
