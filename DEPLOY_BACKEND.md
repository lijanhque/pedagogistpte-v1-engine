# PTE Academic Scoring Engine - Production Deployment Guide

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Vercel / Motia Cloud                     │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         FastAPI Scoring Service (services/scoring_api) │ │
│  │  - /health                                              │ │
│  │  - /score (sync PTE scoring with NLP)                  │ │
│  │  - /score_async (enqueue job, returns job_id)          │ │
│  │  - /job/{job_id} (poll for results)                    │ │
│  │  - /workflow/* (orchestration & state)                 │ │
│  │  - /stream (SSE real-time updates)                     │ │
│  │  - /batch_score (batch processing)                     │ │
│  │  - /metrics (monitoring)                               │ │
│  └────────────────────────────────────────────────────────┘ │
│           ↓ (async job queue)                                 │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         RQ Worker (processes scoring jobs)              │ │
│  │  - Listens on Redis queue "scoring"                     │ │
│  │  - Calls local NLP scorer + Vercel Gateway              │ │
│  │  - Returns aggregated scores                            │ │
│  └────────────────────────────────────────────────────────┘ │
│                          ↓                                    │
│  ┌────────────────────────────────────────────────────────┐ │
│  │         Redis (state, pub/sub, queue)                  │ │
│  │  - Workflow state (24hr TTL)                            │ │
│  │  - Job queue for scoring tasks                          │ │
│  │  - Pub/sub for SSE streaming updates                    │ │
│  └────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
        ↓ (external API calls)
┌─────────────────────────────────────────────────────────────┐
│                 External AI Models                           │
│  - Vercel AI Gateway (LLM-based scoring refinement)         │
│  - Google GenAI (optional alternative)                      │
│  - AssemblyAI (optional audio transcription)                │
└─────────────────────────────────────────────────────────────┘
```

## Five Levels of the Engine

### **Level 1: API Endpoints** ✅
- **Endpoints:** `POST /score`, `POST /assessments`, `GET /assessments/{id}`
- **Response:** PTE scores (fluency, pronunciation, lexical_range, grammar, overall)
- **Local scoring:** Built-in NLP heuristics (no external dependencies)

### **Level 2: Background Jobs** ✅
- **Endpoints:** `POST /score_async`, `GET /job/{job_id}`, `POST /batch_score`
- **Queue:** RQ (Redis Queue) with configurable workers
- **Use case:** Large-scale submissions, batch scoring without blocking

### **Level 3: Workflow Orchestrator** ✅
- **Endpoints:** `POST /workflow/create`, `GET /workflow/{workflow_id}`
- **Features:** Multi-step workflows, state management, audit logging
- **Backend:** Redis for ephemeral state, Postgres for durable logs (optional)

### **Level 4: AI Agents** ✅
- **Integration:** Vercel AI Gateway, Google GenAI
- **Behavior:** Hybrid scoring (50% local NLP + 50% AI model)
- **Aggregation:** Weighted scoring ensures interpretability

### **Level 5: Streaming AI Agents** ✅
- **Endpoint:** `GET /workflow/{workflow_id}/stream`
- **Protocol:** Server-Sent Events (SSE)
- **Real-time:** Redis pub/sub broadcasts updates to all connected clients

---

## Environment Variables

Create a `.env` file in the repo root or configure in Vercel/Motia Cloud:

```bash
# Redis (required for queues and streaming)
REDIS_URL=redis://user:password@redis-host:6379/0

# AI Gateway Keys (optional, but recommended for production)
VERCEL_AI_GATEWAY_KEY=your_vercel_gateway_key_here
GOOGLE_GENAI_KEY=your_google_genai_key_here

# Scoring mode: 'sync' (default) or 'async' (enqueue jobs)
SCORE_MODE=sync

# Optional: PostgreSQL for audit logs (not required for basic operation)
DATABASE_URL=postgresql://user:password@db-host/pte_scoring

# Environment
APP_ENV=production
```

### Getting Keys

**Vercel AI Gateway:**
1. Go to https://vercel.com/docs/ai-gateway
2. Create an API key
3. Copy to `VERCEL_AI_GATEWAY_KEY`

**Google GenAI:**
1. Go to https://ai.google.dev
2. Create an API key
3. Copy to `GOOGLE_GENAI_KEY`

**Redis (self-hosted or managed):**
- **Local:** `redis://localhost:6379/0`
- **Upstash:** Use connection string from dashboard
- **AWS ElastiCache:** Follow AWS docs for connection string

---

## Deployment Options

### **Option 1: Vercel (Recommended for Simplicity)**

1. **Push code to GitHub:**
   ```bash
   git add .
   git commit -m "Add PTE scoring engine"
   git push origin main
   ```

2. **Connect to Vercel:**
   - Visit https://vercel.com/new
   - Import your GitHub repo
   - Select root directory: `/`
   - Build command: `pip install -r services/scoring_api/requirements.txt`

3. **Add environment variables in Vercel Dashboard:**
   - Go to Settings → Environment Variables
   - Add `REDIS_URL`, `VERCEL_AI_GATEWAY_KEY`, etc.

4. **Deploy:**
   - Click "Deploy"
   - Vercel automatically detects Python and builds the service

5. **API URL:**
   - `https://your-project.vercel.app/score`
   - `https://your-project.vercel.app/docs` (OpenAPI)

**Note:** Vercel's serverless functions have a 60-second timeout by default. For long-running scoring, use the async endpoint or configure a background worker.

### **Option 2: Motia Cloud (Recommended for Full Control)**

1. **Deploy via Motia CLI:**
   ```bash
   npm run build  # Build all services
   motia deploy --service scoring_api
   ```

2. **Configure in `motia-workbench.json`:**
   ```json
   {
     "services": {
       "scoring_api": {
         "build": "./services/scoring_api/Dockerfile",
         "port": 8000,
         "env": {
           "REDIS_URL": "${REDIS_URL}",
           "VERCEL_AI_GATEWAY_KEY": "${VERCEL_AI_GATEWAY_KEY}"
         }
       }
    }
   }
   ```

3. **Verify deployment:**
   ```bash
   curl https://scoring-api.motia.app/health
   ```

### **Option 3: Docker Compose (Local Development)**

```bash
# Build and run locally
docker compose up --build

# Test the API
curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d '{"text": "The quick brown fox jumps over the lazy dog"}'

# Open interactive docs
open http://localhost:8000/docs
```

---

## Running Background Workers

### **Option 1: Vercel Functions (Cold Start Friendly)**

For Vercel, use the async endpoints (`/score_async`, `/job/{id}`). The frontend polls for results.

### **Option 2: Dedicated Worker Host**

Deploy the RQ worker on a separate host or container:

```bash
# Start a worker that listens on Redis queue "scoring"
rq worker scoring --connection redis://redis-host:6379/0

# For production, use supervisor or systemd:
# [program:pte_worker]
# command=rq worker scoring --connection redis://redis-host:6379/0
# autorestart=true
```

### **Option 3: Motia Worker Service**

Add a `worker` service in `docker-compose.yml`:

```yaml
worker:
  build:
    context: ./services/scoring_api
  command: ["rq", "worker", "scoring"]
  environment:
    - REDIS_URL=redis://redis:6379/0
  depends_on:
    - redis
```

---

## Testing & Monitoring

### **Test the API:**

```bash
# Health check
curl http://localhost:8000/health

# Sync score
curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d '{
    "text": "This is a test response for the PTE academic exam.",
    "metadata": {"clarity_rating": 5}
  }'

# Async score
curl -X POST http://localhost:8000/score_async \
  -H "Content-Type: application/json" \
  -d '{"text": "Another sample response."}'

# Poll job
curl http://localhost:8000/job/job-id-from-above

# Batch score
curl -X POST http://localhost:8000/batch_score \
  -H "Content-Type: application/json" \
  -d '[
    {"text": "Sample 1"},
    {"text": "Sample 2"}
  ]'

# Stream workflow
curl --no-buffer http://localhost:8000/workflow/workflow-123/stream
```

### **Metrics:**

```bash
curl http://localhost:8000/metrics
# Returns: queue size, Redis status, etc.
```

### **OpenAPI Docs:**

Open http://localhost:8000/docs in a browser to explore and test all endpoints.

---

## Production Checklist

- [ ] **Redis:** Configured and accessible from all services
- [ ] **Env vars:** Set all `VERCEL_AI_GATEWAY_KEY` etc. in cloud platform
- [ ] **Monitoring:** Enable logs in Vercel/Motia Cloud dashboard
- [ ] **Error handling:** Errors are logged; fallback to local NLP if AI fails
- [ ] **Rate limiting:** Add rate limiting for `/score` and `/job` endpoints (optional via middleware)
- [ ] **Security:** Use TLS for all external API calls; validate input payloads
- [ ] **Testing:** Run `pytest tests/` before deploying
- [ ] **Backup:** Export audit logs and workflow states regularly

---

## Troubleshooting

### Redis Connection Error
```
Error: Connection refused
```
**Fix:** Ensure Redis is running and `REDIS_URL` is correct.

### Vercel AI Gateway 401 Error
```
Authorization failed
```
**Fix:** Check `VERCEL_AI_GATEWAY_KEY` is set and valid in Vercel environment variables.

### Worker Not Processing Jobs
```
Queue size keeps growing
```
**Fix:** Restart the RQ worker or check logs with `rq jobs scoring`.

---

## Next Steps

1. **Add Postgres for Audit Logs:**
   - Create schema for `audit_logs` table
   - Call `orchestrator.store_audit_log()` in `/score` endpoint

2. **Rate Limiting:**
   - Use `slowapi` library to add token bucket rate limiting

3. **Custom Models:**
   - Replace NLP scorer with fine-tuned models (e.g., using Hugging Face)

4. **Webhook Integration:**
   - Add `/webhook/submission_completed` to notify external systems

---

**Support:** For issues, check logs in Vercel/Motia Cloud dashboard or run locally with `docker compose logs scoring_api`.
