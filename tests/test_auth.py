from tests.conftest import get_auth_headers

def test_user_registration(client):
    response = client.post("/api/v1/auth/register", json={
        "username": "new_player",
        "email": "new_player@domain.com",
        "password": "Password123!"
    })
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "new_player"
    assert data["role"] == "PLAYER"

def test_user_login(client, player_user):
    response = client.post("/api/v1/auth/login/json", json={
        "username": "player_test",
        "password": "PlayerPass123!"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "PLAYER"

def test_get_me_profile(client, player_user):
    headers = get_auth_headers(player_user)
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "player_test"
