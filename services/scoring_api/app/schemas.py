from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class Assessment(BaseModel):
    id: Optional[str] = None
    student_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class Submission(BaseModel):
    assessment_id: Optional[str] = None
    student_id: Optional[str] = None
    text: Optional[str] = None
    audio_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ScoreResponse(BaseModel):
    scores: Dict[str, int]
    model: Dict[str, Any]
    raw: Optional[Dict[str, Any]] = None
