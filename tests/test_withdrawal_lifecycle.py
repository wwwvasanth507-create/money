from tests.conftest import get_auth_headers
from app.services.wallet_service import WalletService
from app.models.payment import WithdrawalStatus

def test_withdrawal_lifecycle_approve(client, db, player_user, super_admin_user):
    player_headers = get_auth_headers(player_user)
    admin_headers = get_auth_headers(super_admin_user)

    wallet_before = WalletService.get_or_create_wallet(db, player_user.id)
    real_before = wallet_before.real_balance

    # 1. Submit withdrawal request ₹500.00 = 50,000 paise
    res = client.post("/api/v1/wallet/withdraw", json={
        "amount": 50000,
        "upi_id": "player@paytm"
    }, headers=player_headers)

    assert res.status_code == 200
    w_data = res.json()
    w_id = w_data["id"]

    # Refresh session identity map after client API execution
    db.expire_all()

    # 2. Check locked balance
    wallet_mid = WalletService.get_or_create_wallet(db, player_user.id)
    assert wallet_mid.locked_balance == 50000
    assert wallet_mid.available_balance == real_before - 50000

    # 3. Super Admin approves withdrawal
    proc_res = client.post(f"/api/v1/admin/withdrawals/{w_id}/process", json={
        "action": "APPROVE",
        "notes": "Paid out via IMPS bank gateway"
    }, headers=admin_headers)

    assert proc_res.status_code == 200
    assert proc_res.json()["status"] == WithdrawalStatus.APPROVED.value

    db.expire_all()

    # 4. Check balance settled
    wallet_final = WalletService.get_or_create_wallet(db, player_user.id)
    assert wallet_final.locked_balance == 0
    assert wallet_final.real_balance == real_before - 50000

def test_withdrawal_lifecycle_reject(client, db, player_user, super_admin_user):
    player_headers = get_auth_headers(player_user)
    admin_headers = get_auth_headers(super_admin_user)

    wallet_before = WalletService.get_or_create_wallet(db, player_user.id)
    real_before = wallet_before.real_balance

    # 1. Submit withdrawal request
    w_data = client.post("/api/v1/wallet/withdraw", json={
        "amount": 50000,
        "upi_id": "player@paytm"
    }, headers=player_headers).json()

    w_id = w_data["id"]

    # 2. Admin rejects withdrawal
    proc_res = client.post(f"/api/v1/admin/withdrawals/{w_id}/process", json={
        "action": "REJECT",
        "notes": "Incorrect UPI ID"
    }, headers=admin_headers)

    assert proc_res.status_code == 200
    assert proc_res.json()["status"] == WithdrawalStatus.REJECTED.value

    db.expire_all()

    # 3. Check funds unlocked back to available balance
    wallet_final = WalletService.get_or_create_wallet(db, player_user.id)
    assert wallet_final.locked_balance == 0
    assert wallet_final.real_balance == real_before
