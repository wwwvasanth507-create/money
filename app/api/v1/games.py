import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.game import Game, GameSession, GameCode, SessionStatus
from app.schemas.game import (
    StartGameRequest, MinesRevealTileRequest, CashoutRequest, DiceRollRequest,
    ProvablyFairVerifyRequest, GameSessionResponse, VerificationResultResponse,
    AviatorBetRequest, AviatorCashoutRequest
)
from app.api.deps import get_current_user
from app.services.wallet_service import WalletService
from app.services.provably_fair import ProvablyFairEngine
from app.services.responsible_gaming_service import ResponsibleGamingService
from app.services.crash_manager import CrashRoundManager
from app.models.wallet import TransactionType

router = APIRouter(prefix="/games", tags=["Provably Fair Games"])

@router.get("/crash/state")
def get_aviator_state():
    """Returns current live Aviator flight round state (phase, countdown, live multiplier, history)."""
    mgr = CrashRoundManager.get_instance()
    return mgr.get_current_state()

@router.post("/crash/bet")
def place_aviator_bet(
    req: AviatorBetRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Places bet on Panel 1 or Panel 2 during the BETTING phase."""
    ResponsibleGamingService.check_self_exclusion(db, current_user.id)

    game = db.query(Game).filter(Game.code == GameCode.CRASH.value).first()
    if not game or not game.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aviator game is inactive.")

    if req.bet_amount < game.min_bet or req.bet_amount > game.max_bet:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bet amount must be between ₹{game.min_bet / 100:.2f} and ₹{game.max_bet / 100:.2f}"
        )

    mgr = CrashRoundManager.get_instance()
    try:
        bet_info = mgr.place_bet(current_user.id, req.panel_key, req.bet_amount, req.client_seed)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

    # Debit bet amount from user's wallet
    WalletService.debit_wallet(
        db=db,
        user_id=current_user.id,
        amount_paise=req.bet_amount,
        trans_type=TransactionType.BET_PLACED.value,
        reference_type="AVIATOR_ROUND",
        description=f"Aviator Flight Bet on Panel #{req.panel_key.replace('p', '')}"
    )

    return bet_info

@router.post("/crash/cashout")
def cashout_aviator_bet(
    req: AviatorCashoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cashes out active flight bet at current live multiplier and credits wallet atomically!"""
    mgr = CrashRoundManager.get_instance()
    try:
        bet_info = mgr.cashout_bet(current_user.id, req.panel_key)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))

    # Payout = bet_amount * multiplier credited to wallet
    payout_paise = bet_info["payout_amount"]
    WalletService.credit_wallet(
        db=db,
        user_id=current_user.id,
        amount_paise=payout_paise,
        trans_type=TransactionType.BET_WIN.value,
        reference_id=f"aviator_{bet_info['round_id']}_{req.panel_key}",
        reference_type="AVIATOR_ROUND",
        description=f"Aviator Flight Win! Cashed out @ {bet_info['cashout_multiplier']:.2f}x! Payout: ₹{bet_info['payout_amount_inr']:.2f}"
    )

    return bet_info


@router.get("", response_model=List[dict])
def list_games(db: Session = Depends(get_db)):
    games = db.query(Game).filter(Game.is_active == True).all()
    return [
        {
            "id": g.id,
            "code": g.code,
            "name": g.name,
            "house_edge_percent": g.house_edge_percent,
            "min_bet_paise": g.min_bet,
            "min_bet_inr": g.min_bet / 100.0,
            "max_bet_paise": g.max_bet,
            "max_bet_inr": g.max_bet / 100.0
        }
        for g in games
    ]

