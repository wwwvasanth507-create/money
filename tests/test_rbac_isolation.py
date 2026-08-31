from tests.conftest import get_auth_headers

def test_player_cannot_access_verifier_or_admin_endpoints(client, player_user):
    headers = get_auth_headers(player_user)

    res1 = client.get("/api/v1/admin/deposits/pending", headers=headers)
    assert res1.status_code == 403

    res2 = client.get("/api/v1/admin/economics/preview", headers=headers)
    assert res2.status_code == 403

def test_payment_verifier_restricted_from_admin_economics(client, verifier_user):
    headers = get_auth_headers(verifier_user)

    # Verifier CAN access pending deposits
    res1 = client.get("/api/v1/admin/deposits/pending", headers=headers)
    assert res1.status_code == 200

    # Verifier CANNOT access economics preview or payment config updates
    res2 = client.get("/api/v1/admin/economics/preview", headers=headers)
    assert res2.status_code == 403

def test_super_admin_full_access(client, super_admin_user):
    headers = get_auth_headers(super_admin_user)

    res1 = client.get("/api/v1/admin/deposits/pending", headers=headers)
    assert res1.status_code == 200

    res2 = client.get("/api/v1/admin/economics/preview", headers=headers)
    assert res2.status_code == 200
