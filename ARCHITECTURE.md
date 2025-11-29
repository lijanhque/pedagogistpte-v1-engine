# PTE Academic Scoring Engine - Architecture

## Overview

The PTE Academic Scoring Engine is a **production-grade, backend-only** system designed to score speaking and writing responses for the PTE Academic exam. It uses a multi-level architecture with local NLP scoring, AI Gateway integration, async job processing, and real-time streaming updates.

**Key characteristics:**
- ✅ Backend-only (no frontend included)
- ✅ Deployable to Vercel, Motia Cloud, or Docker
- ✅ 5-level modular design (CRUD → Background Jobs → Orchestration → AI Agents → Streaming)
- ✅ Hybrid scoring: Local NLP (50%) + Vercel AI Gateway (50%)
- ✅ Real-time updates via SSE/WebSocket
- ✅ Redis-based queue and streaming
- ✅ Fully tested with pytest

---

## Core Components

### 1. **FastAPI Application** (`app/main_v2.py`)

The main HTTP API with 8 core endpoints:

| Endpoint | Method | Purpose | Level |
|----------|--------|---------|-------|
| `/health` | GET | Service health & feature flags | 1 |
| `/score` | POST | Sync PTE scoring (NLP + optional AI) | 1 |
| `/score_async` | POST | Enqueue scoring job | 2 |
| `/job/{job_id}` | GET | Poll async job result | 2 |
| `/assessments` | POST/GET | CRUD for assessment metadata | 1 |
| `/workflow/create` | POST | Create orchestration workflow | 3 |
| `/workflow/{id}` | GET | Retrieve workflow state | 3 |
| `/workflow/{id}/stream` | GET | SSE stream for real-time updates | 5 |
| `/batch_score` | POST | Enqueue multiple submissions | 2 |
| `/metrics` | GET | Queue & system metrics | 2 |

### 2. **NLP Scorer** (`app/core/pte_nlp_scorer.py`)

Local machine learning-free scoring based on linguistic features:

**Scoring dimensions:**
- **Fluency (0-90):** Response length, word complexity, sentence structure, filler word detection
- **Pronunciation (0-90):** Word syllable patterns, stress markers, metadata hints (clarity rating)
- **Lexical Range (0-90):** Type-Token Ratio (vocabulary diversity), lexical density (content vs. function words), advanced vocabulary detection
- **Grammar (0-90):** Sentence length variety, punctuation consistency, clause counts
- **Overall (0-90):** Weighted average of above (25% each)

**Why NLP-based scoring?**
- Instant response (no model latency)
- Deterministic and interpretable
- Works offline without external APIs
- Provides strong baseline for hybrid scoring

### 3. **Vercel AI Gateway Adapter** (`app/adapters/vercel_gateway.py`)

Async HTTP client for calling Vercel AI Gateway:

```python
await vercel_gateway.generate(prompt=text, api_key=key)
```

- Supports configurable model selection
- Returns structured JSON or raw text
- Error handling with fallback to NLP

### 4. **Workflow Orchestrator** (`app/core/workflow_orchestrator.py`)

Manages multi-step scoring pipelines with state management:

```
Workflow States:
  PENDING    → PROCESSING   → COMPLETED
             → FAILED (with error details)
```

Features:
- Create workflow instances with unique IDs
- Store state in Redis (24hr TTL)
- Publish updates via pub/sub
- Audit logging hook for Postgres (optional)

### 5. **RQ Worker** (`app/worker_v2.py`)

Background job processor:

```bash
rq worker scoring --connection redis://...
```

- Listens on Redis queue `scoring`
- Processes submissions asynchronously
- Runs same scoring pipeline as sync endpoint
- Returns results to Redis for client polling

### 6. **SSE Publisher** (`app/streaming/sse.py`)

Server-Sent Events for real-time updates:

```python
async def stream_updates(workflow_id: str) -> AsyncGenerator[str, None]:
    # Yields "data: {...}\n\n" for each workflow update
```

- In-memory queue per subscriber
- Automatic pub/sub via Redis
- 30-second keepalive to prevent timeouts
- Scales to multiple instances via Redis

---

## Data Flow

### Synchronous Scoring (Default)

```
Client Request
     ↓
POST /score {"text": "...", "metadata": {...}}
     ↓
FastAPI endpoint
     ↓
1. Compute NLP scores → compute_pte_scores()
     ↓
2. If VERCEL_AI_GATEWAY_KEY set:
   - Call Vercel Gateway asynchronously
   - Aggregate (50% NLP + 50% AI)
     ↓
3. Return ScoreResponse
     ↓
HTTP 200 + JSON
```

### Asynchronous Scoring

```
Client Request
     ↓
POST /score_async {"text": "..."}
     ↓
FastAPI endpoint
     ↓
1. Enqueue to Redis queue: scoring_queue.enqueue("app.worker.process_submission", sub_data)
     ↓
2. Return job_id immediately
     ↓
HTTP 200 + {"job_id": "...", "status": "queued"}
     ↓
Client polls GET /job/{job_id}
     ↓
RQ Worker (on separate process/host)
     ↓
1. Dequeue job
2. Call process_submission(sub_data)
3. Compute scores (NLP + optional AI)
4. Return result
     ↓
Client retrieves result: GET /job/{job_id} → {"status": "completed", "result": {...}}
```

