import pytest
from app.services.crash_manager import CrashRoundManager

def test_crash_manager_singleton_and_state():
    mgr = CrashRoundManager.get_instance()
    state = mgr.get_current_state()

    assert "round_id" in state
    assert "phase" in state
    assert state["phase"] in ["BETTING", "IN_FLIGHT", "CRASHED"]
    assert "server_seed_hash" in state
    assert "history" in state
    assert isinstance(state["history"], list)

def test_aviator_bet_placement_during_betting_phase(client, player_user):
    from app.api.deps import create_access_token
    token = create_access_token({"sub": player_user.username})
    headers = {"Authorization": f"Bearer {token}"}

    mgr = CrashRoundManager.get_instance()
    mgr._init_new_round()  # Force BETTING phase

    resp = client.post(
        "/api/v1/games/crash/bet",
        json={"panel_key": "p1", "bet_amount": 1000, "client_seed": "test_seed"},
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["panel_key"] == "p1"
    assert data["bet_amount"] == 1000
    assert data["status"] == "ACTIVE"

def test_aviator_cashout_mid_flight(client, player_user):
    from app.api.deps import create_access_token
    token = create_access_token({"sub": player_user.username})
    headers = {"Authorization": f"Bearer {token}"}

    mgr = CrashRoundManager.get_instance()
    mgr._init_new_round()
    mgr.phase = "IN_FLIGHT"
    mgr.crash_point = 10.0  # High crash point

    mgr.bets[player_user.id] = {
        "p1": {
            "round_id": mgr.round_id,
            "user_id": player_user.id,
            "panel_key": "p1",
            "bet_amount": 1000,
            "bet_amount_inr": 10.0,
            "status": "ACTIVE"
        }
    }

    resp = client.post(
        "/api/v1/games/crash/cashout",
        json={"panel_key": "p1"},
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "CASHOUT"
    assert data["cashout_multiplier"] >= 1.0
    assert data["payout_amount"] > 0

def test_admin_can_update_aviator_limits(client, super_admin_user):
    from app.api.deps import create_access_token
    token = create_access_token({"sub": super_admin_user.username})
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.put(
        "/api/v1/admin/aviator-config",
        json={"min_crash_multiplier": 1.50, "max_crash_multiplier": 5.00},
        headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["min_crash_multiplier"] == 1.50
    assert data["max_crash_multiplier"] == 5.00

    mgr = CrashRoundManager.get_instance()
    assert mgr.min_crash_multiplier == 1.50
    assert mgr.max_crash_multiplier == 5.00

    # Reset back to default
    mgr.update_limits(1.00, 1000.00)

def test_player_cannot_update_aviator_limits(client, player_user):
    from app.api.deps import create_access_token
    token = create_access_token({"sub": player_user.username})
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.put(
        "/api/v1/admin/aviator-config",
        json={"min_crash_multiplier": 2.00, "max_crash_multiplier": 10.00},
        headers=headers
    )
    assert resp.status_code == 403

def test_admin_can_update_aviator_bet_amount_limits(client, super_admin_user, player_user):
    from app.api.deps import create_access_token
    admin_token = create_access_token({"sub": super_admin_user.username})
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Set min bet to ₹50.00 and max bet to ₹500.00
    resp = client.put(
        "/api/v1/admin/aviator-config",
        json={
            "min_crash_multiplier": 1.00,
            "max_crash_multiplier": 100.00,
            "min_bet_inr": 50.0,
            "max_bet_inr": 500.0
        },
        headers=admin_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["min_bet_inr"] == 50.0
    assert data["max_bet_inr"] == 500.0

    player_token = create_access_token({"sub": player_user.username})
    player_headers = {"Authorization": f"Bearer {player_token}"}

    mgr = CrashRoundManager.get_instance()
    mgr._init_new_round()

    # Attempt bet below min (₹10.00 = 1000 paise) -> Should fail
    resp_low = client.post(
        "/api/v1/games/crash/bet",
        json={"panel_key": "p1", "bet_amount": 1000, "client_seed": "seed"},
        headers=player_headers
    )
    assert resp_low.status_code == 400

    # Reset bet limits to default (₹10.00 to ₹50,000.00)
    client.put(
        "/api/v1/admin/aviator-config",
        json={
            "min_crash_multiplier": 1.00,
            "max_crash_multiplier": 1000.00,
            "min_bet_inr": 10.0,
            "max_bet_inr": 50000.0
        },
        headers=admin_headers
    )




