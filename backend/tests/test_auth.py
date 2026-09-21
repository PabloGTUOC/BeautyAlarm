def test_healthz_stays_open(auth_client):
    assert auth_client.get("/healthz").status_code == 200


def test_endpoints_require_a_token(auth_client):
    assert auth_client.get("/products/").status_code == 401


def test_wrong_token_rejected(auth_client):
    response = auth_client.get("/products/", headers={"Authorization": "Bearer nope"})
    assert response.status_code == 401


def test_correct_token_accepted(auth_client):
    response = auth_client.get("/products/", headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200


def test_auth_disabled_when_no_token_configured(client):
    assert client.get("/products/").status_code == 200
