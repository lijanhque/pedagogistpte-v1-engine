# Architecture & Scoring Deep Dive

## Multi-Level Architecture

### Level 1: RESTful API Endpoints
**Purpose:** Expose CRUD operations and synchronous scoring.

**Endpoints:**
- `POST /assessments` – Create an assessment record
- `GET /assessments/{id}` – Retrieve assessment
- `POST /score` – Synchronous scoring (returns scores immediately)
- `GET /health` – Health check

**Tech:** FastAPI with Pydantic validation

---

### Level 2: Background Job Processing
**Purpose:** Handle async scoring jobs for high throughput and non-blocking responses.

**Components:**
- **RQ Queue:** Redis-backed job queue
- **Worker Process:** Consumes jobs from queue
- **Cron Tasks:** Future: scheduled re-scoring, batch processing

**Endpoints:**
- `POST /jobs` – Create and enqueue a job
- `GET /jobs/{job_id}` – Poll job status

**Workflow:**
```
Client → /jobs → Create job → Enqueue to RQ → Worker processes → Update Redis → Client polls status
```

---

### Level 3: Centralized Orchestration
**Purpose:** Manage complex scoring workflows with state machine and audit trails.

**Components:**
- **WorkflowOrchestrator:** State machine enforcing job transitions
- **Redis Pub/Sub:** Broadcast state changes to all listeners
- **Audit Logging:** Track all scoring decisions for compliance

**State Transitions:**
```
pending → processing → scored → enriched → completed
                                    ↓
                               (optional AI enrichment)
```

**Example Workflow:**
1. Job created in PENDING state
2. Worker picks it up → PROCESSING
3. Core PTE scoring completes → SCORED
4. AI enrichment adds insights → ENRICHED
5. Final validation → COMPLETED

---

### Level 4: AI Agents with Fallback
**Purpose:** Use LLMs (Vercel AI Gateway, Google GenAI) for nuanced scoring while maintaining local fallback.

**Agent Strategy:**
```
Try Vercel AI Gateway (primary)
    ↓ (if fails or key not present)
Try Google GenAI (secondary)
    ↓ (if fails or key not present)
Fall back to local rule-based PTE scorer
```

**Scoring Modes:**
- **Local Only:** Fast, deterministic, no API costs
- **AI-Assisted:** Hybrid (50% AI + 50% local) for accuracy
- **AI-First:** Prefer LLM with local fallback

---

### Level 5: Real-Time Streaming
**Purpose:** Push scoring updates to clients in real-time via Server-Sent Events.

**Endpoints:**
- `GET /stream/scoring/{job_id}` – Subscribe to job lifecycle events
- `GET /stream/scores/{job_id}` – Stream final scores when ready

**Event Types:**
```
job_created → job_state_changed → job_enriched → job_completed
```

**Client Example:**
```javascript
const eventSource = new EventSource('/stream/scoring/job123');
eventSource.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Update:', data.type, data.data);
};
```

---

## PTE Academic Scoring Algorithm

### Scoring Dimensions

#### 1. Fluency & Coherence (25% weight)

**Measures:**
- **Lexical Diversity:** Type-Token Ratio (unique words / total words)
  - Target: 0.5–0.8 for advanced fluency
  - Formula: `unique_words / total_words`
  
- **Sentence Complexity:** Average words per sentence, subordinate clauses
  - Simple sentences: < 10 words (penalize)
  - Complex: 15–25 words with subordinate clauses (reward)
  
- **Discourse Markers:** Transition words, connectives
  - Examples: "furthermore", "moreover", "nevertheless", "however"
  - Count frequency, weight by appropriateness

**Scoring Formula:**
```
fluency = (diversity_score * 0.4) + (complexity_score * 0.3) + (connectives_score * 0.3)
```

---

#### 2. Lexical Resource (25% weight)

**Measures:**
- **Vocabulary Level (CEFR):** Map words to proficiency bands (A1–C2)
  - A1–A2: High frequency, common words (penalize for advanced test)
  - B1–B2: Intermediate academic vocabulary
  - C1–C2: Advanced, sophisticated vocabulary (reward)
  
- **Academic Word List (AWL):** Proportion of words from AWL
  - Target: 10–15% for strong performance

**Scoring Formula:**
```
lexical_score = (advanced_ratio * 40) + (academic_ratio * 30) + (balance_score * 30)
```

