"""
Background worker for async scoring jobs (Level 2, Level 4, Level 5).
Runs as: rq worker scoring
"""
import os
import redis
from .core.pte_nlp_scorer import compute_pte_scores
from .adapters import vercel_gateway
from .schemas import Submission
import asyncio


def process_submission(sub_data: dict) -> dict:
    """
    Worker function: process a submission asynchronously.
    
    Steps:
    1. Reconstruct Submission model
    2. Compute NLP scores
    3. Try AI Gateway if available
    4. Aggregate and return
    """
    try:
        sub = Submission(**sub_data)
        text = sub.text or ""
        metadata = sub.metadata or {}
        
        # NLP scores
        nlp_scores = compute_pte_scores(text, metadata)
        
        # AI Gateway (if available)
        vercel_key = os.getenv("VERCEL_AI_GATEWAY_KEY")
        ai_scores = None
        if vercel_key and text:
            try:
                # Run async in a loop
                async def get_ai():
                    return await vercel_gateway.generate(prompt=text, api_key=vercel_key)
                
                ai_response = asyncio.run(get_ai())
                if isinstance(ai_response, dict) and "scores" in ai_response:
                    ai_scores = ai_response["scores"]
            except Exception as e:
                print(f"[Worker] AI Gateway error: {e}")
        
        # Aggregate
        final_scores = nlp_scores.copy()
        if ai_scores:
            for key in nlp_scores:
                if key in ai_scores:
                    final_scores[key] = int(0.5 * nlp_scores[key] + 0.5 * ai_scores[key])
        
        return {
            "status": "completed",
            "scores": final_scores,
            "model": "hybrid_nlp_ai" if ai_scores else "pte_nlp_scorer",
        }
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
        }
