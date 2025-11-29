import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_health():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_score_endpoint():
    payload = {"text": "This is a short response for testing.", "metadata": {}}
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/score", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert "scores" in body
    assert "model" in body
