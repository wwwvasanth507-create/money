from tests.conftest import get_auth_headers
from app.services.wallet_service import WalletService
from app.models.payment import DepositStatus

def test_deposit_submission_zero_auto_credit(client, player_user):
    headers = get_auth_headers(player_user)
    wallet_before = client.get("/api/v1/wallet/balance", headers=headers).json()

    # Submit deposit request
    res = client.post("/api/v1/wallet/deposit", data={
        "utr_number": "UTR123456789",
        "amount_inr": "500.00"
    }, headers=headers)

    assert res.status_code == 200
    deposit_data = res.json()
    assert deposit_data["status"] == "PENDING"

    # Verify wallet balance remained completely unchanged
    wallet_after = client.get("/api/v1/wallet/balance", headers=headers).json()
    assert wallet_after["real_balance"] == wallet_before["real_balance"]

def test_payment_verifier_approval_workflow(client, db, player_user, verifier_user):
    player_headers = get_auth_headers(player_user)
    verifier_headers = get_auth_headers(verifier_user)

    balance_before = WalletService.get_or_create_wallet(db, player_user.id).real_balance

    # 1. Player submits claim
    dep_res = client.post("/api/v1/wallet/deposit", data={
        "utr_number": "UTR999888777",
        "amount_inr": "1000.00"
    }, headers=player_headers).json()

    dep_id = dep_res["id"]

    # 2. Verifier inspects pending deposits
    pending_list = client.get("/api/v1/admin/deposits/pending", headers=verifier_headers).json()
    assert any(d["id"] == dep_id for d in pending_list)

    # 3. Verifier approves claim with mandatory notes
    verify_res = client.post(f"/api/v1/admin/deposits/{dep_id}/verify", json={
        "action": "APPROVE",
        "verifier_notes": "Verified against HDFC settlement statement #10293"
    }, headers=verifier_headers)

    assert verify_res.status_code == 200
    assert verify_res.json()["status"] == DepositStatus.APPROVED.value

    # 4. Player balance is credited ₹1,000.00 = 100,000 paise
    balance_after = WalletService.get_or_create_wallet(db, player_user.id).real_balance
    assert balance_after == balance_before + 100000
