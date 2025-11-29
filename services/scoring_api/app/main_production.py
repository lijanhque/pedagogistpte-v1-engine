"""
PTE Academic Scoring Engine - Main API
Levels 1-5 integrated:
- Level 1: CRUD + scoring endpoints
- Level 2: Background jobs (RQ + cron)
- Level 3: Workflow orchestrator (Redis state + audit logs)
- Level 4: AI agents (Vercel Gateway, Google GenAI)
- Level 5: Streaming (SSE/WebSocket via Redis pub/sub)
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import Dict, Optional
import os
import redis
from rq import Queue
import uuid
import asyncio

from .schemas import Submission, ScoreResponse, Assessment
from .core.pte_nlp_scorer import compute_pte_scores
from .core.workflow_orchestrator import ScoringWorkflow, WorkflowStatus
from .streaming.sse import get_sse_publisher
from .adapters import vercel_gateway

app = FastAPI(
    title="PTE Academic Scoring Engine",
    version="1.0.0",
    description="Production backend for PTE Academic test scoring"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Redis and orchestration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
redis_conn = redis.from_url(REDIS_URL)
scoring_queue = Queue("scoring", connection=redis_conn)
orchestrator = ScoringWorkflow(redis_conn)
sse_publisher = get_sse_publisher(redis_conn)

# In-memory assessments store (replace with Postgres in production)
ASSESSMENTS: Dict[str, Assessment] = {}


# ============= Level 1: Health & CRUD Endpoints =============

@app.get("/health")
def health():
    """Health check with feature flags."""
    return {
        "status": "ok",
        "version": "1.0.0",
        "features": {
            "crud": True,
            "sync_scoring": True,
            "async_scoring": True,
            "ai_agents": True,
            "streaming": True,
        }
    }


@app.post("/assessments", response_model=Assessment)
def create_assessment(assessment: Assessment):
    """Create a new assessment."""
    if assessment.id is None:
        assessment.id = str(uuid.uuid4())
    ASSESSMENTS[assessment.id] = assessment
    return assessment


@app.get("/assessments/{assessment_id}", response_model=Assessment)
def get_assessment(assessment_id: str):
    """Retrieve an assessment."""
    if assessment_id not in ASSESSMENTS:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return ASSESSMENTS[assessment_id]


# ============= Level 1-4: Scoring Endpoints =============

@app.post("/score", response_model=ScoreResponse)
async def score_submission(sub: Submission):
    """
    Score a PTE submission using local NLP + optional AI Gateway.
    
    Flow:
    1. Compute PTE scores using NLP (fluency, pronunciation, lexical, grammar)
    2. If VERCEL_AI_GATEWAY_KEY is set, also fetch AI scores
    3. Aggregate and return
    
    Optional query: ?async=true to enqueue instead of scoring synchronously.
    """
    SCORE_MODE = os.getenv("SCORE_MODE", "sync")
    
    if SCORE_MODE.lower() == "async":
        # Enqueue the job
        job = scoring_queue.enqueue("app.worker.process_submission", sub.dict())
        return ScoreResponse(
            scores={},
            model={"job_id": job.id, "status": "queued"}
        )
    
    # Synchronous scoring
    text = sub.text or ""
    metadata = sub.metadata or {}
    
    # Step 1: Compute NLP scores
    nlp_scores = compute_pte_scores(text, metadata)
    
    # Step 2: Try AI Gateway if key present
    vercel_key = os.getenv("VERCEL_AI_GATEWAY_KEY")
    ai_scores = None
    if vercel_key and text:
        try:
            ai_response = await vercel_gateway.generate(prompt=text, api_key=vercel_key)
            # Parse AI response (placeholder: extract numeric scores if available)
            if isinstance(ai_response, dict) and "scores" in ai_response:
                ai_scores = ai_response["scores"]
        except Exception as e:
            # Log and continue with NLP scores only
            print(f"AI Gateway error: {e}")
    
    # Step 3: Aggregate
    final_scores = nlp_scores
    if ai_scores:
        # Simple average
        for key in nlp_scores:
            if key in ai_scores:
                final_scores[key] = int(0.5 * nlp_scores[key] + 0.5 * ai_scores[key])
    
    return ScoreResponse(
        scores=final_scores,
        model={"name": "pte_nlp_solver" if not ai_scores else "hybrid_nlp_ai"}
    )


@app.post("/score_async", response_model=Dict)
async def score_submission_enqueue(sub: Submission):
    """
    Level 2: Enqueue a scoring job and return immediately with job_id.
    Client polls /job/{job_id} to get the result.
    """
    job = scoring_queue.enqueue("app.worker.process_submission", sub.dict())
    return {"job_id": job.id, "status": "queued"}


@app.get("/job/{job_id}")
async def get_job_status(job_id: str):
    """Get the result of an async scoring job."""
    job = scoring_queue.fetch_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "job_id": job_id,
        "status": job.get_status(),
        "result": job.result if job.is_finished else None,
        "error": str(job.exc_info) if job.is_failed else None,
    }


# ============= Level 3: Workflow Orchestration =============

@app.post("/workflow/create")
async def create_workflow(assessment_id: str, submission: Submission):
    """Create a new scoring workflow (orchestrator)."""
    workflow_id = orchestrator.create_workflow(assessment_id, submission.dict())
    return {"workflow_id": workflow_id, "status": "created"}


@app.get("/workflow/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Retrieve workflow state."""
    state = orchestrator.get_workflow(workflow_id)
    if not state:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return state


# ============= Level 5: Streaming with SSE =============

@app.get("/workflow/{workflow_id}/stream")
async def stream_workflow_updates(workflow_id: str):
    """
    Stream real-time workflow updates via Server-Sent Events (SSE).
    
    Usage (browser):
        const eventSource = new EventSource(`/workflow/{id}/stream`);
        eventSource.onmessage = (e) => console.log(JSON.parse(e.data));
    """
    # Verify workflow exists
    state = orchestrator.get_workflow(workflow_id)
    if not state:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return StreamingResponse(
        sse_publisher.stream_updates(workflow_id),
        media_type="text/event-stream"
    )


# ============= Level 2: Batch & Cron Operations =============

@app.post("/batch_score")
async def batch_score(submissions: list[Submission]):
    """
    Enqueue multiple submissions for batch scoring.
    Returns list of job IDs.
    """
    job_ids = []
    for sub in submissions:
        job = scoring_queue.enqueue("app.worker.process_submission", sub.dict())
        job_ids.append(job.id)
    
    return {"job_ids": job_ids, "count": len(job_ids)}


@app.get("/metrics")
async def get_metrics():
    """Return operational metrics."""
    queue_count = len(scoring_queue)
    return {
        "queue_size": queue_count,
        "redis_url": os.getenv("REDIS_URL"),
        "score_mode": os.getenv("SCORE_MODE", "sync"),
    }
