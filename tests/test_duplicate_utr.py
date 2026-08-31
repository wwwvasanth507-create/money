from tests.conftest import get_auth_headers
from app.models.risk_audit import RiskFlag, FlagType

def test_duplicate_utr_prevention_and_risk_flag(client, db, player_user):
    headers = get_auth_headers(player_user)

    # First deposit submission with unique UTR
    res1 = client.post("/api/v1/wallet/deposit", data={
        "utr_number": "DUPLICATE_UTR_12345",
        "amount_inr": "500.00"
    }, headers=headers)
    assert res1.status_code == 200

    # Second deposit submission with duplicate UTR
    res2 = client.post("/api/v1/wallet/deposit", data={
        "utr_number": "DUPLICATE_UTR_12345",
        "amount_inr": "500.00"
    }, headers=headers)
    assert res2.status_code == 400
    assert "already been submitted" in res2.json()["detail"] or "Duplicate UTR" in res2.json()["detail"]

    # Verify anti-fraud RiskFlag was created in DB
    risk_flag = db.query(RiskFlag).filter(
        RiskFlag.user_id == player_user.id,
        RiskFlag.flag_type == FlagType.DUPLICATE_UTR_ATTEMPT.value
    ).first()

    assert risk_flag is not None
    assert risk_flag.severity == "HIGH"
