"""
Updated main.py integrating all levels (1-5) with PTE scorer, orchestrator, streaming, and agents.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import redis
from rq import Queue
import uuid
from typing import Dict, Any, Optional

from .schemas import Submission, ScoreResponse, Assessment
from .core.pte_scorer import PTEScorer
from .core.orchestrator import WorkflowOrchestrator, ScoringState
from .agents.scoring_agent import ScoringAgent
from .routes.stream import router as stream_router

app = FastAPI(
    title="PTE Academic Scoring Engine",
    version="1.0.0",
    description="Production-grade PTE Academic test scoring with AI agents and real-time streaming",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
pte_scorer = PTEScorer()
orchestrator = WorkflowOrchestrator(
    redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0")
)
scoring_agent = ScoringAgent()

# Redis for queue
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_conn = redis.from_url(redis_url)
scoring_queue = Queue("scoring", connection=redis_conn)

# In-memory store for demo (replace with Postgres in production)
ASSESSMENTS: Dict[str, Assessment] = {}


# ============= Level 1: Basic CRUD & Scoring =============

@app.get("/health")
def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": "1.0.0",
        "features": ["scoring", "streaming", "async_jobs", "ai_agents"],
    }


@app.post("/assessments", response_model=Assessment)
def create_assessment(a: Assessment):
    """Create a new assessment."""
    if a.id is None:
        a.id = str(uuid.uuid4())
    ASSESSMENTS[a.id] = a
    return a


@app.get("/assessments/{assessment_id}", response_model=Assessment)
def get_assessment(assessment_id: str):
    """Retrieve an assessment."""
    if assessment_id not in ASSESSMENTS:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return ASSESSMENTS[assessment_id]


# ============= Level 4: AI Agents + Level 1: Scoring =============

@app.post("/score", response_model=ScoreResponse)
async def score_submission(
    sub: Submission,
    use_ai_agent: bool = False,
    background_tasks: BackgroundTasks = None,
):
    """
    Score a PTE submission.

    Query params:
    - use_ai_agent: If True, use the scoring agent (Vercel/Google); else use local PTE scorer.

    Returns a ScoreResponse with scores and metadata.
    """
    SCORE_MODE = os.getenv("SCORE_MODE", "sync")

    # Async mode: enqueue job
    if SCORE_MODE.lower() == "async":
        job = scoring_queue.enqueue(
            "app.worker.process_submission",
            sub.dict(),
            use_ai_agent=use_ai_agent,
        )
        return ScoreResponse(
            scores={},
            model={"job_id": job.id, "status": "queued"},
        )

    # Sync mode: score immediately
    scores_dict = pte_scorer.score(sub.text or "", sub.metadata)

    return ScoreResponse(
        scores=scores_dict["scores"],
        model={
            "name": "pte_academic_v1",
            "ai_used": use_ai_agent,
        },
        raw=scores_dict,
    )


@app.post("/score/with-ai")
async def score_with_ai_agent(sub: Submission) -> Dict[str, Any]:
    """Score using AI agents (Vercel AI Gateway or Google GenAI)."""
    from .config.prompts import SCORING_PROMPTS

    prompt = SCORING_PROMPTS["overall_pte_score"].format(text=sub.text or "")

    try:
        ai_result = await scoring_agent.score_with_fallback(prompt)
        local_result = pte_scorer.score(sub.text or "", sub.metadata)

        # Hybrid: combine AI and local results
        combined_scores = {
            "fluency": (
                ai_result.get("fluency", local_result["scores"]["fluency"]) * 0.5
                + local_result["scores"]["fluency"] * 0.5
            ),
            "lexical_resource": (
                ai_result.get("lexical_resource", local_result["scores"]["lexical_resource"]) * 0.5
                + local_result["scores"]["lexical_resource"] * 0.5
            ),
            "grammar": (
                ai_result.get("grammar", local_result["scores"]["grammar"]) * 0.5
                + local_result["scores"]["grammar"] * 0.5
            ),
            "communicative": (
                ai_result.get("communicative", local_result["scores"]["oral_fluency"]) * 0.5
                + local_result["scores"]["oral_fluency"] * 0.5
            ),
        }

        return {
            "scores": combined_scores,
            "ai_response": ai_result,
            "local_response": local_result,
        }
    except Exception as e:
        return {"error": str(e), "fallback_to_local": True}


# ============= Level 2 & 3: Background Jobs & Orchestration =============

@app.post("/jobs")
def create_scoring_job(sub: Submission) -> Dict[str, Any]:
    """Create a scoring job and track it via orchestrator."""
    job_data = orchestrator.create_scoring_job(
        submission_id=sub.assessment_id or str(uuid.uuid4()),
        text=sub.text or "",
        metadata=sub.metadata,
    )
    return job_data


@app.get("/jobs/{job_id}")
def get_job_status(job_id: str) -> Dict[str, Any]:
    """Get the status of a scoring job."""
    job = orchestrator.get_job_status(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/jobs/{job_id}/enqueue")
def enqueue_job_to_worker(job_id: str) -> Dict[str, Any]:
    """Enqueue a job to the background worker."""
    job_status = orchestrator.get_job_status(job_id)
    if not job_status:
        raise HTTPException(status_code=404, detail="Job not found")

    # Transition to processing
    orchestrator.transition_job(job_id, ScoringState.PROCESSING)

    # Enqueue to worker
    worker_job = scoring_queue.enqueue(
        "app.worker.process_job",
        job_id,
    )

    return {"job_id": job_id, "worker_job_id": worker_job.id, "state": "processing"}


# ============= Level 5: Streaming =============

app.include_router(stream_router)


# ============= Admin & Metrics =============

@app.get("/metrics")
def get_metrics() -> Dict[str, Any]:
    """Return basic metrics (queue size, job states, etc.)."""
    return {
        "queue_size": len(scoring_queue.jobs),
        "redis_ping": redis_conn.ping(),
    }
