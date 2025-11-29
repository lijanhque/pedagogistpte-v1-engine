"""
Orchestrator for multi-step scoring workflows with state machine and Redis pub/sub.
Implements Level 3 centralized workflow management.
"""

import json
import redis
import enum
from typing import Dict, Any, Optional
from datetime import datetime
import uuid


class ScoringState(enum.Enum):
    """Scoring workflow states."""
    PENDING = "pending"
    PROCESSING = "processing"
    SCORED = "scored"
    ENRICHED = "enriched"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowOrchestrator:
    """Centralized orchestrator for scoring workflows with Redis state store."""

    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self.conn = redis.from_url(redis_url)
        self.pubsub_channel = "scoring_workflow"

    def create_scoring_job(
        self,
        submission_id: str,
        text: str,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Create a new scoring job and track it."""
        job_id = str(uuid.uuid4())
        metadata = metadata or {}

        job_data = {
            "job_id": job_id,
            "submission_id": submission_id,
            "text": text,
            "metadata": json.dumps(metadata),
            "state": ScoringState.PENDING.value,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "steps_completed": [],
            "results": {},
            "errors": [],
        }

        # Store in Redis (key expires in 7 days)
        self.conn.setex(
            f"job:{job_id}",
            7 * 24 * 3600,
            json.dumps(job_data),
        )

        # Publish job created event
        self._publish_event("job_created", job_data)
        return job_data

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve job status from Redis."""
        raw = self.conn.get(f"job:{job_id}")
        if raw:
            return json.loads(raw)
        return None

    def update_job_state(
        self,
        job_id: str,
        state: ScoringState,
        step_name: str = None,
        result: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Update job state and track completed steps."""
        job = self.get_job_status(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        job["state"] = state.value
        job["updated_at"] = datetime.utcnow().isoformat()

        if step_name:
            job["steps_completed"].append(step_name)
            if result:
                job["results"][step_name] = result

        # Save back to Redis
        self.conn.setex(
            f"job:{job_id}",
            7 * 24 * 3600,
            json.dumps(job),
        )

        # Publish state change event
        self._publish_event("job_state_changed", {
            "job_id": job_id,
            "state": state.value,
            "step": step_name,
        })

        return job

    def transition_job(self, job_id: str, next_state: ScoringState) -> Dict[str, Any]:
        """Safely transition job to next state."""
        job = self.get_job_status(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        current_state = ScoringState(job["state"])

        # Define allowed transitions
        allowed = {
            ScoringState.PENDING: [ScoringState.PROCESSING, ScoringState.FAILED],
            ScoringState.PROCESSING: [ScoringState.SCORED, ScoringState.FAILED],
            ScoringState.SCORED: [ScoringState.ENRICHED, ScoringState.COMPLETED],
            ScoringState.ENRICHED: [ScoringState.COMPLETED, ScoringState.FAILED],
            ScoringState.COMPLETED: [],
            ScoringState.FAILED: [],
        }

        if next_state not in allowed.get(current_state, []):
            raise ValueError(
                f"Cannot transition from {current_state.value} to {next_state.value}"
            )

        return self.update_job_state(job_id, next_state)

    def enrich_job_results(self, job_id: str, enrichment: Dict[str, Any]) -> Dict[str, Any]:
        """Add enrichment data (e.g., model insights, flags) to job results."""
        job = self.get_job_status(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        if "enrichment" not in job["results"]:
            job["results"]["enrichment"] = {}

        job["results"]["enrichment"].update(enrichment)

        # Save back
        self.conn.setex(
            f"job:{job_id}",
            7 * 24 * 3600,
            json.dumps(job),
        )

        self._publish_event("job_enriched", {"job_id": job_id, "enrichment": enrichment})
        return job

    def record_error(self, job_id: str, error: str) -> Dict[str, Any]:
        """Record an error for a job."""
        job = self.get_job_status(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        job["errors"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "message": error,
        })

        # Save back
        self.conn.setex(
            f"job:{job_id}",
            7 * 24 * 3600,
            json.dumps(job),
        )

        return job

    def subscribe_to_events(self, callback):
        """Subscribe to workflow events (for real-time UI updates)."""
        pubsub = self.conn.pubsub()
        pubsub.subscribe(self.pubsub_channel)

        try:
            for message in pubsub.listen():
                if message["type"] == "message":
                    callback(json.loads(message["data"]))
        finally:
            pubsub.close()

    def _publish_event(self, event_type: str, data: Dict[str, Any]):
        """Publish an event to Redis pub/sub."""
        event = {"type": event_type, "data": data, "timestamp": datetime.utcnow().isoformat()}
        self.conn.publish(self.pubsub_channel, json.dumps(event))