---

#### 3. Grammar (20% weight)

**Checks:**
- Subject-verb agreement (e.g., "he don't" ❌)
- Tense consistency (mixing past/present)
- Article usage (a/an, the)
- Preposition correctness
- Sentence structure (fragments, run-ons)

**Scoring:**
```
grammar_score = (1 - error_ratio) * 100
where error_ratio = detected_errors / sentence_count
```

---

#### 4. Oral Fluency (15% weight)

**Approximations (from text):**
- **Filler Words:** "um", "uh", "like", "you know"
  - Target: < 5% of words
  - Formula: `filler_score = max(0, 80 - (filler_ratio * 100))`
  
- **Pacing:** Estimate speech rate
  - Assume ~150 words/min for natural speech
  - Penalize if text too short or too long for time allowed

---

#### 5. Pronunciation (Proxy – Text-Based)

**Phonetic Complexity:**
- Difficult sound combinations: "th", "sibilants" (s, z, sh)
- Consonant clusters: "str", "scr"
- Multi-syllabic words

**Heuristic:**
```
pronunciation_score = 60 + (phonetic_complexity / word_count) * 10
```

---

### Composite Scoring

**Weighted Sum:**
```
composite_score = 
  (fluency * 0.25) +
  (lexical * 0.25) +
  (grammar * 0.20) +
  (oral_fluency * 0.15) +
  (pronunciation * 0.15)
```

**Calibration to PTE Band (10–90):**
```
band = 10 + (composite_score / 100) * 80
band = round(band / 10) * 10  # Round to nearest 10
```

**Mapping to Section Score (0–90):**
```
section_score = ((band - 10) / 80) * 90
```

---

## AI Agent Integration

### Vercel AI Gateway

**Configuration:**
```python
{
  "endpoint": "https://api.vercel.ai/v1/chat/completions",
  "model": "gpt-4-turbo",
  "temperature": 0.7,
  "max_tokens": 500,
}
```

**Prompt Template:**
```
You are a PTE Academic scoring expert. Score this response:

{text}

Provide scores as JSON:
{
  "fluency": <0-100>,
  "lexical_resource": <0-100>,
  "grammar": <0-100>,
  "communicative": <0-100>,
  "rationale": "..."
}
```

**Fallback:** If Gateway fails or no key, use Google GenAI or local scorer.

---

### Hybrid Scoring (AI + Local)

**When AI is enabled:**
```
final_fluency = (ai_fluency * 0.5) + (local_fluency * 0.5)
```

This balances:
- **AI strength:** Context awareness, semantic understanding
- **Local strength:** Consistency, determinism, no cost

---

## Data Flow Example

**User submits text → Scores returned (with SSE updates):**

```
1. Client posts to POST /score or POST /jobs
2. API creates job in Redis (state: PENDING)
3. Publishes "job_created" event via pub/sub
4. If async mode: returns job_id immediately
5. Worker picks up job (state: PROCESSING)
6. Calls pte_scorer.score() → calculates fluency, lexical, etc.
7. Optionally calls ScoringAgent with Vercel fallback
8. Updates job state: SCORED
9. Optionally enriches with insights (state: ENRICHED)
10. Marks job COMPLETED
11. Client receives updates via SSE /stream/scoring/{job_id}
12. Client displays final scores
```

---

## Performance Characteristics

| Operation | Latency | Notes |
|-----------|---------|-------|
| Local scoring (sync) | 100–500ms | Pure Python NLP |
| Vercel AI Gateway | 1–3s | Network + LLM inference |
| Background job (RQ) | 1–5s | Queue + worker overhead |
| SSE streaming | < 100ms | Real-time pub/sub |

---

## Accuracy & Calibration

- **Local PTE scorer:** Rule-based, consistent (±5 points)
- **AI-enhanced:** More contextual, better at detecting nuance (±2 points with good prompts)
- **Hybrid mode:** Best balance of speed and accuracy

**Validation:** Compare system scores against human raters on a test set; adjust weights if needed.

---

## Security & Compliance

1. **Audit Logging:** All scoring decisions logged to Postgres
2. **API Keys:** Never logged; stored in environment secrets
3. **Data Retention:** Configurable; default 90 days
4. **GDPR:** Support data deletion via API endpoint (future)

