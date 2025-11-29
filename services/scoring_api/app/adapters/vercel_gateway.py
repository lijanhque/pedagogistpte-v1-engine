import httpx
from typing import Any, Dict, Optional


async def generate(prompt: str, api_key: str, model: Optional[str] = None) -> Any:
    """
    Call Vercel AI Gateway to generate a response for `prompt`.

    Note: Vercel's API surface can change. This adapter uses a conservative
    REST call with a JSON payload and `Authorization: Bearer <key>` header.
    Replace the `endpoint` with the correct Vercel Gateway path for your
    account / project if different.
    """
    endpoint = "https://api.vercel.ai/v1/generate"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload: Dict[str, Any] = {"input": prompt}
    if model:
        payload["model"] = model

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.post(endpoint, json=payload, headers=headers)
        r.raise_for_status()
        # Try to decode JSON; if not JSON, return raw text
        try:
            return r.json()
        except Exception:
            return {"text": r.text}
