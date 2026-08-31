from typing import Dict, Any, List
from pydantic import BaseModel

class GameRTPStat(BaseModel):
    game_code: str
    game_name: str
    total_bets: int
    total_bets_inr: float
    total_payouts: int
    total_payouts_inr: float
    ggr: int
    ggr_inr: float
    actual_rtp_percent: float

class EconomicsPreviewResponse(BaseModel):
    total_deposits_paise: int
    total_deposits_inr: float
    total_withdrawals_paise: int
    total_withdrawals_inr: float
    total_bets_paise: int
    total_bets_inr: float
    total_payouts_paise: int
    total_payouts_inr: float
    ggr_paise: int
    ggr_inr: float
    ngr_paise: int
    ngr_inr: float
    total_players_count: int
    active_players_count: int
    pending_deposits_count: int
    pending_withdrawals_count: int
    game_stats: List[GameRTPStat]
