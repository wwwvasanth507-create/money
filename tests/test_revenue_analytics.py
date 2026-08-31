from tests.conftest import get_auth_headers

def test_economics_preview_endpoint(client, super_admin_user):
    headers = get_auth_headers(super_admin_user)
    res = client.get("/api/v1/admin/economics/preview", headers=headers)
    assert res.status_code == 200
    data = res.json()

    assert "total_deposits_paise" in data
    assert "total_withdrawals_paise" in data
    assert "ggr_paise" in data
    assert "ngr_paise" in data
    assert "game_stats" in data
    assert isinstance(data["game_stats"], list)
