# Environment Variables Guide

Copy this file to `.env` and populate with your actual keys.

```bash
# ============= Application =============
APP_ENV=production                          # development or production
SCORE_MODE=sync                             # sync or async (background jobs)

# ============= Database =============
DATABASE_URL=postgresql://user:pass@localhost:5432/pte_scoring
                                            # Format: postgresql://[user[:password]@][netloc][:port][/dbname]

# ============= Redis / Caching =============
REDIS_URL=redis://redis:6379/0              # Redis URL for queues and pub/sub
                                            # For UpStash: redis://:<API_KEY>@<HOST>:6379

# ============= AI Models =============
VERCEL_AI_GATEWAY_KEY=sk_...               # Vercel AI Gateway API key
                                            # Get from: https://vercel.com/docs/ai-gateway
GOOGLE_GENAI_KEY=AIz...                    # Google GenAI API key
                                            # Get from: https://makersuite.google.com/app/apikey

# ============= Frontend (Vercel) =============
NEXT_PUBLIC_SCORING_API_URL=https://api.example.com
                                            # Public URL of scoring API
                                            # Set in Vercel dashboard

# ============= Monitoring & Logging =============
SENTRY_DSN=https://...@sentry.io/...       # Sentry error tracking (optional)
LOG_LEVEL=info                              # debug, info, warning, error

# ============= CORS =============
CORS_ORIGINS=https://app.example.com,https://staging-app.example.com
```

## Deployment-Specific Values

### Local Development
```bash
DATABASE_URL=postgresql://postgres:password@localhost:5432/pte_dev
REDIS_URL=redis://localhost:6379/0
NEXT_PUBLIC_SCORING_API_URL=http://localhost:8000
```

### Staging (e.g., DigitalOcean)
```bash
DATABASE_URL=postgresql://staging_user:${STAGING_DB_PASS}@managed-db-staging.ondigitalocean.com:25060/pte_staging
REDIS_URL=redis://:<API_KEY>@redis-staging.upstash.io:6379
NEXT_PUBLIC_SCORING_API_URL=https://api-staging.example.com
VERCEL_AI_GATEWAY_KEY=sk_...  # Your Vercel key
```

### Production (AWS/Cloud)
```bash
DATABASE_URL=postgresql://<RDS_ENDPOINT>:5432/pte_prod  # AWS RDS
REDIS_URL=redis://:<API_KEY>@redis-prod.upstash.io:6379  # UpStash Redis
NEXT_PUBLIC_SCORING_API_URL=https://api.example.com
VERCEL_AI_GATEWAY_KEY=sk_...  # Use AWS Secrets Manager in production
GOOGLE_GENAI_KEY=...          # Use AWS Secrets Manager in production
CORS_ORIGINS=https://app.example.com
```

## How to Get API Keys

### Vercel AI Gateway
1. Sign up / log in at https://vercel.com
2. Go to https://vercel.com/docs/ai-gateway
3. Create a new AI Gateway API key
4. Copy key and set as `VERCEL_AI_GATEWAY_KEY`

### Google GenAI (Gemini)
1. Go to https://makersuite.google.com/app/apikey
2. Click "Create API Key"
3. Choose "Create API key in new project" or existing
4. Copy and set as `GOOGLE_GENAI_KEY`

### AWS RDS (Postgres)
1. Create RDS database cluster
2. Get endpoint, username, password from RDS console
3. Construct `DATABASE_URL=postgresql://user:pass@endpoint:5432/dbname`

### UpStash Redis (Managed)
1. Sign up at https://upstash.com
2. Create Redis database
3. Copy connection string (includes API key)
4. Set as `REDIS_URL=redis://:<API_KEY>@endpoint:6379`

### Sentry (Error Tracking)
1. Sign up at https://sentry.io
2. Create new project (choose Python + FastAPI)
3. Copy DSN
4. Set as `SENTRY_DSN`

## Secure Handling

**In development:**
- Use `.env.local` (git-ignored) for local secrets
- Never commit secrets to git

**In production (recommended):**
- Use cloud platform secret managers:
  - **Vercel:** Environment variables in project settings
  - **AWS:** Secrets Manager or Parameter Store
  - **DigitalOcean:** App Platform environment variables
- Rotate keys regularly
- Use different keys for staging vs. production

## Docker Compose

For local development, the `docker-compose.yml` will read from `.env`:
```bash
cp services/scoring_api/.env.example .env
docker compose up --build
```

Environment variables are passed to containers automatically.
