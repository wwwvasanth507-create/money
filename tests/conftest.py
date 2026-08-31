import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app
from app.models.user import User, UserRole
from app.models.payment import PaymentConfiguration
from app.models.game import Game, GameCode
from app.api.deps import get_password_hash, create_access_token
from app.services.wallet_service import WalletService
from app.models.wallet import TransactionType

# In-memory SQLite with StaticPool so all connections share the same memory DB
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function", autouse=True)
def setup_test_database():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    
    # Initialize Payment Configuration
    config = PaymentConfiguration(
        upi_id="auragaming@upi",
        min_deposit=10000,       # ₹100
        max_deposit=5000000,     # ₹50,000
        min_withdrawal=50000,    # ₹500
        max_withdrawal=10000000  # ₹100,000
    )
    session.add(config)

    # Initialize Games
    g1 = Game(code=GameCode.CRASH.value, name="Crash", house_edge_percent=1.0, min_bet=1000, max_bet=1000000)
    g2 = Game(code=GameCode.MINES.value, name="Mines", house_edge_percent=1.0, min_bet=1000, max_bet=1000000)
    g3 = Game(code=GameCode.DICE.value, name="Dice", house_edge_percent=1.0, min_bet=1000, max_bet=1000000)
    session.add_all([g1, g2, g3])
    session.commit()
    session.close()

    yield

    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture(scope="function")
def client():
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def super_admin_user(db):
    user = User(
        username="admin_test",
        email="admin_test@auragaming.local",
        hashed_password=get_password_hash("AdminPass123!"),
        role=UserRole.SUPER_ADMIN.value,
        is_active=True,
        is_verified=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    WalletService.get_or_create_wallet(db, user.id)
    return user

@pytest.fixture
def admin_user(db):
    user = User(
        username="ops_admin_test",
        email="ops_admin_test@auragaming.local",
        hashed_password=get_password_hash("AdminPass123!"),
        role=UserRole.ADMIN.value,
        is_active=True,
        is_verified=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    WalletService.get_or_create_wallet(db, user.id)
    return user


@pytest.fixture
def verifier_user(db):
    user = User(
        username="verifier_test",
        email="verifier_test@auragaming.local",
        hashed_password=get_password_hash("VerifierPass123!"),
        role=UserRole.PAYMENT_VERIFIER.value,
        is_active=True,
        is_verified=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    WalletService.get_or_create_wallet(db, user.id)
    return user

@pytest.fixture
def player_user(db):
    user = User(
        username="player_test",
        email="player_test@auragaming.local",
        hashed_password=get_password_hash("PlayerPass123!"),
        role=UserRole.PLAYER.value,
        is_active=True,
        is_verified=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Seed initial ₹2,500.00 = 250,000 paise
    WalletService.credit_wallet(
        db=db,
        user_id=user.id,
        amount_paise=250000,
        trans_type=TransactionType.BONUS_CREDIT.value,
        description="Initial Seed Balance"
    )
    return user

def get_auth_headers(user: User):
    token = create_access_token(data={"sub": user.username, "role": user.role})
    return {"Authorization": f"Bearer {token}"}
