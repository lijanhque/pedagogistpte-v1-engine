# PTE Academic Scoring Engine - Quick Start Guide

## 🚀 Get Started in 2 Minutes

### Prerequisites
- Docker & Docker Compose
- Git
- (Optional) Vercel account for deployment

### Step 1: Clone & Setup

```bash
git clone <your-repo>
cd pedagogistpte-v1-engine
cp services/scoring_api/.env.example .env
```

### Step 2: Run Locally

```bash
docker compose up --build
```

**Output:**
```
scoring_api   | INFO:     Uvicorn running on http://0.0.0.0:8000
redis         | Ready to accept connections
worker        | Worker started...
```

### Step 3: Test the API

**Option A: Interactive UI**
```bash
open http://localhost:8000/docs
```
Click "Try it out" on any endpoint.

**Option B: Curl Commands**
```bash
# Health check
curl http://localhost:8000/health

# Score a response (synchronous)
curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d '{
    "text": "The rapid development of technology has significantly changed our daily lives in many positive ways.",
    "metadata": {"clarity_rating": 8}
  }'

# Response
{
  "scores": {
    "fluency": 72,
    "pronunciation": 75,
    "lexical_range": 70,
    "grammar": 73,
    "overall": 72
  },
  "model": "pte_nlp_scorer"
}
```

**Option C: Full Test Script**
```bash
bash test-endpoints.sh
```

---

## 📊 Understanding Scores

Each response receives a score from **0-90** across four dimensions:

| Score | Dimension | What It Measures |
|-------|-----------|------------------|
| **Fluency** | Coherence, pacing, discourse flow | Does the response flow naturally? |
| **Pronunciation** | Phoneme accuracy, stress patterns | Are sounds produced correctly? |
| **Lexical Range** | Vocabulary diversity and sophistication | Is vocabulary varied and advanced? |
| **Grammar** | Sentence structure and accuracy | Are sentences well-formed? |
| **Overall** | Average of above four | Total performance score |

**Example scores:**
- **30-40:** Short, simple response with basic vocabulary → Low across all dimensions
- **70-79:** Good length, varied vocabulary, mostly correct grammar → Solid performance
- **85-90:** Complex sentences, advanced vocabulary, minimal errors → Excellent performance

---

## 🔄 Async vs Sync Scoring

### Sync (Default, Immediate Response)
```bash
POST /score
→ ~5-10ms (instant)
→ Returns scores immediately
```

### Async (Enqueue & Poll)
```bash
POST /score_async
→ Immediate response: {"job_id": "uuid", "status": "queued"}
→ Worker processes in background
→ Poll: GET /job/uuid
→ Get result when ready
```

### Batch (Multiple Submissions)
```bash
POST /batch_score
→ Enqueue multiple submissions
→ Returns: {"job_ids": ["id1", "id2", ...]}
→ Poll each job individually
```

---

## 🌐 Deploy to Vercel

### 1. Push to GitHub
```bash
git add .
git commit -m "Add PTE scoring engine"
git push origin main
```

### 2. Connect to Vercel
- Go to https://vercel.com/new
- Import your GitHub repo
- Build command: (auto-detected)

### 3. Add Environment Variables
In Vercel Dashboard → Settings → Environment Variables:
```
REDIS_URL=your_redis_url
VERCEL_AI_GATEWAY_KEY=your_key
SCORE_MODE=sync
```

### 4. Deploy
- Click "Deploy"
- Wait for build to complete
- Your API is live at: `https://your-project.vercel.app`

### 5. Test
```bash
curl https://your-project.vercel.app/health
```

---

## 🌐 Deploy to Motia Cloud

```bash
npm run build
motia deploy --service scoring_api
```

---

## 🧪 Running Tests

```bash
# All tests
pytest services/scoring_api/tests/ -v

# Specific test class
pytest services/scoring_api/tests/test_comprehensive.py::TestNLPScorer -v

# With coverage
pytest services/scoring_api/tests/ --cov=app --cov-report=html
open htmlcov/index.html
```

---

## 📡 Real-Time Streaming

