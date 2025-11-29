"""
Integration tests for PTE Scoring Engine covering all levels.
"""

import pytest
from httpx import AsyncClient
import json
from app.main import app
from app.core.pte_scorer import PTEScorer


@pytest.mark.asyncio
async def test_health():
    """Test health check endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "features" in data


@pytest.mark.asyncio
async def test_score_endpoint_sync():
    """Test synchronous scoring with local PTE scorer."""
    payload = {
        "text": "The technological revolution has dramatically transformed our society in ways previously unimaginable. From artificial intelligence to biotechnology, innovations continually reshape how we communicate, work, and live. These advancements present both unprecedented opportunities and significant challenges that require careful consideration.",
        "metadata": {"submission_type": "speaking"},
    }
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/score", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert "scores" in body
    assert "model" in body
    assert "fluency" in body["scores"]
    assert "lexical_resource" in body["scores"]
    assert "grammar" in body["scores"]


@pytest.mark.asyncio
async def test_create_assessment():
    """Test assessment creation (Level 1)."""
    payload = {
        "student_id": "test_student_123",
        "metadata": {"course": "PTE Academic"},
    }
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/assessments", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["student_id"] == "test_student_123"
    assert body["id"] is not None


@pytest.mark.asyncio
async def test_get_assessment():
    """Test assessment retrieval (Level 1)."""
    # Create first
    create_payload = {"student_id": "test_student_456"}
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r_create = await ac.post("/assessments", json=create_payload)
        assessment_id = r_create.json()["id"]
        
        # Retrieve
        r_get = await ac.get(f"/assessments/{assessment_id}")
    assert r_get.status_code == 200


@pytest.mark.asyncio
async def test_create_scoring_job():
    """Test job creation (Level 2/3)."""
    payload = {
        "assessment_id": "test_assess_789",
        "text": "This is a test submission for scoring.",
        "metadata": {"duration": 60},
    }
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/jobs", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert "job_id" in body
    assert body["state"] == "pending"


@pytest.mark.asyncio
async def test_metrics_endpoint():
    """Test metrics endpoint."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.get("/metrics")
    assert r.status_code == 200
    body = r.json()
    assert "queue_size" in body


def test_pte_scorer_fluency():
    """Test PTE scorer fluency calculation."""
    scorer = PTEScorer()
    text = "The rapid advancement of technology has revolutionized modern society. Innovations in artificial intelligence, biotechnology, and renewable energy continue to shape our future in unprecedented ways. These developments present both significant opportunities and considerable challenges that society must address thoughtfully."
    
    result = scorer.score(text)
    assert "scores" in result
    assert "fluency" in result["scores"]
    assert result["scores"]["fluency"] > 0
    assert result["scores"]["fluency"] <= 100


def test_pte_scorer_lexical():
    """Test PTE scorer lexical resource calculation."""
    scorer = PTEScorer()
    text = "The ubiquitous implementation of machine learning algorithms has engendered profound amelioration in computational efficiency, demonstrating perspicacious architectural delineation."
    
    result = scorer.score(text)
    assert result["scores"]["lexical_resource"] > 50  # Advanced vocabulary


def test_pte_scorer_grammar():
    """Test PTE scorer grammar assessment."""
    scorer = PTEScorer()
    text = "She don't like apples. He are going. To do thinking."
    
    result = scorer.score(text)
    # Grammar errors present, score should be lower
    assert result["scores"]["grammar"] < 70


def test_pte_scorer_band_calibration():
    """Test PTE band calibration (10-90)."""
    scorer = PTEScorer()
    
    # Test band boundaries
    band = scorer._calibrate_to_band(100)
    assert band == 90  # Max
    
    band = scorer._calibrate_to_band(0)
    assert band == 10  # Min
    
    band = scorer._calibrate_to_band(50)
    assert band == 50  # Mid


def test_pte_scorer_section_score():
    """Test mapping PTE band to section score (0-90)."""
    scorer = PTEScorer()
    
    section = scorer._band_to_section_score(90)
    assert section == 90
    
    section = scorer._band_to_section_score(10)
    assert section == 0
