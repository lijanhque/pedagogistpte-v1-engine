"""
Prompt templates and model configuration for Vercel AI Gateway and Google GenAI.
"""

SCORING_PROMPTS = {
    "fluency_analysis": """
Analyze the fluency and coherence of the following response. Consider:
- Lexical diversity and synonym use
- Sentence structure and complexity
- Use of connectives and transitions
- Logical flow and organization

Response: {text}

Provide a JSON response with:
{{ "fluency_score": <0-100>, "coherence": <0-100>, "notes": "..." }}
""",

    "lexical_assessment": """
Evaluate the lexical resource (vocabulary) of this response. Consider:
- Range of vocabulary used
- Word frequency and appropriateness
- Academic word use
- Variety and repetition

Response: {text}

Provide a JSON response with:
{{ "lexical_score": <0-100>, "cefr_level": "A1|A2|B1|B2|C1|C2", "vocab_range": "..." }}
""",

    "grammar_check": """
Analyze grammar and sentence structure in this response:
- Grammatical errors and types
- Sentence construction complexity
- Use of tenses and aspects
- Subject-verb agreement

Response: {text}

Provide a JSON response with:
{{ "grammar_score": <0-100>, "error_count": <int>, "errors": [{{ "type": "...", "description": "..." }}] }}
""",

    "overall_pte_score": """
You are a PTE Academic scoring expert. Score this submission holistically:

Response: {text}

Consider: fluency, coherence, lexical resource, grammar, and communicative effectiveness.

Provide a JSON response with:
{{
  "overall_score": <10-90>,
  "fluency": <0-100>,
  "lexical_resource": <0-100>,
  "grammar": <0-100>,
  "communicative": <0-100>,
  "rationale": "..."
}}
""",
}

MODEL_CONFIG = {
    "vercel_gateway": {
        "endpoint": "https://api.vercel.ai/v1/generate",
        "model": "gpt-4",
        "temperature": 0.7,
        "max_tokens": 500,
    },
    "google_genai": {
        "model": "gemini-pro",
        "temperature": 0.7,
        "top_k": 40,
        "top_p": 0.95,
    },
    "local_nlp": {
        "type": "rule_based",
        "features": ["lexical_diversity", "grammar_rules", "discourse_markers"],
    },
}