### Workflow Orchestration + Streaming

```
Client Request
     ↓
POST /workflow/create {assessment_id, submission}
     ↓
1. Create workflow_id
2. Store state in Redis
3. Return workflow_id
     ↓
Client opens SSE stream
     ↓
GET /workflow/{workflow_id}/stream
     ↓
SSE Publisher subscribes to workflow
     ↓
Worker (background) processes workflow steps
     ↓
1. Compute NLP scores
2. Call AI Gateway (if available)
3. Aggregate scores
4. Publish update via Redis pub/sub
     ↓
SSE Publisher broadcasts to all connected clients
     ↓
Client receives real-time update:
   data: {"status": "processing", "scores": {...}}
```

---

## Redis Schema

### Keys

**Workflow state:**
```
workflow:{workflow_id} → JSON
  {
    "workflow_id": "uuid",
    "status": "completed|processing|failed",
    "scores": {...},
    "created_at": "iso-timestamp",
    "errors": [...]
  }
TTL: 24 hours
```

**Job queue:**
```
rq:job:{job_id} → RQ job data (handled by RQ library)
```

### Pub/Sub Channels

**Workflow updates:**
```
workflow_updates:{workflow_id}
  Publishes: {"workflow_id": "...", "status": "...", "scores": {...}}
```

---

## Integration Points

### Vercel AI Gateway

**Endpoint:** `https://api.vercel.ai/v1/generate` (example, adapt to your account)

**Request:**
```json
{
  "input": "The response text to score",
  "model": "gpt-4" (optional)
}
```

**Response:**
```json
{
  "scores": {
    "fluency": 75,
    "pronunciation": 80,
    "lexical_range": 72,
    "grammar": 78,
    "overall": 76
  }
}
```

**Error handling:** If AI Gateway fails, system falls back to local NLP scores.

### Google GenAI

Similar to Vercel Gateway but uses Google's API:
- Set `GOOGLE_GENAI_KEY` environment variable
- Adapter code can be added in `app/adapters/google_genai.py`

### PostgreSQL (Optional Audit Logging)

For production deployments, optional audit table:

```sql
CREATE TABLE audit_logs (
  id SERIAL PRIMARY KEY,
  workflow_id UUID NOT NULL,
  step VARCHAR(255) NOT NULL,
  result JSONB NOT NULL,
  timestamp TIMESTAMP DEFAULT NOW()
);
```

---

## Deployment Architectures

### Single-Server Deployment

```
┌─────────────────────────────┐
│  Vercel / Motia / Docker    │
│  ┌───────────────────────┐  │
│  │   FastAPI Server      │  │
│  │ (main_v2.py)          │  │
│  ├───────────────────────┤  │
│  │   RQ Worker           │  │
│  │ (worker_v2.py)        │  │
│  ├───────────────────────┤  │
│  │   Redis               │  │
│  │ (Queue + State + Pub) │  │
│  └───────────────────────┘  │
└─────────────────────────────┘
```

### Distributed Deployment

```
┌──────────────┐
│  Vercel      │
│  API Servers │ (multiple instances, stateless)
└──────┬───────┘
       ↓
┌──────────────────────┐
│  Redis (Upstash)     │ (managed, highly available)
│  Queue + State +Pub  │
└──────┬───────────────┘
       ↓
┌──────────────────────┐
│  Worker Host         │ (dedicated container/host)
│  RQ Worker(s)        │ (multiple workers if needed)
└──────────────────────┘
```

---

## Security Considerations

1. **API Keys:**
   - Store `VERCEL_AI_GATEWAY_KEY` and `GOOGLE_GENAI_KEY` as Vercel/Motia secrets
   - Never commit to version control

2. **Input Validation:**
   - Use Pydantic models to validate all inputs
   - Max text length: 10,000 characters (configurable)

3. **Rate Limiting:**
   - Optional: Add `slowapi` middleware for rate limiting
   - Prevent abuse of `/score` and `/score_async` endpoints

4. **TLS/HTTPS:**
   - All communication to external APIs uses HTTPS
   - Deploy with TLS certificates

5. **Audit Logging:**
   - Store all scoring requests/results in audit table (optional)
   - Enable in production for compliance

---

## Performance Characteristics

**Scoring latency:**
- **Local NLP:** ~5-10ms per submission
- **With Vercel AI Gateway:** ~200-500ms (network + model inference)
- **Batch scoring:** Linear with submission count

**Throughput:**
- **Sync endpoint:** Limited by response time (CPU-bound on NLP)
- **Async endpoint:** Can queue 1000s of jobs; worker throughput depends on external API rate limits

**Memory usage:**
- FastAPI app: ~50-100 MB
- Worker: ~100-150 MB per instance
- Redis: Depends on queue depth + workflow states

---

## Future Enhancements

1. **Fine-tuned NLP Models:** Replace heuristics with ML models (Hugging Face, etc.)
2. **Custom Model Endpoints:** Support user-defined scoring models
3. **Webhook Notifications:** POST to external systems when scoring completes
4. **Metrics & Analytics:** Prometheus metrics, dashboards in Grafana
5. **Multi-language Support:** Extend NLP scorer for non-English responses
6. **Audio Processing:** Integrate AssemblyAI for speech-to-text preprocessing

---

**Last Updated:** November 2025
