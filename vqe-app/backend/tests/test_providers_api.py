"""Coverage for /api/providers."""
from unittest.mock import patch


def test_unconfigured_providers(client):
    response = client.get("/api/providers")
    assert response.status_code == 200
    body = response.json()
    names = {item["name"] for item in body}
    assert names == {"qiskit", "braket"}
    for item in body:
        assert item["configured"] is False
        assert item["ready"] is False


def test_configured_provider_runs_probe(client):
    client.put(
        "/api/settings",
        json={"qiskit": {"token": "tok-aaaaaaaa-1234"}},
    )
    with patch(
        "app.providers.qiskit_provider.probe",
        return_value=(True, "Backends available: ibm_kyiv"),
    ) as probe:
        response = client.get("/api/providers")
    assert response.status_code == 200
    by_name = {item["name"]: item for item in response.json()}
    assert by_name["qiskit"]["configured"] is True
    assert by_name["qiskit"]["ready"] is True
    assert "ibm_kyiv" in by_name["qiskit"]["detail"]
    probe.assert_called_once()


def test_probe_failure_reports_not_ready(client):
    client.put(
        "/api/settings",
        json={"braket": {"token": "tok-bbbbbbbb-5678"}},
    )
    with patch(
        "app.providers.braket_provider.probe",
        return_value=(False, "Probe failed: access denied"),
    ):
        response = client.get("/api/providers")
    by_name = {item["name"]: item for item in response.json()}
    assert by_name["braket"]["configured"] is True
    assert by_name["braket"]["ready"] is False
    assert "access denied" in by_name["braket"]["detail"]
