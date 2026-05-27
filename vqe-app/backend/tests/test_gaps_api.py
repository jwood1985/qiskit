def test_gaps_endpoint_returns_markdown(client):
    response = client.get("/api/gaps")
    assert response.status_code == 200
    body = response.json()
    assert "markdown" in body
    # GAPS.md ships in the repo and starts with the H1.
    assert body["markdown"].lstrip().startswith("# GAPS.md")