@router.post("/start", response_model=GameSessionResponse)
def start_game_session(
    req: StartGameRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ResponsibleGamingService.check_self_exclusion(db, current_user.id)

    game = db.query(Game).filter(Game.code == req.game_code.upper()).first()
    if not game or not game.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found or inactive.")

    if req.bet_amount < game.min_bet or req.bet_amount > game.max_bet:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bet amount must be between ₹{game.min_bet / 100:.2f} and ₹{game.max_bet / 100:.2f}"
        )

    # Check active sessions for this user & game (Allow 2 active sessions for CRASH game to support Dual Bets)
    max_allowed = 2 if game.code == GameCode.CRASH.value else 1
    active_count = db.query(GameSession).filter(
        GameSession.user_id == current_user.id,
        GameSession.game_id == game.id,
        GameSession.status == SessionStatus.ACTIVE.value
    ).count()
    if active_count >= max_allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum active sessions ({max_allowed}) reached for this game. Complete your active round first."
        )


    # CSPRNG Seed generation
    server_seed, server_seed_hash = ProvablyFairEngine.generate_server_seed()
    client_seed = req.client_seed or "default_client_seed"
    nonce = db.query(GameSession).filter(GameSession.user_id == current_user.id).count() + 1

    # Prepare game-specific initial outcome data
    initial_outcome = {}
    if game.code == GameCode.CRASH.value:
        crash_point = ProvablyFairEngine.calculate_crash_point(server_seed, client_seed, nonce, game.house_edge_percent)
        initial_outcome = {"crash_point": crash_point}
    elif game.code == GameCode.MINES.value:
        mines_count = req.mines_count if req.mines_count and 1 <= req.mines_count <= 24 else 3
        mines_locations = ProvablyFairEngine.generate_mines_locations(server_seed, client_seed, nonce, mines_count)
        initial_outcome = {
            "mines_count": mines_count,
            "mines_locations": mines_locations,
            "revealed_tiles": [],
            "current_step": 0
        }

    # Atomic debit bet amount
    wallet, tx = WalletService.debit_wallet(
        db=db,
        user_id=current_user.id,
        amount_paise=req.bet_amount,
        trans_type=TransactionType.BET_PLACED.value,
        reference_type="GAME_SESSION",
        description=f"Bet placed for {game.name} round."
    )

    session = GameSession(
        game_id=game.id,
        user_id=current_user.id,
        server_seed=server_seed,
        server_seed_hash=server_seed_hash,
        client_seed=client_seed,
        nonce=nonce,
        bet_amount=req.bet_amount,
        payout_amount=0,
        multiplier=1.0,
        outcome_data=json.dumps(initial_outcome),
        status=SessionStatus.ACTIVE.value
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Return response without revealing server_seed while active
    return {
        "id": session.id,
        "game_code": game.code,
        "user_id": session.user_id,
        "server_seed_hash": session.server_seed_hash,
        "client_seed": session.client_seed,
        "nonce": session.nonce,
        "bet_amount": session.bet_amount,
        "bet_amount_inr": session.bet_amount / 100.0,
        "payout_amount": session.payout_amount,
        "payout_amount_inr": session.payout_amount / 100.0,
        "multiplier": session.multiplier,
        "status": session.status,
        "outcome_data": initial_outcome if game.code != GameCode.CRASH.value else {}, # Mask crash_point until cashout/bust
        "server_seed": None,
        "started_at": session.started_at,
        "ended_at": session.ended_at
    }

@router.post("/mines/reveal", response_model=GameSessionResponse)
def reveal_mines_tile(
    req: MinesRevealTileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(GameSession).filter(
        GameSession.id == req.session_id,
        GameSession.user_id == current_user.id
    ).first()

    if not session or session.status != SessionStatus.ACTIVE.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active Mines session not found.")

    game = db.query(Game).filter(Game.id == session.game_id).first()
    outcome = json.loads(session.outcome_data or "{}")

    tile_idx = req.tile_index
    if tile_idx < 0 or tile_idx > 24:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tile index. Must be 0 to 24.")

    revealed = outcome.get("revealed_tiles", [])
    if tile_idx in revealed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tile already revealed.")

    mines_locations = outcome.get("mines_locations", [])
    mines_count = outcome.get("mines_count", 3)

    if tile_idx in mines_locations:
        # Hit a mine! BUST!
        session.status = SessionStatus.BUST.value
        session.multiplier = 0.0
        session.payout_amount = 0
        session.ended_at = datetime.utcnow()
        revealed.append(tile_idx)
        outcome["revealed_tiles"] = revealed
        session.outcome_data = json.dumps(outcome)
        db.commit()
        db.refresh(session)

        return {
            "id": session.id,
            "game_code": game.code,
            "user_id": session.user_id,
            "server_seed_hash": session.server_seed_hash,
            "client_seed": session.client_seed,
            "nonce": session.nonce,
            "bet_amount": session.bet_amount,
            "bet_amount_inr": session.bet_amount / 100.0,
            "payout_amount": 0,
            "payout_amount_inr": 0.0,
            "multiplier": 0.0,
            "status": session.status,
            "outcome_data": outcome,
            "server_seed": session.server_seed, # Reveal seed on round end
            "started_at": session.started_at,
            "ended_at": session.ended_at
        }

    # Safe tile revealed
    revealed.append(tile_idx)
    outcome["revealed_tiles"] = revealed

    # Calculate next multiplier: 25_choose_safe / remaining_safe
    total_tiles = 25
    safe_tiles_count = total_tiles - mines_count
    k = len(revealed)

    # Multiplier formula for Mines: (25 / safe_tiles) * ...
    mult = 1.0
    for i in range(k):
        mult *= (total_tiles - i) / (safe_tiles_count - i)

    # Apply 1% house edge
    mult = round(mult * (1.0 - game.house_edge_percent / 100.0), 2)
    session.multiplier = mult
    session.outcome_data = json.dumps(outcome)

    # Auto cashout if all safe tiles revealed
    if len(revealed) == safe_tiles_count:
        payout_paise = int(round(session.bet_amount * session.multiplier))
        session.status = SessionStatus.CASHOUT.value
        session.payout_amount = payout_paise
        session.ended_at = datetime.utcnow()

        WalletService.credit_wallet(
            db=db,
            user_id=current_user.id,
            amount_paise=payout_paise,
            trans_type=TransactionType.BET_WIN.value,
            reference_id=str(session.id),
            reference_type="GAME_SESSION",
            description=f"Mines Win Payout! Multiplier: {session.multiplier}x"
        )

    db.commit()
    db.refresh(session)

    return {
        "id": session.id,
        "game_code": game.code,
        "user_id": session.user_id,
        "server_seed_hash": session.server_seed_hash,
        "client_seed": session.client_seed,
        "nonce": session.nonce,
        "bet_amount": session.bet_amount,
        "bet_amount_inr": session.bet_amount / 100.0,
        "payout_amount": session.payout_amount,
        "payout_amount_inr": session.payout_amount / 100.0,
        "multiplier": session.multiplier,
        "status": session.status,
        "outcome_data": outcome,
        "server_seed": session.server_seed if session.status != SessionStatus.ACTIVE.value else None,
        "started_at": session.started_at,
        "ended_at": session.ended_at
    }

@router.post("/cashout", response_model=GameSessionResponse)
def cashout_game_session(
    req: CashoutRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(GameSession).filter(
        GameSession.id == req.session_id,
        GameSession.user_id == current_user.id
    ).first()

    if not session or session.status != SessionStatus.ACTIVE.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Active game session not found.")

    game = db.query(Game).filter(Game.id == session.game_id).first()
    outcome = json.loads(session.outcome_data or "{}")

    multiplier = session.multiplier
    if game.code == GameCode.CRASH.value:
        # Cash out on crash game
        crash_point = outcome.get("crash_point", 1.0)
        # Server verifies cashout multiplier is <= crash_point
        multiplier = max(1.0, multiplier)
        if multiplier > crash_point:
            # Player tried to cashout after crash! BUST!
            session.status = SessionStatus.BUST.value
            session.multiplier = 0.0
            session.payout_amount = 0
            session.ended_at = datetime.utcnow()
            db.commit()
            db.refresh(session)
            return {
                "id": session.id,
                "game_code": game.code,
                "user_id": session.user_id,
                "server_seed_hash": session.server_seed_hash,
                "client_seed": session.client_seed,
                "nonce": session.nonce,
                "bet_amount": session.bet_amount,
                "bet_amount_inr": session.bet_amount / 100.0,
                "payout_amount": 0,
                "payout_amount_inr": 0.0,
                "multiplier": 0.0,
                "status": session.status,
                "outcome_data": outcome,
                "server_seed": session.server_seed,
                "started_at": session.started_at,
                "ended_at": session.ended_at
            }

    payout_paise = int(round(session.bet_amount * multiplier))
    session.status = SessionStatus.CASHOUT.value
    session.payout_amount = payout_paise
    session.ended_at = datetime.utcnow()

    # Credit win payout atomically
    WalletService.credit_wallet(
        db=db,
        user_id=current_user.id,
        amount_paise=payout_paise,
        trans_type=TransactionType.BET_WIN.value,
        reference_id=str(session.id),
        reference_type="GAME_SESSION",
        description=f"{game.name} Cashout Payout! Multiplier: {multiplier:.2f}x"
    )

    db.commit()
    db.refresh(session)

    return {
        "id": session.id,
        "game_code": game.code,
        "user_id": session.user_id,
        "server_seed_hash": session.server_seed_hash,
        "client_seed": session.client_seed,
        "nonce": session.nonce,
        "bet_amount": session.bet_amount,
        "bet_amount_inr": session.bet_amount / 100.0,
        "payout_amount": session.payout_amount,
        "payout_amount_inr": session.payout_amount / 100.0,
        "multiplier": session.multiplier,
        "status": session.status,
        "outcome_data": outcome,
        "server_seed": session.server_seed,
        "started_at": session.started_at,
        "ended_at": session.ended_at
    }

@router.post("/dice/roll", response_model=GameSessionResponse)
def roll_dice(
    req: DiceRollRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ResponsibleGamingService.check_self_exclusion(db, current_user.id)

    game = db.query(Game).filter(Game.code == GameCode.DICE.value).first()
    if not game or not game.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dice game not active.")

    if req.bet_amount < game.min_bet or req.bet_amount > game.max_bet:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bet amount must be between ₹{game.min_bet / 100:.2f} and ₹{game.max_bet / 100:.2f}"
        )

    target = req.target_value
    cond = req.condition.upper()
    if target < 1.0 or target > 98.0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Target value must be between 1.0 and 98.0")

    # Win probability & Multiplier calculation (with 1% house edge)
    win_chance = target if cond == "UNDER" else (100.0 - target)
    multiplier = round((100.0 - game.house_edge_percent) / win_chance, 4)

    # Generate CSPRNG Seed & Roll
    server_seed, server_seed_hash = ProvablyFairEngine.generate_server_seed()
    client_seed = req.client_seed or "default_client_seed"
    nonce = db.query(GameSession).filter(GameSession.user_id == current_user.id).count() + 1

    roll_result = ProvablyFairEngine.calculate_dice_roll(server_seed, client_seed, nonce)

    is_win = (roll_result < target) if cond == "UNDER" else (roll_result > target)

    # Atomic debit bet
    WalletService.debit_wallet(
        db=db,
        user_id=current_user.id,
        amount_paise=req.bet_amount,
        trans_type=TransactionType.BET_PLACED.value,
        reference_type="GAME_SESSION",
        description=f"Dice Roll Bet ({cond} {target})"
    )

    payout_paise = int(round(req.bet_amount * multiplier)) if is_win else 0
    session_status = SessionStatus.CASHOUT.value if is_win else SessionStatus.BUST.value

    outcome_data = {
        "roll_result": roll_result,
        "target_value": target,
        "condition": cond,
        "win_chance_percent": win_chance,
        "is_win": is_win
    }

    session = GameSession(
        game_id=game.id,
        user_id=current_user.id,
        server_seed=server_seed,
        server_seed_hash=server_seed_hash,
        client_seed=client_seed,
        nonce=nonce,
        bet_amount=req.bet_amount,
        payout_amount=payout_paise,
        multiplier=multiplier if is_win else 0.0,
        outcome_data=json.dumps(outcome_data),
        status=session_status,
        ended_at=datetime.utcnow()
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    if is_win:
        WalletService.credit_wallet(
            db=db,
            user_id=current_user.id,
            amount_paise=payout_paise,
            trans_type=TransactionType.BET_WIN.value,
            reference_id=str(session.id),
            reference_type="GAME_SESSION",
            description=f"Dice Win Payout! Roll: {roll_result} ({multiplier:.2f}x)"
        )

    return {
        "id": session.id,
        "game_code": game.code,
        "user_id": session.user_id,
        "server_seed_hash": session.server_seed_hash,
        "client_seed": session.client_seed,
        "nonce": session.nonce,
        "bet_amount": session.bet_amount,
        "bet_amount_inr": session.bet_amount / 100.0,
        "payout_amount": session.payout_amount,
        "payout_amount_inr": session.payout_amount / 100.0,
        "multiplier": multiplier if is_win else 0.0,
        "status": session.status,
        "outcome_data": outcome_data,
        "server_seed": session.server_seed, # Instantly revealed for Dice
        "started_at": session.started_at,
        "ended_at": session.ended_at
    }

@router.post("/verify", response_model=VerificationResultResponse)
def verify_provably_fair_round(req: ProvablyFairVerifyRequest):
    res = ProvablyFairEngine.verify_outcome(
        server_seed=req.server_seed,
        client_seed=req.client_seed,
        nonce=req.nonce,
        game_code=req.game_code
    )
    return {
        "is_valid": res["is_valid"],
        "computed_hash": res["server_seed_hash"],
        "game_code": res["game_code"],
        "server_seed": res["server_seed"],
        "client_seed": res["client_seed"],
        "nonce": res["nonce"],
        "derived_outcome": res["derived_outcome"]
    }
