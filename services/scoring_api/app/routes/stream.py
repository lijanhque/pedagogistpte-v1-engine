"""
Streaming SSE endpoint for real-time scoring updates.
Implements Level 5 streaming with Redis pub/sub and Server-Sent Events.
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import asyncio
import json
import redis
from typing import AsyncGenerator

router = APIRouter()


@router.get("/stream/scoring/{job_id}")
async def stream_scoring_updates(job_id: str) -> StreamingResponse:
    """
    Stream real-time scoring updates via Server-Sent Events.

    Example:
        curl -N "http://localhost:8000/stream/scoring/job-abc123"

    The client will receive events like:
        data: {"type": "job_state_changed", "data": {"state": "processing", ...}}
        data: {"type": "job_enriched", "data": {"enrichment": {...}}}
        data: {"type": "job_completed", "data": {"scores": {...}}}
    """

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events for job updates."""
        redis_conn = redis.from_url("redis://redis:6379/0")
        pubsub = redis_conn.pubsub()
        pubsub.subscribe("scoring_workflow")

        try:
            # Send initial "connection established" event
            yield f"data: {json.dumps({'type': 'connected', 'job_id': job_id})}\n\n"

            for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        event = json.loads(message["data"])
                        # Filter events for this specific job
                        if event.get("data", {}).get("job_id") == job_id:
                            yield f"data: {json.dumps(event)}\n\n"
                    except json.JSONDecodeError:
                        pass

        except asyncio.CancelledError:
            pass
        finally:
            pubsub.close()
            redis_conn.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/stream/scores/{job_id}")
async def stream_final_scores(job_id: str) -> StreamingResponse:
    """
    Stream only the final scoring result once available.
    Polls Redis for job completion.
    """

    async def poll_and_stream() -> AsyncGenerator[str, None]:
        """Poll Redis for job and stream when done."""
        redis_conn = redis.from_url("redis://redis:6379/0")
        import time

        max_wait = 300  # 5 minutes
        start = time.time()

        while time.time() - start < max_wait:
            raw = redis_conn.get(f"job:{job_id}")
            if raw:
                job_data = json.loads(raw)
                if job_data.get("state") == "completed":
                    yield f"data: {json.dumps({'type': 'scores_ready', 'job': job_data})}\n\n"
                    return

            await asyncio.sleep(1)

        # Timeout
        yield f"data: {json.dumps({'type': 'timeout', 'job_id': job_id})}\n\n"
        redis_conn.close()

    return StreamingResponse(poll_and_stream(), media_type="text/event-stream")
