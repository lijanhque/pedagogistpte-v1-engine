# PTE Scoring Engine — Backend Testing & Debugging Guide

This guide covers testing all backend routes and debugging the production PTE Academic scoring system.

---

## Quick Start: Local Testing

### 1. Prerequisites

- Docker and Docker Compose installed
- Python 3.9+ (for local testing without Docker)
- `httpx` and `curl` for API testing

### 2. Start Services (Docker Compose)

```bash
cd /workspaces/pedagogistpte-v1-engine

# Copy environment template
cp services/scoring_api/.env.example .env

# Build and run
docker compose up --build
```

This starts:
- **FastAPI app** on port `8000`
- **Redis** on port `6379`
- **RQ Worker** (listening on `scoring` queue)

### 3. Verify Health

```bash
curl -s http://localhost:8000/health | jq .
```

Expected output:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "features": ["scoring", "streaming", "async_jobs", "ai_agents"]
}
```

### 4. Interactive API Docs

Open in browser:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

---

## Route Testing

### Run Automated Tests

```bash
# Inside the container or with local Python
cd services/scoring_api
python test-routes.py
```

This tests all routes and reports pass/fail status.

### Manual Route Tests

#### **Level 1: CRUD Operations**

**Create Assessment**
```bash
curl -X POST http://localhost:8000/assessments \
  -H "Content-Type: application/json" \
  -d '{"student_id": "student_001", "metadata": {"test_type": "speaking"}}'
```

**Get Assessment**
```bash
curl http://localhost:8000/assessments/{assessment_id}
```

#### **Level 1-4: Scoring**

**Local Scoring (Sync)**
```bash
curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d '{
    "assessment_id": "test_001",
    "student_id": "student_001",
    "text": "This is a comprehensive test of the PTE Academic scoring engine demonstrating fluency, lexical range, and grammatical accuracy.",
    "metadata": {"source": "test"}
  }' | jq .
```

**AI Agent Scoring (Requires Keys)**
```bash
curl -X POST http://localhost:8000/score/with-ai \
  -H "Content-Type: application/json" \
  -d '{
    "assessment_id": "test_ai_001",
    "student_id": "student_001",
    "text": "The rapid advancement of artificial intelligence has transformed multiple sectors...",
    "metadata": {}
  }' | jq .
```

#### **Level 2-3: Background Jobs & Orchestration**

**Create Job**
```bash
JOB=$(curl -s -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "assessment_id": "job_test_001",
    "text": "Speaking fluently is important for effective communication.",
    "metadata": {"job_type": "scoring"}
  }' | jq -r '.job_id')

echo "Job ID: $JOB"
```

**Get Job Status**
```bash
curl http://localhost:8000/jobs/{job_id} | jq .
```

**Enqueue Job to Worker**
```bash
curl -X POST http://localhost:8000/jobs/{job_id}/enqueue | jq .
```

#### **Level 5: Streaming**

**Subscribe to Scoring Updates (SSE)**
```bash
curl -N http://localhost:8000/stream/scoring/{job_id}
```

This opens an event stream. The server will send updates as the job progresses.

Example output:
```
data: {"type":"connected","job_id":"..."}
data: {"type":"job_state_changed","data":{"state":"processing",...}}
data: {"type":"job_completed","data":{"scores":{...}}}
```

#### **Metrics**

```bash
curl http://localhost:8000/metrics | jq .
```

Example:
```json
{
  "queue_size": 2,
  "redis_ping": true
}
```

---

## Scoring Accuracy Validation

### What Scoring Dimensions Are Tested?

The PTE scorer evaluates:

1. **Fluency & Coherence** (0-100)
   - Lexical diversity
   - Sentence complexity
   - Use of discourse markers

2. **Lexical Resource** (0-100)
   - Vocabulary range (CEFR classification)
   - Academic word use
   - Repetition analysis

3. **Grammar** (0-100)
   - Rule-based error detection
   - Subject-verb agreement
   - Tense accuracy

4. **Oral Fluency** (0-100) — Text-based proxy
   - Filler word detection
   - Pacing indicators
   - Hesitation markers

5. **Pronunciation** (0-100) — Text-based proxy
   - Phonetic complexity
   - Syllable patterns

### Score Calibration

Scores are calibrated to:
- **PTE Band**: 10-90 (per PTE Academic standard)
- **Section Score**: 0-90 (mapped from band)

### Test Case: Check Accuracy

Send a high-quality response:
```bash
curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d '{
    "text": "The multifaceted implications of technological advancement across contemporary society necessitate a comprehensive and nuanced analysis of both opportunities and challenges. Furthermore, the intersection of artificial intelligence, sustainable development, and equitable resource distribution remains pivotal...",
    "metadata": {}
  }' | jq '.scores'
