"""Coverage for /api/settings."""


def test_empty_settings(client):
    response = client.get("/api/settings")
    assert response.status_code == 200
    body = response.json()
    for slug in ("qiskit", "braket"):
        assert body["providers"][slug]["configured"] is False
        assert body["providers"][slug]["token_fingerprint"] is None
    assert body["dynatrace"]["configured"] is False


def test_put_persists_and_redacts(client):
    payload = {
        "providers": {
            "qiskit": {"token": "abcdef-qiskit-token-1234"},
            "braket": {
                "token": "abcdef-braket-secret-5678",
                "extra": {"access_key_id": "AKIAEXAMPLE", "region": "us-east-1"},
            },
        },
        "dynatrace": {"token": "dt0c01.test.token.value-9999"},
    }
    response = client.put("/api/settings", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["providers"]["qiskit"]["configured"] is True
    assert body["providers"]["qiskit"]["token_fingerprint"] == "••••1234"
    assert body["providers"]["braket"]["token_fingerprint"] == "••••5678"
    assert body["providers"]["braket"]["extra"]["region"] == "us-east-1"
    assert body["dynatrace"]["token_fingerprint"] == "••••9999"
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
        json={"providers": {"qiskit": {"token": "first-token-aaaa"}}},
    )
    client.put(
        "/api/settings",
        json={"providers": {"braket": {"token": "second-token-bbbb"}}},
    )
    body = client.get("/api/settings").json()
    assert body["providers"]["qiskit"]["configured"] is True
    assert body["providers"]["qiskit"]["token_fingerprint"] == "••••aaaa"
    assert body["providers"]["braket"]["configured"] is True
    assert body["providers"]["braket"]["token_fingerprint"] == "••••bbbb"


def test_unknown_provider_slug_is_ignored(client):
    response = client.put(
        "/api/settings",
        json={"providers": {"made-up-slug": {"token": "x"}}},
    )
    assert response.status_code == 200
    body = response.json()
    assert "made-up-slug" not in body["providers"]


def test_persistence_is_encrypted_on_disk(client):
    client.put(
        "/api/settings",
        json={"providers": {"qiskit": {"token": "needle-in-haystack-1111"}}},
    )
    from app.config import get_config

    cipher_path = get_config().data_dir / "secrets.enc"
    assert cipher_path.exists()
    raw = cipher_path.read_bytes()
    assert b"needle-in-haystack" not in raw
