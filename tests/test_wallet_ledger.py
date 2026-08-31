import pytest
from app.services.wallet_service import WalletService
from app.models.wallet import TransactionType, WalletTransaction

def test_integer_paise_math_and_ledger_entry(db, player_user):
    wallet_before = WalletService.get_or_create_wallet(db, player_user.id)
    initial_balance = wallet_before.real_balance

    # Credit ₹500.00 = 50,000 paise
    wallet_after, tx = WalletService.credit_wallet(
        db=db,
        user_id=player_user.id,
        amount_paise=50000,
        trans_type=TransactionType.DEPOSIT.value,
        description="Test Deposit"
    )

    assert wallet_after.real_balance == initial_balance + 50000
    assert tx.amount == 50000
    assert tx.balance_before == initial_balance
    assert tx.balance_after == initial_balance + 50000
    assert tx.type == TransactionType.DEPOSIT.value

def test_locked_balance_deduction(db, player_user):
    wallet = WalletService.get_or_create_wallet(db, player_user.id)
    avail_before = wallet.available_balance

    # Lock ₹1,000.00 = 100,000 paise
    WalletService.lock_funds(
        db=db,
        user_id=player_user.id,
        amount_paise=100000,
        description="Withdrawal Hold"
    )

    db.refresh(wallet)
    assert wallet.locked_balance == 100000
    assert wallet.available_balance == avail_before - 100000

def test_insufficient_available_balance_debit_error(db, player_user):
    with pytest.raises(Exception) as exc_info:
        WalletService.debit_wallet(
            db=db,
            user_id=player_user.id,
            amount_paise=999999999, # Excess amount
            trans_type=TransactionType.BET_PLACED.value
        )
    assert "Insufficient available balance" in str(exc_info.value)
