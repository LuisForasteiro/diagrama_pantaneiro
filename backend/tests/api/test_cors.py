from httpx import AsyncClient


async def test_cors_preflight_allows_vite_dev_origin(client: AsyncClient) -> None:
    """CORS preflight (OPTIONS) from the Vite dev server must succeed.

    Before this middleware existed, the browser-originated preflight hit
    a bare FastAPI app and got a 405 Method Not Allowed, which meant the
    real POST /api/auth/register never left the browser. curl-based
    smoke tests did not catch it because curl does not do preflights.
    """
    response = await client.options(
        "/api/auth/register",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "POST" in response.headers["access-control-allow-methods"]


async def test_cors_actual_request_includes_origin_header(client: AsyncClient) -> None:
    """A real POST from the Vite origin should get `access-control-allow-origin` back."""
    response = await client.post(
        "/api/auth/register",
        headers={"Origin": "http://localhost:5173"},
        json={"email": "cors@example.com", "password": "StrongPass!123"},
    )
    assert response.status_code == 201
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


async def test_cors_rejects_unknown_origin(client: AsyncClient) -> None:
    """Origins not on the allowlist must not receive an `allow-origin` header."""
    response = await client.options(
        "/api/auth/register",
        headers={
            "Origin": "http://evil.example.com",
            "Access-Control-Request-Method": "POST",
        },
    )
    # Preflight from unknown origin either fails outright or succeeds without
    # the echo header. Either way, the browser will block.
    assert response.headers.get("access-control-allow-origin") != "http://evil.example.com"
