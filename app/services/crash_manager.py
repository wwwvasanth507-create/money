import time
import math
import threading
from typing import Dict, Any, List, Optional
from app.services.provably_fair import ProvablyFairEngine

class CrashRoundManager:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.round_id = 1
        self.phase = "BETTING"  # "BETTING", "IN_FLIGHT", "CRASHED"
        self.phase_start_time = time.time()
        self.betting_duration = 5.0  # 5 seconds betting phase
        self.crashed_duration = 2.5  # 2.5 seconds crashed pause phase

        self.server_seed = ""
        self.server_seed_hash = ""
        self.crash_point = 1.0
        self.min_crash_multiplier = 1.00
        self.max_crash_multiplier = 1000.00
        self.history: List[float] = [2.45, 1.12, 14.80, 3.20, 1.85, 5.40, 1.05]

        # Active bets: { user_id: { "p1": bet_dict, "p2": bet_dict } }
        self.bets: Dict[int, Dict[str, Any]] = {}
        self._init_new_round()

    @classmethod
    def get_instance(cls) -> 'CrashRoundManager':
        with cls._lock:
            if cls._instance is None:
                cls._instance = CrashRoundManager()
            return cls._instance

    def update_limits(self, min_mult: float, max_mult: float):
        """Updates minimum and maximum allowed crash multiplier limits live."""
        with self._lock:
            if min_mult < 1.0:
                raise ValueError("Minimum multiplier cannot be less than 1.00x")
            if max_mult < min_mult:
                raise ValueError("Maximum multiplier cannot be less than Minimum multiplier")
            self.min_crash_multiplier = round(min_mult, 2)
            self.max_crash_multiplier = round(max_mult, 2)

    def _init_new_round(self):
        self.round_id += 1
        self.server_seed, self.server_seed_hash = ProvablyFairEngine.generate_server_seed()
        client_seed = f"global_flight_{self.round_id}"
        raw_point = ProvablyFairEngine.calculate_crash_point(self.server_seed, client_seed, self.round_id, 1.0)

        # Enforce Admin Dynamic Multiplier Limits
        self.crash_point = max(self.min_crash_multiplier, min(raw_point, self.max_crash_multiplier))
        self.phase = "BETTING"
        self.phase_start_time = time.time()
        self.bets = {}

    def update_state(self):
        """Ticks state machine based on current time."""
        now = time.time()
        elapsed = now - self.phase_start_time

        if self.phase == "BETTING":
            if elapsed >= self.betting_duration:
                self.phase = "IN_FLIGHT"
                self.phase_start_time = now
        elif self.phase == "IN_FLIGHT":
            current_mult = self._calculate_live_multiplier(elapsed)
            if current_mult >= self.crash_point:
                self.phase = "CRASHED"
                self.phase_start_time = now
                self.history.insert(0, self.crash_point)
                if len(self.history) > 15:
                    self.history.pop()
        elif self.phase == "CRASHED":
            if elapsed >= self.crashed_duration:
                self._init_new_round()

    def _calculate_live_multiplier(self, flight_elapsed: float) -> float:
        if flight_elapsed <= 0:
            return 1.0
        mult = 1.0 + math.pow(flight_elapsed * 0.38, 1.75)
        return math.floor(mult * 100.0) / 100.0

    def get_current_state(self) -> Dict[str, Any]:
        with self._lock:
            self.update_state()
            now = time.time()
            elapsed = now - self.phase_start_time

            live_mult = 1.0
            countdown = 0.0

            if self.phase == "BETTING":
                countdown = max(0.0, round(self.betting_duration - elapsed, 1))
            elif self.phase == "IN_FLIGHT":
                live_mult = min(self.crash_point, self._calculate_live_multiplier(elapsed))
            elif self.phase == "CRASHED":
                live_mult = self.crash_point

            return {
                "round_id": self.round_id,
                "phase": self.phase,
                "server_seed_hash": self.server_seed_hash,
                "server_seed": self.server_seed if self.phase == "CRASHED" else None,
                "live_multiplier": live_mult,
                "crash_point": self.crash_point if self.phase == "CRASHED" else None,
                "min_crash_multiplier": self.min_crash_multiplier,
                "max_crash_multiplier": self.max_crash_multiplier,
                "countdown": countdown,
                "history": self.history
            }


    def place_bet(self, user_id: int, panel_key: str, bet_amount_paise: int, client_seed: str) -> Dict[str, Any]:
        with self._lock:
            self.update_state()
            if self.phase != "BETTING":
                raise ValueError("Betting phase has ended for this flight round. Wait for next flight!")

            if user_id not in self.bets:
                self.bets[user_id] = {}

            if panel_key in self.bets[user_id]:
                raise ValueError(f"Bet already placed for Panel #{panel_key.replace('p', '')} in this round.")

            bet_info = {
                "round_id": self.round_id,
                "user_id": user_id,
                "panel_key": panel_key,
                "bet_amount": bet_amount_paise,
                "bet_amount_inr": bet_amount_paise / 100.0,
                "client_seed": client_seed,
                "status": "ACTIVE",
                "cashout_multiplier": 0.0,
                "payout_amount": 0
            }
            self.bets[user_id][panel_key] = bet_info
            return bet_info

    def cashout_bet(self, user_id: int, panel_key: str) -> Dict[str, Any]:
        with self._lock:
            self.update_state()
            if self.phase != "IN_FLIGHT":
                raise ValueError("Flight is not in progress.")

            if user_id not in self.bets or panel_key not in self.bets[user_id]:
                raise ValueError("No active bet found for this panel in current flight.")

            bet_info = self.bets[user_id][panel_key]
            if bet_info["status"] != "ACTIVE":
                raise ValueError("Bet has already been cashed out or processed.")

            now = time.time()
            elapsed = now - self.phase_start_time
            current_mult = self._calculate_live_multiplier(elapsed)

            if current_mult >= self.crash_point:
                bet_info["status"] = "BUST"
                bet_info["cashout_multiplier"] = 0.0
                bet_info["payout_amount"] = 0
                raise ValueError("Flight crashed before cashout!")

            cashout_mult = current_mult
            payout_paise = int(round(bet_info["bet_amount"] * cashout_mult))

            bet_info["status"] = "CASHOUT"
            bet_info["cashout_multiplier"] = cashout_mult
            bet_info["payout_amount"] = payout_paise
            bet_info["payout_amount_inr"] = payout_paise / 100.0

            return bet_info

    def get_user_bet(self, user_id: int, panel_key: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            return self.bets.get(user_id, {}).get(panel_key)
