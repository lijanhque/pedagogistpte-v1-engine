import os
import redis
import json
from rq import Queue
from .schemas import Submission
from .core.pte_scorer import PTEScorer
from .core.orchestrator import WorkflowOrchestrator, ScoringState
from .agents.scoring_agent import ScoringAgent


pte_scorer = PTEScorer()
orchestrator = WorkflowOrchestrator(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
scoring_agent = ScoringAgent()


def process_submission(sub_data: dict, use_ai_agent: bool = False) -> dict:
    """
    Synchronous worker entrypoint for RQ.
    
    Scores a submission using the PTE scorer, optionally enriched with AI agent.
    """
    sub = Submission(**sub_data)

    # Score with local PTE scorer
    result = pte_scorer.score(sub.text or "", sub.metadata)

    # Optionally enrich with AI agent
    if use_ai_agent:
        try:
            import asyncio
            from .config.prompts import SCORING_PROMPTS

            prompt = SCORING_PROMPTS["overall_pte_score"].format(text=sub.text or "")

            async def call_agent():
                return await scoring_agent.score_with_fallback(prompt)

            ai_result = asyncio.run(call_agent())
            result["ai_features"] = ai_result
        except Exception as e:
            result["ai_error"] = str(e)

    return result


def process_job(job_id: str) -> dict:
    """
    Worker entrypoint for orchestrated jobs.
    
    Retrieves a job from the orchestrator, scores it, and updates state.
    """
    try:
        job_data = orchestrator.get_job_status(job_id)
        if not job_data:
            return {"error": f"Job {job_id} not found"}

        # Parse metadata
        metadata = json.loads(job_data.get("metadata", "{}"))

        # Score
        result = pte_scorer.score(job_data["text"], metadata)

        # Update orchestrator
        orchestrator.update_job_state(
            job_id,
            ScoringState.SCORED,
            step_name="pte_scoring",
            result=result,
        )

        # Optional: enrich with AI
        try:
            from .config.prompts import SCORING_PROMPTS
            import asyncio

            prompt = SCORING_PROMPTS["overall_pte_score"].format(text=job_data["text"])

            async def call_agent():
                return await scoring_agent.score_with_fallback(prompt)

            ai_result = asyncio.run(call_agent())
            orchestrator.enrich_job_results(job_id, {"ai_insights": ai_result})
            orchestrator.transition_job(job_id, ScoringState.ENRICHED)
        except Exception as e:
            orchestrator.record_error(job_id, f"AI enrichment failed: {str(e)}")

        # Mark completed
        orchestrator.transition_job(job_id, ScoringState.COMPLETED)
        return {"job_id": job_id, "status": "completed", "scores": result["scores"]}

    except Exception as e:
        orchestrator.record_error(job_id, str(e))
        orchestrator.transition_job(job_id, ScoringState.FAILED)
        return {"error": str(e), "job_id": job_id}


if __name__ == "__main__":
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    rconn = redis.from_url(redis_url)
    q = Queue("scoring", connection=rconn)
    print("Worker ready. Use `rq worker scoring` from the app directory.")