```

Expected: Fluency, lexical_resource, and grammar scores should be **higher** (70+).

Send a low-quality response:
```bash
curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d '{
    "text": "The thing is good. I like it. It is very good.",
    "metadata": {}
  }' | jq '.scores'
```

Expected: Scores should be **lower** (40-60).

---

## Debugging

### Check Logs

**API logs:**
```bash
docker compose logs scoring_api
```

**Worker logs:**
```bash
docker compose logs worker
```

**Redis logs:**
```bash
docker compose logs redis
```

### Monitor Redis Queue

```bash
# Inside Redis CLI
redis-cli

# List jobs in the "scoring" queue
llen rq:queue:scoring

# Inspect a job
hgetall rq:job:{job_id}
```

Or via Python:
```python
import redis
from rq import Queue

conn = redis.from_url("redis://localhost:6379/0")
q = Queue("scoring", connection=conn)
print(f"Pending jobs: {len(q.jobs)}")
for job in q.jobs:
    print(f"  {job.id}: {job.get_status()}")
```

### Test with Local Environment Variables

Create `.env` file in repo root:
```bash
VERCEL_AI_GATEWAY_KEY=your_key_here
GOOGLE_GENAI_KEY=your_key_here
REDIS_URL=redis://localhost:6379/0
SCORE_MODE=sync
APP_ENV=development
```

Rebuild and restart:
```bash
docker compose up --build
```

---

## Deployment Verification

### Vercel Deployment

1. Ensure `vercel.json` is configured (see `PRODUCTION_DEPLOYMENT.md`)
2. Test with Vercel preview:
   ```bash
   vercel deploy --prebuilt
   ```

### Docker Registry

1. Build image:
   ```bash
   docker build -t pte-scoring-api:latest services/scoring_api/
   ```

2. Test locally:
   ```bash
   docker run -p 8000:8000 \
     -e REDIS_URL=redis://host.docker.internal:6379/0 \
     pte-scoring-api:latest
   ```

### Kubernetes (if applicable)

Deploy with:
```bash
kubectl apply -f k8s-scoring-api.yaml
```

Check status:
```bash
kubectl logs -f deployment/pte-scoring-api
```

---

## Performance Benchmarks

Run load test:
```bash
# Install Apache Bench
apt-get install -y apache2-utils

# 100 requests, 10 concurrent
ab -n 100 -c 10 http://localhost:8000/health
```

Expected: ~100-500ms response time per request

---

## Common Issues & Fixes

### Redis Connection Error
```
ConnectionError: Error -3 connecting to redis://redis:6379/0. Temporary failure in name resolution.
```

**Fix:** Ensure `docker-compose.yml` has `depends_on: redis` and both services are running.

### Module Not Found (e.g., `nltk`)
```
ModuleNotFoundError: No module named 'nltk'
```

**Fix:** Rebuild the image:
```bash
docker compose up --build
```

### Job Not Processing
- Check worker logs: `docker compose logs worker`
- Verify Redis is running: `redis-cli ping`
- Check queue: `docker compose exec redis redis-cli LLEN rq:queue:scoring`

### Streaming Not Working
- Use `curl -N` (unbuffered) to receive SSE events
- Check that job_id exists before subscribing
- Verify Redis pub/sub is enabled (default is on)

---

## Next Steps

1. **Integrate with Frontend:** Use endpoints from your separate Next.js app
2. **Add Database:** Replace in-memory `ASSESSMENTS` store with Postgres
3. **Set API Keys:** Add `VERCEL_AI_GATEWAY_KEY` and `GOOGLE_GENAI_KEY` to production
4. **Monitor:** Add logging (structured logs, Sentry, etc.)
5. **Scale:** Deploy worker to separate container/machine for higher throughput

---

## Support & Documentation

- **API Docs:** http://localhost:8000/docs
- **Architecture:** See `ARCHITECTURE.md`
- **Deployment:** See `PRODUCTION_DEPLOYMENT.md`
- **Scoring Details:** See `SCORING_METHODOLOGY.md`
