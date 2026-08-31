def test_html_page_routes(client):
    routes = [
        "/login",
        "/register",
        "/dashboard",
        "/games/crash",
        "/games/mines",
        "/games/dice",
        "/wallet",
        "/kyc",
        "/admin/verification-desk",
        "/admin/dashboard"
    ]
    for route in routes:
        response = client.get(route)
        assert response.status_code == 200, f"Route {route} failed with status {response.status_code}"
