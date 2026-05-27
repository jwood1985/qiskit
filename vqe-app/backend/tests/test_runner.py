"""Direct coverage of the VQE runner's polling logic.

The API-level test in ``test_vqe_api.py`` mocks the whole runner. This
one exercises the real ``run_vqe`` code with stub chemistry / estimator
so the submit → poll → completion path itself is verified.
"""
from __future__ import annotations

from types import SimpleNamespace

from app.models import AnsatzName, Molecule
from app.providers.base import JobSnapshot
from app.vqe import runner as runner_mod


def test_runner_polls_job_lifecycle_until_terminal(monkeypatch):
    fake_problem = SimpleNamespace(
        qubit_op=SimpleNamespace(num_qubits=2),
        num_particles=(1, 1),
        num_spatial_orbitals=2,
        nuclear_repulsion=0.0,
        hf_energy=-1.0,
        problem=None,
    )
    fake_ansatz = SimpleNamespace(num_parameters=2)
    monkeypatch.setattr(runner_mod, "build_problem", lambda _m: fake_problem)
    monkeypatch.setattr(runner_mod, "build_ansatz", lambda _p, _k: fake_ansatz)

    class FakeJob:
        def __init__(self):
            self._states = iter(["queued", "running", "completed"])
            self._current = "queued"
            self.values = [-1.234]

        def job_id(self):
            return "fake-job"

        def advance(self) -> str:
            try:
                self._current = next(self._states)
            except StopIteration:
                self._current = "completed"
            return self._current

        def result(self):
            return self

    class FakeEstimator:
        def run(self, *_a, **_k):
            return FakeJob()

    emitted: list[str] = []

    class FakeProvider:
        slug = "fake"
        display_name = "Fake"
        settings_schema: list = []

        def probe(self, secret):
            return True, "ok"

        def make_estimator(self, secret, *, simulator):
            return FakeEstimator()

        def inspect_backend(self, estimator):
            return {"backend": "fake-sim"}

        def snapshot_job(self, job):
            return JobSnapshot(state=job.advance(), backend="fake-sim")

    result = runner_mod.run_vqe(
        molecule=Molecule.H2,
        provider_slug="fake",
        provider=FakeProvider(),
        ansatz_kind=AnsatzName.HARDWARE_EFFICIENT,
        max_iter=1,
        estimator_factory=lambda _ansatz: FakeEstimator(),
        on_job_event=lambda snap: emitted.append(snap.state),
        poll_interval_s=0.0,
    )

    # First iteration walks the full lifecycle; subsequent iterations
    # may start at "completed" because state lists are per-job.
    assert "queued" in emitted
    assert "running" in emitted
    assert "completed" in emitted
    # And each iteration's expectation reached the result.
    assert result.final_energy == -1.234


def test_runner_raises_on_failed_job_state(monkeypatch):
    fake_problem = SimpleNamespace(
        qubit_op=SimpleNamespace(num_qubits=2),
        num_particles=(1, 1),
        num_spatial_orbitals=2,
        nuclear_repulsion=0.0,
        hf_energy=-1.0,
        problem=None,
    )
    fake_ansatz = SimpleNamespace(num_parameters=2)
    monkeypatch.setattr(runner_mod, "build_problem", lambda _m: fake_problem)
    monkeypatch.setattr(runner_mod, "build_ansatz", lambda _p, _k: fake_ansatz)

    class FailingProvider:
        slug = "fail"
        display_name = "Fail"
        settings_schema: list = []

        def probe(self, secret):
            return True, "ok"

        def make_estimator(self, secret, *, simulator):
            return SimpleNamespace(run=lambda *a, **k: SimpleNamespace(
                job_id=lambda: "x", values=[0.0],
            ))

        def inspect_backend(self, estimator):
            return {}

        def snapshot_job(self, job):
            return JobSnapshot(state="failed", raw_state="ERROR")

    try:
        runner_mod.run_vqe(
            molecule=Molecule.H2,
            provider_slug="fail",
            provider=FailingProvider(),
            ansatz_kind=AnsatzName.HARDWARE_EFFICIENT,
            max_iter=1,
            estimator_factory=lambda _ansatz: FailingProvider().make_estimator({}, simulator=True),
            poll_interval_s=0.0,
        )
    except RuntimeError as exc:
        assert "failed" in str(exc).lower()
    else:
        raise AssertionError("expected RuntimeError on failed quantum job")
