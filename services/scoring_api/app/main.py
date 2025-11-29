from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
from .schemas import Submission, ScoreResponse, Assessment
import uuid

app = FastAPI(title="PTE Scoring API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory stores for demo / scaffolding. Replace with Postgres/Redis in prod.
ASSESSMENTS: Dict[str, Assessment] = {}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/assessments", response_model=Assessment)
def create_assessment(a: Assessment):
    if a.id is None:
        a.id = str(uuid.uuid4())
    ASSESSMENTS[a.id] = a
    return a


@app.get("/assessments/{assessment_id}", response_model=Assessment)
def get_assessment(assessment_id: str):
    if assessment_id not in ASSESSMENTS:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return ASSESSMENTS[assessment_id]


@app.post("/score", response_model=ScoreResponse)
async def score_submission(sub: Submission):
    # Placeholder scoring logic. Replace with integration to Vercel AI Gateway,
    # Google GenAI, or local Python models. This returns a deterministic demo score.
    # Keep responses small and auditable.
    base = 70
    fluency = min(100, base + len(sub.text or "") % 31)
    pronunciation = min(100, base + (sub.metadata.get("pronunciation_hint", 0) if sub.metadata else 0))
    communicative = min(100, (fluency + pronunciation) // 2)

    result = {
        "scores": {
            "fluency": fluency,
            "pronunciation": pronunciation,
            "communicative": communicative,
        },
        "model": {
            "name": "vercel-ai-gateway-placeholder",
            "notes": "Replace with real model id and response when integrating Vercel AI Gateway v5",
        },
        "raw": {"debug": "synthetic_demo"},
    }

    return ScoreResponse(**result)
