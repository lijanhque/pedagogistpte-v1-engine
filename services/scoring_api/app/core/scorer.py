from typing import Dict, Any
from ..schemas import Submission


def compute_scores(sub: Submission) -> Dict[str, Any]:
    """Core scoring logic separated for reuse by sync endpoint and worker.

    Currently a deterministic placeholder. Replace with model calls or
    post-processing of model outputs.
    """
    base = 70
    text_len = len(sub.text or "")
    fluency = min(100, base + text_len % 31)
    pronunciation = min(100, base + (sub.metadata.get("pronunciation_hint", 0) if sub.metadata else 0))
    communicative = min(100, (fluency + pronunciation) // 2)

    return {
        "scores": {
            "fluency": fluency,
            "pronunciation": pronunciation,
            "communicative": communicative,
        },
        "raw": {"debug": "synthetic_demo"},
    }
