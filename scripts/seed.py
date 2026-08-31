import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session
from app.database import engine, SessionLocal, Base
from app.models.user import User, UserRole
from app.models.payment import PaymentConfiguration
from app.models.game import Game, GameCode
from app.models.wallet import Wallet, WalletTransaction, TransactionType
from app.api.deps import get_password_hash
from app.services.wallet_service import WalletService

def seed_database():
    print("Initializing Database Schema...")
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        print("Seeding Games...")
        games_data = [
            {"code": GameCode.CRASH.value, "name": "Crash Multiplier", "house_edge_percent": 1.0, "min_bet": 1000, "max_bet": 1000000},
            {"code": GameCode.MINES.value, "name": "Mines Grid", "house_edge_percent": 1.0, "min_bet": 1000, "max_bet": 1000000},
            {"code": GameCode.DICE.value, "name": "Provably Fair Dice", "house_edge_percent": 1.0, "min_bet": 1000, "max_bet": 1000000},
        ]
        for g_data in games_data:
            existing = db.query(Game).filter(Game.code == g_data["code"]).first()
            if not existing:
                g = Game(**g_data)
                db.add(g)

        print("Seeding Payment Configuration...")
        payment_config = db.query(PaymentConfiguration).first()
        if not payment_config:
            payment_config = PaymentConfiguration(
                upi_id="auragaming@upi",
                min_deposit=10000,       # ₹100
                max_deposit=5000000,     # ₹50,000
                min_withdrawal=50000,    # ₹500
                max_withdrawal=10000000  # ₹100,000
            )
            db.add(payment_config)

        db.commit()

        print("Seeding Baseline Accounts...")
        # 1. Super Admin
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                email="admin@auragaming.local",
                mobile_number="9876543210",
                aadhaar_number="123456789012",
                hashed_password=get_password_hash("Admin@SecurePass2026!"),
                role=UserRole.SUPER_ADMIN.value,
                is_active=True,
                is_verified=True
            )
            db.add(admin)
            db.flush()
            WalletService.get_or_create_wallet(db, admin.id)

        # 2. Payment Verifier
        verifier = db.query(User).filter(User.username == "verifier1").first()
        if not verifier:
            verifier = User(
                username="verifier1",
                email="verifier@auragaming.local",
                mobile_number="9876543211",
                aadhaar_number="123456789013",
                hashed_password=get_password_hash("Verifier@SecurePass2026!"),
                role=UserRole.PAYMENT_VERIFIER.value,
                is_active=True,
                is_verified=True
            )
            db.add(verifier)
            db.flush()
            WalletService.get_or_create_wallet(db, verifier.id)

        # 3. Demo Player
        player = db.query(User).filter(User.username == "player1").first()
        if not player:
            player = User(
                username="player1",
                email="player@auragaming.local",
                mobile_number="9876543212",
                aadhaar_number="123456789014",
                hashed_password=get_password_hash("Player@SecurePass2026!"),
                role=UserRole.PLAYER.value,
                is_active=True,
                is_verified=True
            )
            db.add(player)
            db.flush()

            # Credit initial ₹2,500.00 = 250,000 paise
            WalletService.credit_wallet(
                db=db,
                user_id=player.id,
                amount_paise=250000,
                trans_type=TransactionType.BONUS_CREDIT.value,
                created_by="SYSTEM_SEED",
                description="Initial Demo Balance Credit (₹2,500.00)"
            )

        db.commit()
        print("Database Seeding Completed Successfully!")
        print("Default Seed Accounts:")
        print("  Super Admin:      admin / Admin@SecurePass2026!")
        print("  Payment Verifier: verifier1 / Verifier@SecurePass2026!")
        print("  Demo Player:      player1 / Player@SecurePass2026! (Balance: Rs.2,500.00)")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