Create a workflow and stream updates:

```bash
# 1. Create workflow
curl -X POST http://localhost:8000/workflow/create \
  -H "Content-Type: application/json" \
  -d '{
    "assessment_id": "ASSESS-001",
    "submission": {"text": "My response..."}
  }'
# Returns: {"workflow_id": "uuid"}

# 2. Stream updates (in another terminal)
curl --no-buffer http://localhost:8000/workflow/uuid/stream

# Browser (JavaScript)
const eventSource = new EventSource('http://localhost:8000/workflow/uuid/stream');
eventSource.onmessage = (e) => {
  const data = JSON.parse(e.data);
  console.log('Update:', data);
};
```

---

## 🤖 Adding AI Gateway Scoring

Optional: Enable hybrid scoring (50% NLP + 50% AI).

### 1. Get API Keys
- **Vercel AI Gateway:** https://vercel.com/docs/ai-gateway
- **Google GenAI:** https://ai.google.dev

### 2. Set Environment Variables
```bash
# .env file or Vercel dashboard
VERCEL_AI_GATEWAY_KEY=your_key_here
GOOGLE_GENAI_KEY=your_key_here
```

### 3. Restart Service
```bash
docker compose down
docker compose up --build
```

### 4. Test
```bash
curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d '{"text": "Test response"}'

# Response now includes hybrid scores (50% AI + 50% NLP)
```

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Technical design and data flows |
| [DEPLOY_BACKEND.md](./DEPLOY_BACKEND.md) | Detailed deployment guide |
| [services/scoring_api/README.md](./services/scoring_api/README.md) | Service overview |
| OpenAPI docs | `http://localhost:8000/docs` (interactive) |

---

## 🔍 Monitoring & Debugging

### Check Logs
```bash
docker compose logs scoring_api    # API logs
docker compose logs worker         # Worker logs
docker compose logs redis          # Redis logs
```

### Health Check
```bash
curl http://localhost:8000/health
{
  "status": "ok",
  "version": "1.0.0",
  "features": {
    "crud": true,
    "sync_scoring": true,
    "async_scoring": true,
    "ai_agents": true,
    "streaming": true
  }
}
```

### Queue Metrics
```bash
curl http://localhost:8000/metrics
{
  "queue_size": 0,
  "redis_url": "redis://redis:6379/0",
  "score_mode": "sync"
}
```

### Restart Services
```bash
docker compose down
docker compose up --build
```

---

## ❓ Troubleshooting

### Redis Connection Error
```
Error: Connection refused at 6379
```
**Fix:** Make sure Redis is running: `docker compose ps`

### Vercel AI Gateway 401
```
Authorization failed
```
**Fix:** Check `VERCEL_AI_GATEWAY_KEY` in environment variables

### Worker Not Processing Jobs
```
Queue size keeps growing
```
**Fix:** Restart worker: `docker compose restart worker`

### Tests Failing
```bash
# Make sure Redis is running
docker compose up redis -d

# Run tests
pytest services/scoring_api/tests/ -v
```

---

## 🎯 What's Next?

1. **Explore the API:** Visit http://localhost:8000/docs
2. **Run tests:** `pytest services/scoring_api/tests/ -v`
3. **Deploy:** Push to GitHub for Vercel auto-deploy
4. **Monitor:** Check metrics at `/metrics` endpoint
5. **Scale:** Add more workers or deploy to Motia Cloud

---

## 📞 Quick Reference

```bash
# Development
docker compose up --build          # Start all services
docker compose down                # Stop all services
bash test-endpoints.sh             # Run all endpoint tests

# Testing
pytest services/scoring_api/tests/ -v  # Run tests
pytest --cov=app                   # With coverage

# Deployment
git push origin main               # Deploy to Vercel
motia deploy --service scoring_api # Deploy to Motia

# Debugging
docker compose logs -f scoring_api # Follow logs
curl http://localhost:8000/health  # Health check
curl http://localhost:8000/metrics # Queue metrics
```

---

**You're all set! 🚀 Visit http://localhost:8000/docs to explore the API.**
