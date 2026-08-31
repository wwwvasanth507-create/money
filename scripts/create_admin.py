import sys
import os
import argparse
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.orm import Session
from app.database import SessionLocal, Base, engine
from app.models.user import User, UserRole
from app.api.deps import get_password_hash
from app.services.wallet_service import WalletService

def main():
    parser = argparse.ArgumentParser(description="Create administrative or staff account for AURA GAMING")
    parser.add_argument("--username", required=True, help="Account Username")
    parser.add_argument("--email", required=True, help="Account Email Address")
    parser.add_argument("--password", required=True, help="Account Password")
    parser.add_argument(
        "--role",
        required=True,
        choices=["PAYMENT_VERIFIER", "ADMIN", "SUPER_ADMIN"],
        help="Account Role (PAYMENT_VERIFIER, ADMIN, SUPER_ADMIN)"
    )

    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        existing = db.query(User).filter(
            (User.username == args.username) | (User.email == args.email)
        ).first()

        if existing:
            print(f"Error: User with username '{args.username}' or email '{args.email}' already exists.")
            sys.exit(1)

        user = User(
            username=args.username,
            email=args.email,
            hashed_password=get_password_hash(args.password),
            role=args.role,
            is_active=True,
            is_verified=True
        )
        db.add(user)
        db.flush()

        WalletService.get_or_create_wallet(db, user.id)

        db.commit()
        print(f"Success! Admin user '{args.username}' created with role '{args.role}'.")

    except Exception as e:
        db.rollback()
        print(f"Failed to create admin user: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
