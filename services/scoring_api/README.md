# PTE Academic Scoring Engine (Production Backend)

A fully-featured **backend-only** scoring engine for PTE Academic exam responses. Deployable to **Vercel** or **Motia Cloud** with support for hybrid NLP + AI scoring, async job processing, workflow orchestration, and real-time streaming.

## 🎯 Features

- ✅ **Level 1:** CRUD API + sync/async scoring endpoints
- ✅ **Level 2:** RQ background job queue with batch processing
- ✅ **Level 3:** Workflow orchestrator with Redis state management
- ✅ **Level 4:** Hybrid scoring (50% local NLP + 50% Vercel AI Gateway)
- ✅ **Level 5:** Real-time updates via Server-Sent Events (SSE)
- ✅ **Production-ready:** Docker, CI/CD, comprehensive tests, monitoring

## 📊 PTE Scoring Dimensions

Scores responses across four core dimensions (0-90 scale):

1. **Fluency** — Response length, word complexity, discourse structure, filler word detection
2. **Pronunciation** — Word syllable patterns, stress patterns, metadata hints
3. **Lexical Range** — Vocabulary diversity (Type-Token Ratio), lexical density, advanced vocabulary
4. **Grammar** — Sentence structure variety, punctuation consistency, clause complexity
5. **Overall** — Weighted average of above four

All scoring is **interpretable** (no black-box ML) and **instant** (no external API latency needed).

## 🚀 Quick Start

### Local Development

```bash
# Clone and install
git clone <repo>
cd pedagogistpte-v1-engine

# Set up environment
cp services/scoring_api/.env.example .env

# Build and run
docker compose up --build

# Test
curl -X POST http://localhost:8000/score \
  -H "Content-Type: application/json" \
  -d '{"text": "The rapid development of technology has changed our lives significantly."}'

# OpenAPI docs
open http://localhost:8000/docs
```

### Deploy to Vercel

```bash
git push origin main
# Vercel auto-deploys via GitHub webhook

# Check deployment
curl https://your-project.vercel.app/health
```

### Deploy to Motia Cloud

```bash
npm run build
motia deploy --service scoring_api
```

## 📝 API Endpoints

### Scoring

**Sync scoring (returns immediately):**
```bash
POST /score
Content-Type: application/json

{
  "text": "Response text to score",
  "metadata": {"clarity_rating": 8}
}

# Returns
{
  "scores": {
    "fluency": 72,
    "pronunciation": 75,
    "lexical_range": 68,
    "grammar": 70,
    "overall": 71
  },
  "model": "pte_nlp_scorer"
}
```

**Async scoring (returns job_id):**
```bash
POST /score_async
Content-Type: application/json

{"text": "..."}

# Returns
{"job_id": "job-uuid", "status": "queued"}

# Poll for result
GET /job/job-uuid
```

### Batch Processing

```bash
POST /batch_score
Content-Type: application/json

[
  {"text": "Sample 1"},
  {"text": "Sample 2"}
]

# Returns
{"job_ids": ["job-1", "job-2"], "count": 2}
```

### Real-Time Streaming

```bash
# Create a workflow
POST /workflow/create
{"assessment_id": "ASSESS-001", "submission": {"text": "..."}}

# Returns
{"workflow_id": "workflow-uuid"}

# Stream updates
GET /workflow/workflow-uuid/stream
# EventSource receives: data: {"status": "...", "scores": {...}}\n\n
```

### CRUD Operations

```bash
# Create assessment
POST /assessments
{"student_id": "STU-001", "metadata": {...}}

# Get assessment
GET /assessments/{assessment_id}
```

### Monitoring

```bash
GET /health          # Service health & features
GET /metrics         # Queue size, Redis status
```

## 🔑 Environment Variables

```bash
# Required
REDIS_URL=redis://localhost:6379/0

# AI Gateway Keys (optional but recommended)
VERCEL_AI_GATEWAY_KEY=your_key_here
GOOGLE_GENAI_KEY=your_key_here

# Scoring mode
SCORE_MODE=sync  # or 'async'

# Optional
DATABASE_URL=postgresql://...  # For audit logs
APP_ENV=production
```

## 🏗 Architecture

See [ARCHITECTURE.md](../../ARCHITECTURE.md) for detailed design.

```
FastAPI Server (Vercel/Motia)
    ↓
NLP Scorer (instant local scoring)
    ↓
Vercel AI Gateway (optional hybrid scoring)
    ↓
Redis Queue (background jobs)
    ↓
RQ Worker (async processing)
    ↓
SSE Publisher (real-time updates)
```

## 🧪 Testing

```bash
# Run all tests
pytest services/scoring_api/tests/ -v

# With coverage
pytest services/scoring_api/tests/ --cov=app --cov-report=html

# Specific test
pytest services/scoring_api/tests/test_comprehensive.py::TestNLPScorer -v
```

## 📦 Production Deployment

See [DEPLOY_BACKEND.md](../../DEPLOY_BACKEND.md) for step-by-step instructions.

**Deployment checklist:**
- [ ] Redis configured and accessible
- [ ] Environment variables set (VERCEL_AI_GATEWAY_KEY, etc.)
- [ ] Tests passing
- [ ] Docker image builds successfully
- [ ] Monitoring/logging enabled

## 📊 Performance

- **Sync scoring latency:** ~5-10ms (NLP only) or ~200-500ms (with AI Gateway)
- **Async throughput:** Limited by queue worker count (can scale horizontally)
- **Memory:** ~100-150MB per instance

## 🔒 Security

- Input validation via Pydantic
- API key management via environment variables
- Rate limiting (optional via slowapi middleware)
- Audit logging support (optional Postgres)
- TLS/HTTPS for all external API calls

## 🛠 Files Structure

```
services/scoring_api/
├── app/
│   ├── main_v2.py              # Main API (all 5 levels)
│   ├── worker_v2.py            # RQ worker for async jobs
│   ├── schemas.py              # Pydantic models
│   ├── core/
│   │   ├── pte_nlp_scorer.py  # PTE scoring logic (fluency, etc.)
│   │   └── workflow_orchestrator.py  # Workflow state management
│   ├── adapters/
│   │   └── vercel_gateway.py   # AI Gateway integration
│   ├── streaming/
│   │   └── sse.py             # Server-Sent Events
│   └── __init__.py
├── tests/
│   ├── test_comprehensive.py    # Full test suite
│   └── test_main.py
├── requirements.txt
├── Dockerfile
├── README.md
└── .env.example
```

## 🤝 Contributing

1. Add feature in a new branch
2. Add tests in `tests/test_*.py`
3. Run `pytest` and linters (`black`, `flake8`)
4. Push and open a PR

## 📖 Documentation

- [DEPLOY_BACKEND.md](../../DEPLOY_BACKEND.md) — Deployment guide
- [ARCHITECTURE.md](../../ARCHITECTURE.md) — Technical architecture
- OpenAPI docs: `http://localhost:8000/docs` (when running locally)

## 📞 Support

Check logs in Vercel/Motia Cloud dashboard or run locally with `docker compose logs scoring_api`.
