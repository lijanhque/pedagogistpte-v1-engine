"""
Server-Sent Events (SSE) streaming for real-time workflow updates.

Allows clients to subscribe to workflow status changes and receive
updates as they happen during the scoring pipeline.
"""
import asyncio
import json
from typing import AsyncGenerator
from fastapi import HTTPException


class SSEPublisher:
    """Manages SSE subscriptions and broadcasts workflow updates."""

    def __init__(self, redis_conn):
        self.redis = redis_conn
        self.subscribers = {}  # workflow_id -> list of queues

    def subscribe(self, workflow_id: str) -> asyncio.Queue:
        """Subscribe to updates for a workflow."""
        if workflow_id not in self.subscribers:
            self.subscribers[workflow_id] = []
        
        queue = asyncio.Queue()
        self.subscribers[workflow_id].append(queue)
        return queue

    def unsubscribe(self, workflow_id: str, queue: asyncio.Queue):
        """Unsubscribe from workflow updates."""
        if workflow_id in self.subscribers:
            try:
                self.subscribers[workflow_id].remove(queue)
            except ValueError:
                pass

    async def publish(self, workflow_id: str, event: dict):
        """Publish an event to all subscribers."""
        if workflow_id in self.subscribers:
            for queue in self.subscribers[workflow_id]:
                try:
                    await queue.put(event)
                except asyncio.QueueFull:
                    pass

    async def stream_updates(self, workflow_id: str) -> AsyncGenerator[str, None]:
        """Stream updates as SSE data.
        
        Usage in FastAPI:
            @app.get("/score/{workflow_id}/stream")
            async def stream_scores(workflow_id: str):
                return StreamingResponse(
                    sse_publisher.stream_updates(workflow_id),
                    media_type="text/event-stream"
                )
        """
        queue = self.subscribe(workflow_id)
        try:
            while True:
                # Wait for an update or timeout after 30 seconds
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                except asyncio.TimeoutError:
                    # Send a keepalive comment
                    yield ": keepalive\n\n"
                    continue
                
                # Format as SSE
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            self.unsubscribe(workflow_id, queue)


# Global instance (in production, inject via dependency)
_sse_publisher = None


def get_sse_publisher(redis_conn=None) -> SSEPublisher:
    """Get or create the SSE publisher singleton."""
    global _sse_publisher
    if _sse_publisher is None and redis_conn:
        _sse_publisher = SSEPublisher(redis_conn)
    return _sse_publisher
