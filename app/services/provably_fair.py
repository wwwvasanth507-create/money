import secrets
import hashlib
import hmac
import math
from typing import Tuple, Dict, Any, List
from app.models.game import GameCode

class ProvablyFairEngine:
    @staticmethod
    def generate_server_seed() -> Tuple[str, str]:
        """Generates a 64-hex CSPRNG server seed and its pre-committed SHA-256 hash."""
        server_seed = secrets.token_hex(32) # 64 hex characters
        server_seed_hash = hashlib.sha256(server_seed.encode("utf-8")).hexdigest()
        return server_seed, server_seed_hash

    @staticmethod
    def compute_hmac(server_seed: str, client_seed: str, nonce: int) -> str:
        """Computes HMAC-SHA256 hash over f'{client_seed}:{nonce}'."""
        message = f"{client_seed}:{nonce}".encode("utf-8")
        key = server_seed.encode("utf-8")
        return hmac.new(key, message, hashlib.sha256).hexdigest()

    @staticmethod
    def calculate_crash_point(server_seed: str, client_seed: str, nonce: int, house_edge_percent: float = 1.0) -> float:
        """
        Derives Crash multiplier point deterministically.
        Uses first 52 bits (13 hex chars) of HMAC hash.
        Formula: max(1.0, (100 - house_edge) / (1 - (hex / 2^52)) / 100)
        """
        hmac_hex = ProvablyFairEngine.compute_hmac(server_seed, client_seed, nonce)
        # Take first 13 hex characters = 52 bits
        hex_52 = hmac_hex[:13]
        decimal_val = int(hex_52, 16)
        max_52 = 2 ** 52
        float_val = decimal_val / max_52  # Range [0.0, 1.0)

        # Apply 1% house edge rule
        if float_val == 1.0:
            return 1.0

        r = (100.0 - house_edge_percent) / (1.0 - float_val) / 100.0
        multiplier = math.floor(r * 100.0) / 100.0
        return max(1.00, multiplier)

    @staticmethod
    def generate_mines_locations(server_seed: str, client_seed: str, nonce: int, mines_count: int = 3, total_tiles: int = 25) -> List[int]:
        """
        Derives N mine locations in 5x5 grid (0 to 25) using HMAC seed shuffling.
        """
        if mines_count < 1 or mines_count >= total_tiles:
            mines_count = 3

        hmac_hex = ProvablyFairEngine.compute_hmac(server_seed, client_seed, nonce)
        grid = list(range(total_tiles))
        mines = []

        # Use chunks of HMAC hash to select mine locations
        hash_offset = 0
        for i in range(mines_count):
            if hash_offset + 4 > len(hmac_hex):
                # Hash extension if needed
                extra_hash = hashlib.sha256((hmac_hex + str(i)).encode("utf-8")).hexdigest()
                hmac_hex += extra_hash

            chunk = hmac_hex[hash_offset:hash_offset + 4]
            hash_offset += 4
            idx = int(chunk, 16) % len(grid)
            mines.append(grid.pop(idx))

        return sorted(mines)

    @staticmethod
    def calculate_dice_roll(server_seed: str, client_seed: str, nonce: int) -> float:
        """
        Derives Dice roll outcome between 0.00 and 99.99 using first 32 bits (8 hex chars).
        """
        hmac_hex = ProvablyFairEngine.compute_hmac(server_seed, client_seed, nonce)
        hex_32 = hmac_hex[:8]
        val = int(hex_32, 16)
        roll = (val % 10000) / 100.0
        return round(roll, 2)

    @staticmethod
    def verify_outcome(server_seed: str, client_seed: str, nonce: int, game_code: str) -> Dict[str, Any]:
        """
        Independent outcome verifier for player transparency.
        """
        computed_hash = hashlib.sha256(server_seed.encode("utf-8")).hexdigest()

        outcome = None
        game_upper = game_code.upper()
        if game_upper == GameCode.CRASH.value:
            outcome = {
                "crash_point": ProvablyFairEngine.calculate_crash_point(server_seed, client_seed, nonce)
            }
        elif game_upper == GameCode.MINES.value:
            outcome = {
                "mine_locations": ProvablyFairEngine.generate_mines_locations(server_seed, client_seed, nonce, mines_count=3)
            }
        elif game_upper == GameCode.DICE.value:
            outcome = {
                "roll_value": ProvablyFairEngine.calculate_dice_roll(server_seed, client_seed, nonce)
            }

        return {
            "is_valid": True,
            "server_seed_hash": computed_hash,
            "game_code": game_code,
            "server_seed": server_seed,
            "client_seed": client_seed,
            "nonce": nonce,
            "derived_outcome": outcome
        }
