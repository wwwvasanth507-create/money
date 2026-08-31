import hashlib
from app.services.provably_fair import ProvablyFairEngine
from tests.conftest import get_auth_headers

def test_csprng_seed_hash_precommitment():
    server_seed, server_seed_hash = ProvablyFairEngine.generate_server_seed()
    assert len(server_seed) == 64
    assert len(server_seed_hash) == 64
    computed = hashlib.sha256(server_seed.encode("utf-8")).hexdigest()
    assert computed == server_seed_hash

def test_hmac_outcome_determinism_crash():
    seed = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    c_seed = "my_client_seed"
    nonce = 1

    cp1 = ProvablyFairEngine.calculate_crash_point(seed, c_seed, nonce, house_edge_percent=1.0)
    cp2 = ProvablyFairEngine.calculate_crash_point(seed, c_seed, nonce, house_edge_percent=1.0)
    assert cp1 == cp2
    assert cp1 >= 1.0

def test_dice_roll_and_verification_endpoint(client):
    res = client.post("/api/v1/games/verify", json={
        "server_seed": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        "client_seed": "test_client",
        "nonce": 1,
        "game_code": "DICE"
    })

    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] == True
    assert "derived_outcome" in data
    assert "roll_value" in data["derived_outcome"]
