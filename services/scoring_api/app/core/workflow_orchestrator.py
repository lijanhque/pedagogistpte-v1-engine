"""
Workflow orchestrator for PTE scoring pipelines.

Manages multi-step scoring workflows:
1. Text ingestion & validation
2. NLP scoring (fluency, pronunciation, lexical, grammar)
3. AI Gateway scoring (Vercel AI, Google GenAI)
4. Result aggregation & audit log storage
5. Real-time updates via SSE/WebSocket

Uses Redis for state and Postgres for durable logs.
"""
import json
import uuid
from typing import Dict, Any, Optional
from enum import Enum
from datetime import datetime


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ScoringWorkflow:
    """Orchestrates a multi-step scoring workflow."""

    def __init__(self, redis_conn, db_conn=None):
        self.redis = redis_conn
        self.db = db_conn
        self.workflow_key_prefix = "workflow:"

    def create_workflow(self, assessment_id: str, submission_data: Dict[str, Any]) -> str:
        """Create a new workflow instance and return workflow_id."""
        workflow_id = str(uuid.uuid4())
        workflow_state = {
            "workflow_id": workflow_id,
            "assessment_id": assessment_id,
            "status": WorkflowStatus.PENDING.value,
            "submission": submission_data,
            "scores": {},
            "errors": [],
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        key = f"{self.workflow_key_prefix}{workflow_id}"
        self.redis.setex(key, 86400, json.dumps(workflow_state))  # 24hr TTL
        return workflow_id

    def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve workflow state from Redis."""
        key = f"{self.workflow_key_prefix}{workflow_id}"
        data = self.redis.get(key)
        if data:
            return json.loads(data)
        return None

    def update_workflow_status(self, workflow_id: str, status: WorkflowStatus, data: Dict[str, Any] = None):
        """Update workflow status and optionally merge in scores/errors."""
        key = f"{self.workflow_key_prefix}{workflow_id}"
        state = self.get_workflow(workflow_id)
        if not state:
            return
        
        state["status"] = status.value
        state["updated_at"] = datetime.utcnow().isoformat()
        if data:
            state.update(data)
        
        self.redis.setex(key, 86400, json.dumps(state))
        
        # Publish to SSE subscribers if available
        self._publish_update(workflow_id, state)

    def _publish_update(self, workflow_id: str, state: Dict[str, Any]):
        """Publish workflow state update to Redis pub/sub for SSE streaming."""
        channel = f"workflow_updates:{workflow_id}"
        self.redis.publish(channel, json.dumps(state))

    def store_audit_log(self, workflow_id: str, step: str, result: Dict[str, Any]):
        """Store workflow step results in Postgres (if DB connection available)."""
        if self.db:
            # This would be executed as a real INSERT into audit_logs table
            # For now, just log the structure
            audit_entry = {
                "workflow_id": workflow_id,
                "step": step,
                "result": result,
                "timestamp": datetime.utcnow().isoformat(),
            }
            # In production: self.db.execute(INSERT INTO audit_logs ...)
            print(f"[AUDIT] {audit_entry}")

    def aggregate_scores(self, nlp_scores: Dict[str, int], ai_scores: Dict[str, int] = None) -> Dict[str, int]:
        """Aggregate scores from NLP and AI sources.
        
        Weights:
        - NLP scores: 50%
        - AI Gateway scores: 50% (if available)
        """
        if not ai_scores:
            return nlp_scores
        
        # Simple weighted average if both exist
        aggregated = {}
        for key in nlp_scores:
            if key in ai_scores:
                aggregated[key] = int(0.5 * nlp_scores[key] + 0.5 * ai_scores[key])
            else:
                aggregated[key] = nlp_scores[key]
        
        return aggregated
