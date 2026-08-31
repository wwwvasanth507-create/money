from tests.conftest import get_auth_headers

def test_super_admin_create_and_delete_payment_verifier(client, super_admin_user):
    headers = get_auth_headers(super_admin_user)

    # 1. Create Payment Verifier
    payload = {
        "username": "verifier_new",
        "email": "verifier_new@auragaming.com",
        "password": "VerifierPass123!"
    }
    res = client.post("/api/v1/admin/verifiers", json=payload, headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["username"] == "verifier_new"
    assert data["role"] == "PAYMENT_VERIFIER"
    verifier_id = data["id"]

    # 2. List Payment Verifiers
    res_list = client.get("/api/v1/admin/verifiers", headers=headers)
    assert res_list.status_code == 200
    verifiers = res_list.json()
    assert any(v["id"] == verifier_id for v in verifiers)

    # 3. Delete Payment Verifier
    res_del = client.delete(f"/api/v1/admin/verifiers/{verifier_id}", headers=headers)
    assert res_del.status_code == 200
    assert "deleted successfully" in res_del.json()["message"]

    # 4. Verify list no longer contains deleted verifier
    res_list2 = client.get("/api/v1/admin/verifiers", headers=headers)
    assert not any(v["id"] == verifier_id for v in res_list2.json())

def test_admin_cannot_create_or_delete_payment_verifier(client, admin_user, verifier_user):
    headers = get_auth_headers(admin_user)

    # Admin attempting to create verifier -> 403
    payload = {
        "username": "verifier_fail",
        "email": "verifier_fail@auragaming.com",
        "password": "VerifierPass123!"
    }
    res = client.post("/api/v1/admin/verifiers", json=payload, headers=headers)
    assert res.status_code == 403

    # Admin attempting to delete verifier -> 403
    res_del = client.delete(f"/api/v1/admin/verifiers/{verifier_user.id}", headers=headers)
    assert res_del.status_code == 403

def test_admin_and_super_admin_can_update_payment_config(client, admin_user, super_admin_user):
    admin_headers = get_auth_headers(admin_user)
    super_headers = get_auth_headers(super_admin_user)

    # 1. Admin updates payment config (UPI ID, min/max deposit, min/max withdrawal)
    update_payload = {
        "upi_id": "custommerchant@upi",
        "min_deposit_inr": 200.0,
        "max_deposit_inr": 100000.0,
        "min_withdrawal_inr": 300.0,
        "max_withdrawal_inr": 50000.0
    }
    res1 = client.put("/api/v1/admin/payment-config", json=update_payload, headers=admin_headers)
    assert res1.status_code == 200, res1.text
    data1 = res1.json()
    assert data1["upi_id"] == "custommerchant@upi"
    assert data1["min_deposit"] == 20000
    assert data1["max_deposit"] == 10000000
    assert data1["min_withdrawal"] == 30000
    assert data1["max_withdrawal"] == 5000000
    assert "custommerchant%40upi" in data1["qr_code_url"]

    # 2. Super Admin updates payment config
    update_payload2 = {
        "upi_id": "superadminmerchant@upi",
        "min_deposit_inr": 150.0
    }
    res2 = client.put("/api/v1/admin/payment-config", json=update_payload2, headers=super_headers)
    assert res2.status_code == 200
    assert res2.json()["upi_id"] == "superadminmerchant@upi"
    assert res2.json()["min_deposit"] == 15000

def test_verifier_and_player_cannot_update_payment_config(client, verifier_user, player_user):
    v_headers = get_auth_headers(verifier_user)
    p_headers = get_auth_headers(player_user)

    update_payload = {"upi_id": "hacker@upi"}

    res_v = client.put("/api/v1/admin/payment-config", json=update_payload, headers=v_headers)
    assert res_v.status_code == 403

    res_p = client.put("/api/v1/admin/payment-config", json=update_payload, headers=p_headers)
    assert res_p.status_code == 403

def test_player_can_fetch_wallet_config(client, player_user):
    p_headers = get_auth_headers(player_user)
    res = client.get("/api/v1/wallet/config", headers=p_headers)
    assert res.status_code == 200
    data = res.json()
    assert "upi_id" in data
    assert "qr_code_url" in data
    assert "min_deposit" in data
    assert "max_deposit" in data
