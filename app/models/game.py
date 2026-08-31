import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, BigInteger, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class GameCode(str, enum.Enum):
    CRASH = "CRASH"
    MINES = "MINES"
    DICE = "DICE"

class SessionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    CASHOUT = "CASHOUT"
    BUST = "BUST"
    CANCELLED = "CANCELLED"

class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True) # CRASH, MINES, DICE
    name = Column(String(50), nullable=False)
    house_edge_percent = Column(Float, default=1.0, nullable=False)    # e.g., 1.0% house edge
    is_active = Column(Boolean, default=True, nullable=False)
    min_bet = Column(BigInteger, default=1000, nullable=False)         # ₹10 = 1,000 paise
    max_bet = Column(BigInteger, default=1000000, nullable=False)      # ₹10,000 = 1,000,000 paise

    sessions = relationship("GameSession", back_populates="game")

class GameSession(Base):
    __tablename__ = "game_sessions"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    server_seed = Column(String(128), nullable=False)                  # Revealed on end
    server_seed_hash = Column(String(64), nullable=False, index=True)  # Pre-committed SHA-256
    client_seed = Column(String(64), nullable=False)
    nonce = Column(Integer, default=1, nullable=False)
    bet_amount = Column(BigInteger, nullable=False)                     # in paise
    payout_amount = Column(BigInteger, default=0, nullable=False)       # in paise
    multiplier = Column(Float, default=0.0, nullable=False)
    outcome_data = Column(Text, nullable=True)                          # JSON text
    status = Column(String(20), default=SessionStatus.ACTIVE.value, nullable=False, index=True)
    started_at = Column(DateTime, default=utc_now, nullable=False)
    ended_at = Column(DateTime, nullable=True)

    game = relationship("Game", back_populates="sessions")
    user = relationship("User")

