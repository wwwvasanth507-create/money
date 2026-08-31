from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict
from app.models.game import GameCode, SessionStatus

class StartGameRequest(BaseModel):
    game_code: GameCode
    bet_amount: int                     # in paise
    client_seed: Optional[str] = "user_default_seed"
    mines_count: Optional[int] = 3      # For MINES game (1 to 24)

class MinesRevealTileRequest(BaseModel):
    session_id: int
    tile_index: int                    # 0 to 24

class CashoutRequest(BaseModel):
    session_id: int

class DiceRollRequest(BaseModel):
    bet_amount: int                     # in paise
    target_value: float                 # e.g., 50.0
    condition: str                      # "UNDER" or "OVER"
    client_seed: Optional[str] = "user_default_seed"

class AviatorBetRequest(BaseModel):
    panel_key: str                      # "p1" or "p2"
    bet_amount: int                     # in paise
    client_seed: Optional[str] = "user_default_seed"

class AviatorCashoutRequest(BaseModel):
    panel_key: str                      # "p1" or "p2"

class AviatorConfigUpdate(BaseModel):
    min_crash_multiplier: float        # e.g. 1.00
    max_crash_multiplier: float        # e.g. 100.00
    min_bet_inr: Optional[float] = None # e.g. 10.00
    max_bet_inr: Optional[float] = None # e.g. 50000.00



class ProvablyFairVerifyRequest(BaseModel):
    server_seed: str
    client_seed: str
    nonce: int
    game_code: GameCode

class GameSessionResponse(BaseModel):
    id: int
    game_code: str
    user_id: int
    server_seed_hash: str
    client_seed: str
    nonce: int
    bet_amount: int
    bet_amount_inr: float
    payout_amount: int
    payout_amount_inr: float
    multiplier: float
    status: SessionStatus
    outcome_data: Optional[Any] = None
    server_seed: Optional[str] = None   # Revealed only when session ended
    started_at: datetime
    ended_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class VerificationResultResponse(BaseModel):
    is_valid: bool
    computed_hash: str
    game_code: str
    server_seed: str
    client_seed: str
    nonce: int
    derived_outcome: Any
