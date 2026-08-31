def test_html_page_routes(client):
    routes = [
        "/login",
        "/register",
        "/dashboard",
        "/games/crash",
        "/games/mines",
        "/wallet",
        "/kyc",
        "/admin/verification-desk",
        "/admin/dashboard"
    ]
    for route in routes:
        response = client.get(route)
        assert response.status_code == 200, f"Route {route} failed with status {response.status_code}"

    # Verify Dice game route redirects to dashboard
    dice_resp = client.get("/games/dice", follow_redirects=False)
    assert dice_resp.status_code in [303, 307, 302]

