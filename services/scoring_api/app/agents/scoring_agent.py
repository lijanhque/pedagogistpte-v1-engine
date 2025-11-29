"""
Agent module integrating Vercel AI Gateway, Google GenAI, and local NLP.
"""

import json
import os
from typing import Dict, Any, Optional
import httpx


class ScoringAgent:
    """Multi-model scoring agent with fallback strategy."""

    def __init__(
        self,
        vercel_key: Optional[str] = None,
        google_key: Optional[str] = None,
        enable_local_fallback: bool = True,
    ):
        self.vercel_key = vercel_key or os.getenv("VERCEL_AI_GATEWAY_KEY")
        self.google_key = google_key or os.getenv("GOOGLE_GENAI_KEY")
        self.enable_local_fallback = enable_local_fallback

    async def score_with_gateway(
        self,
        prompt: str,
        model: str = "gpt-4",
    ) -> Dict[str, Any]:
        """Call Vercel AI Gateway for scoring."""
        if not self.vercel_key:
            raise ValueError("VERCEL_AI_GATEWAY_KEY not set")

        headers = {
            "Authorization": f"Bearer {self.vercel_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 500,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                resp = await client.post(
                    "https://api.vercel.ai/v1/chat/completions",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()

                # Extract text from response
                if "choices" in data and len(data["choices"]) > 0:
                    text = data["choices"][0].get("message", {}).get("content", "")
                    # Try to parse as JSON
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        return {"raw_response": text}

                return {"error": "No response from gateway"}
            except Exception as e:
                return {"error": str(e)}

    async def score_with_google_genai(
        self,
        prompt: str,
        model: str = "gemini-pro",
    ) -> Dict[str, Any]:
        """Call Google GenAI for scoring."""
        if not self.google_key:
            raise ValueError("GOOGLE_GENAI_KEY not set")

        # Using Google's generativeai SDK pattern
        # In production, install: pip install google-generativeai
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.google_key)
            model_obj = genai.GenerativeModel(model)
            response = model_obj.generate_content(prompt)
            text = response.text

            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"raw_response": text}
        except ImportError:
            return {"error": "google-generativeai not installed"}
        except Exception as e:
            return {"error": str(e)}

    async def score_with_fallback(
        self,
        prompt: str,
        preferred_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Score with fallback: Vercel → Google → Local."""
        # Try Vercel first
        if self.vercel_key:
            result = await self.score_with_gateway(prompt, model=preferred_model or "gpt-4")
            if "error" not in result or result.get("error") is None:
                return {**result, "model_used": "vercel_gateway"}

        # Try Google
        if self.google_key:
            result = await self.score_with_google_genai(prompt, model=preferred_model or "gemini-pro")
            if "error" not in result or result.get("error") is None:
                return {**result, "model_used": "google_genai"}

        # Local fallback
        if self.enable_local_fallback:
            return {"model_used": "local_fallback", "note": "Use local NLP scoring"}

        return {"error": "No scoring model available"}
