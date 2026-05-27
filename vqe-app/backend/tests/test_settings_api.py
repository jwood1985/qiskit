"""Coverage for /api/settings."""


def test_empty_settings(client):
    response = client.get("/api/settings")
    assert response.status_code == 200
    body = response.json()
    for provider in ("qiskit", "braket", "dynatrace"):
        assert body[provider]["configured"] is False
        assert body[provider]["token_fingerprint"] is None


def test_put_persists_and_redacts(client):
    payload = {
        "qiskit": {"token": "abcdef-qiskit-token-1234"},
        "braket": {
            "token": "abcdef-braket-secret-5678",
            "extra": {"access_key_id": "AKIAEXAMPLE", "region": "us-east-1"},
        },
        "dynatrace": {"token": "dt0c01.test.token.value-9999"},
    }
    response = client.put("/api/settings", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["qiskit"]["configured"] is True
    assert body["qiskit"]["token_fingerprint"] == "••••1234"
    assert body["braket"]["token_fingerprint"] == "••••5678"
    assert body["braket"]["extra"]["region"] == "us-east-1"
    assert body["dynatrace"]["token_fingerprint"] == "••••9999"
    # Raw tokens must never appear in the response.
    raw = response.text
    for token in (
        "abcdef-qiskit-token-1234",
        "abcdef-braket-secret-5678",
        "dt0c01.test.token.value-9999",
    ):
        assert token not in raw


def test_partial_update_preserves_other_providers(client):
    client.put(
        "/api/settings",
        json={"qiskit": {"token": "first-token-aaaa"}},
    )
    client.put(
        "/api/settings",
        json={"braket": {"token": "second-token-bbbb"}},
    )
    body = client.get("/api/settings").json()
    assert body["qiskit"]["configured"] is True
    assert body["qiskit"]["token_fingerprint"] == "••••aaaa"
    assert body["braket"]["configured"] is True
    assert body["braket"]["token_fingerprint"] == "••••bbbb"


def test_persistence_is_encrypted_on_disk(client, tmp_path, monkeypatch):
    client.put(
        "/api/settings",
        json={"qiskit": {"token": "needle-in-haystack-1111"}},
    )
    from app.config import get_config

    cipher_path = get_config().data_dir / "secrets.enc"
    assert cipher_path.exists()
    raw = cipher_path.read_bytes()
    assert b"needle-in-haystack" not in raw
