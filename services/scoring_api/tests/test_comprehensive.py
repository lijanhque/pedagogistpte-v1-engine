"""
Comprehensive test suite for PTE Scoring Engine.
Run with: pytest tests/
"""
import pytest
from httpx import AsyncClient
from app.main_v2 import app
from app.core.pte_nlp_scorer import compute_pte_scores
from app.schemas import Submission


@pytest.mark.asyncio
class TestHealth:
    async def test_health_endpoint(self):
        """Test health check."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            r = await ac.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert "features" in body


class TestNLPScorer:
    """Test the local NLP PTE scorer."""

    def test_score_empty_text(self):
        """Empty text should score low."""
        scores = compute_pte_scores("")
        assert scores["overall"] <= 20

    def test_score_short_response(self):
        """Short response (< 5 words) scores low on fluency."""
        scores = compute_pte_scores("Good test.")
        assert scores["fluency"] < 50

    def test_score_long_fluent_response(self):
        """Long, coherent response scores high."""
        text = "The rapid development of technology has significantly changed our daily lives. " \
               "Artificial intelligence, machine learning, and blockchain are revolutionizing industries. " \
               "These advancements offer tremendous opportunities but also present challenges we must address."
        scores = compute_pte_scores(text)
        
        # All scores should be reasonable
        for key in ["fluency", "pronunciation", "lexical_range", "grammar", "overall"]:
            assert 30 <= scores[key] <= 90, f"{key} out of range: {scores[key]}"

    def test_score_with_metadata(self):
        """Scores should incorporate metadata hints."""
        text = "The advanced international telecommunications infrastructure enables seamless global communication."
        metadata = {"clarity_rating": 10}
        scores_with_hint = compute_pte_scores(text, metadata)
        
        # Pronunciation should be higher with clarity hint
        assert scores_with_hint["pronunciation"] >= 60

    def test_score_consistency(self):
        """Same input should produce same output."""
        text = "Consistent scoring is crucial for standardized testing."
        scores1 = compute_pte_scores(text)
        scores2 = compute_pte_scores(text)
        
        assert scores1 == scores2


@pytest.mark.asyncio
class TestScoringEndpoint:
    """Test the /score endpoint."""

    async def test_score_sync_basic(self):
        """Test basic sync scoring."""
        payload = {
            "text": "The examination system has evolved considerably over the past decade.",
            "metadata": {}
        }
        async with AsyncClient(app=app, base_url="http://test") as ac:
            r = await ac.post("/score", json=payload)
        
        assert r.status_code == 200
        body = r.json()
        assert "scores" in body
        assert "model" in body
        assert "overall" in body["scores"]

    async def test_score_with_metadata(self):
        """Test scoring with metadata."""
        payload = {
            "text": "Advanced linguistic proficiency is demonstrated through sophisticated vocabulary usage.",
            "metadata": {"clarity_rating": 8}
        }
        async with AsyncClient(app=app, base_url="http://test") as ac:
            r = await ac.post("/score", json=payload)
        
        assert r.status_code == 200
        body = r.json()
        assert 20 <= body["scores"]["pronunciation"] <= 90

    async def test_score_empty_submission(self):
        """Empty submission should not error."""
        payload = {"text": "", "metadata": {}}
        async with AsyncClient(app=app, base_url="http://test") as ac:
            r = await ac.post("/score", json=payload)
        
        assert r.status_code == 200
        body = r.json()
        assert body["scores"]["overall"] < 30


@pytest.mark.asyncio
class TestAssessmentsCRUD:
    """Test assessment CRUD operations."""

    async def test_create_assessment(self):
        """Create a new assessment."""
        from app.schemas import Assessment
        payload = {
            "student_id": "STU-001",
            "metadata": {"test_type": "speaking"}
        }
        async with AsyncClient(app=app, base_url="http://test") as ac:
            r = await ac.post("/assessments", json=payload)
        
        assert r.status_code == 200
        body = r.json()
        assert body["student_id"] == "STU-001"
        assert body["id"] is not None
        return body["id"]

    async def test_get_assessment(self):
        """Retrieve an assessment."""
        # First create one
        payload = {
            "student_id": "STU-002",
            "metadata": {"test_type": "writing"}
        }
        async with AsyncClient(app=app, base_url="http://test") as ac:
            r1 = await ac.post("/assessments", json=payload)
            assessment_id = r1.json()["id"]
            
            # Now fetch it
            r2 = await ac.get(f"/assessments/{assessment_id}")
        
        assert r2.status_code == 200
        body = r2.json()
        assert body["id"] == assessment_id

    async def test_get_nonexistent_assessment(self):
        """Fetching non-existent assessment should 404."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            r = await ac.get("/assessments/nonexistent-id")
        
        assert r.status_code == 404


@pytest.mark.asyncio
class TestAsync:
    """Test async job endpoints."""

    async def test_enqueue_job(self):
        """Enqueue a scoring job."""
        payload = {"text": "Asynchronous scoring job test submission."}
        async with AsyncClient(app=app, base_url="http://test") as ac:
            r = await ac.post("/score_async", json=payload)
        
        assert r.status_code == 200
        body = r.json()
        assert "job_id" in body
        assert body["status"] == "queued"

    async def test_batch_score(self):
        """Test batch scoring."""
        payloads = [
            {"text": "Batch submission 1."},
            {"text": "Batch submission 2."},
        ]
        async with AsyncClient(app=app, base_url="http://test") as ac:
            r = await ac.post("/batch_score", json=payloads)
        
        assert r.status_code == 200
        body = r.json()
        assert body["count"] == 2
        assert len(body["job_ids"]) == 2


@pytest.mark.asyncio
class TestWorkflow:
    """Test workflow orchestration."""

    async def test_create_workflow(self):
        """Create a workflow."""
        payload = {
            "assessment_id": "ASSESS-001",
            "submission": {
                "text": "Workflow test response for PTE."
            }
        }
        async with AsyncClient(app=app, base_url="http://test") as ac:
            r = await ac.post("/workflow/create", json=payload)
        
        assert r.status_code == 200
        body = r.json()
        assert "workflow_id" in body
        return body["workflow_id"]

    async def test_get_workflow(self):
        """Retrieve workflow state."""
        # Create one first
        payload = {
            "assessment_id": "ASSESS-002",
            "submission": {"text": "Get workflow test."}
        }
        async with AsyncClient(app=app, base_url="http://test") as ac:
            r1 = await ac.post("/workflow/create", json=payload)
            workflow_id = r1.json()["workflow_id"]
            
            # Fetch it
            r2 = await ac.get(f"/workflow/{workflow_id}")
        
        assert r2.status_code == 200
        body = r2.json()
        assert body["workflow_id"] == workflow_id


@pytest.mark.asyncio
class TestMetrics:
    """Test metrics endpoint."""

    async def test_get_metrics(self):
        """Fetch metrics."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            r = await ac.get("/metrics")
        
        assert r.status_code == 200
        body = r.json()
        assert "queue_size" in body
        assert "score_mode" in body


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
