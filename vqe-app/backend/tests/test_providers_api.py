"""Coverage for /api/providers."""
from unittest.mock import patch


def test_unconfigured_providers(client):
    response = client.get("/api/providers")
    assert response.status_code == 200
    body = response.json()
    slugs = {item["slug"] for item in body}
    assert slugs == {"qiskit", "braket"}
    for item in body:
        assert item["configured"] is False
        assert item["ready"] is False
        assert item["schema_fields"], "every provider must declare its form fields"


def test_provider_response_shape_includes_display_name_and_schema(client):
    body = client.get("/api/providers").json()
    by_slug = {item["slug"]: item for item in body}
    assert by_slug["qiskit"]["display_name"] == "Qiskit IBM Runtime"
    field_names = [f["name"] for f in by_slug["qiskit"]["schema_fields"]]
    assert "token" in field_names
    assert any(f["secret"] for f in by_slug["qiskit"]["schema_fields"])


def test_configured_provider_runs_probe(client):
    client.put(
        "/api/settings",
        json={"providers": {"qiskit": {"token": "tok-aaaaaaaa-1234"}}},
    )
    with patch(
        "app.providers.qiskit_provider.QiskitProvider.probe",
        return_value=(True, "Backends available: ibm_kyiv"),
    ) as probe:
        response = client.get("/api/providers")
    by_slug = {item["slug"]: item for item in response.json()}
    assert by_slug["qiskit"]["configured"] is True
    assert by_slug["qiskit"]["ready"] is True
    assert "ibm_kyiv" in by_slug["qiskit"]["detail"]
    probe.assert_called_once()


def test_probe_failure_reports_not_ready(client):
    client.put(
        "/api/settings",
        json={"providers": {"braket": {"token": "tok-bbbbbbbb-5678"}}},
    )
    with patch(
        "app.providers.braket_provider.BraketProvider.probe",
        return_value=(False, "Probe failed: access denied"),
    ):
        response = client.get("/api/providers")
    by_slug = {item["slug"]: item for item in response.json()}
    assert by_slug["braket"]["configured"] is True
    assert by_slug["braket"]["ready"] is False
    assert "access denied" in by_slug["braket"]["detail"]


def test_new_provider_registers_without_touching_other_modules(client):
    """The whole point of the abstraction: dropping in a new Provider
    class and registering it must surface it in /api/providers, /api/settings,
    and accept /api/vqe runs against it — without edits to routes,
    models, or the frontend client schema.
    """
    from app.providers import register
    from app.providers.base import ProviderField

    class StubAzure:
        slug = "azure"
        display_name = "Azure Quantum (stub)"
        settings_schema = [
            ProviderField(name="token", label="Resource ID", secret=True, required=True),
        ]

        def probe(self, secret):
            return True, "Stub backend up"

        def make_estimator(self, secret):
            raise NotImplementedError

        def inspect_backend(self, estimator):
            return {"provider": self.slug}

    register(StubAzure())

    body = client.get("/api/providers").json()
    by_slug = {item["slug"]: item for item in body}
    assert "azure" in by_slug
    assert by_slug["azure"]["display_name"] == "Azure Quantum (stub)"

    settings = client.get("/api/settings").json()
    assert "azure" in settings["providers"]
