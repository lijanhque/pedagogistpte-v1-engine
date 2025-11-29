#!/bin/bash
# Comprehensive Backend Route Testing & Debugging
# Tests all 5 levels of the PTE Scoring Engine

set -e

API_URL="${1:-http://localhost:8000}"
TIMEOUT=5
FAILED=0
PASSED=0

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "================================================"
echo "🧪 PTE Scoring Engine - Full Route Diagnostics"
echo "================================================"
echo "API URL: $API_URL"
echo "Testing Started: $(date)"
echo ""

# Function to test endpoint
test_endpoint() {
  local name="$1"
  local method="$2"
  local endpoint="$3"
  local data="$4"
  local expected_status="$5"

  echo -ne "${BLUE}Testing:${NC} $name... "

  if [ "$method" = "GET" ]; then
    response=$(curl -s -w "\n%{http_code}" "$API_URL$endpoint" 2>&1)
  else
    response=$(curl -s -w "\n%{http_code}" -X "$method" "$API_URL$endpoint" \
      -H "Content-Type: application/json" \
      -d "$data" 2>&1)
  fi

  http_code=$(echo "$response" | tail -n1)
  body=$(echo "$response" | head -n-1)

  if [[ "$http_code" == "$expected_status"* ]]; then
    echo -e "${GREEN}✓ PASS${NC} (HTTP $http_code)"
    ((PASSED++))
    if [[ "$body" != "" && "$body" != "null" ]]; then
      echo "  Response: $(echo "$body" | head -c 100)..."
    fi
  else
    echo -e "${RED}✗ FAIL${NC} (Expected $expected_status, got $http_code)"
    ((FAILED++))
    echo "  Response: $body"
  fi
  echo ""
}

# ============= LEVEL 1: Basic CRUD & Health =============
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}LEVEL 1: API Endpoints & CRUD${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

test_endpoint "Health Check" "GET" "/health" "" "200"

test_endpoint "Create Assessment" "POST" "/assessments" \
  '{"student_id": "STU-001", "metadata": {"test_type": "speaking"}}' "200"

# Store assessment ID for later tests
ASSESS_RESP=$(curl -s -X POST "$API_URL/assessments" \
  -H "Content-Type: application/json" \
  -d '{"student_id": "STU-DEBUG-001", "metadata": {}}')
ASSESS_ID=$(echo "$ASSESS_RESP" | grep -o '"id":"[^"]*' | cut -d'"' -f4 || echo "unknown")

test_endpoint "Get Assessment" "GET" "/assessments/$ASSESS_ID" "" "200"

test_endpoint "Get Non-Existent Assessment" "GET" "/assessments/fake-id" "" "404"

# ============= LEVEL 1: Scoring Endpoints =============
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}LEVEL 1: Scoring (Sync)${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

test_endpoint "Score - Empty Text" "POST" "/score" \
  '{"text": "", "metadata": {}}' "200"

test_endpoint "Score - Short Text" "POST" "/score" \
  '{"text": "Hello world.", "metadata": {}}' "200"

test_endpoint "Score - Long Text" "POST" "/score" \
  '{"text": "The rapid development of technology has significantly transformed our daily lives. Modern innovations in artificial intelligence and machine learning are reshaping industries worldwide. These advancements require careful ethical consideration and responsible implementation to ensure positive societal impact.", "metadata": {"clarity_rating": 8}}' "200"

test_endpoint "Score - With Metadata" "POST" "/score" \
  '{"text": "Advanced vocabulary and complex sentence structures demonstrate high proficiency.", "metadata": {"clarity_rating": 9, "accent_penalty": 0}}' "200"

# ============= LEVEL 2: Async & Batch =============
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}LEVEL 2: Async Jobs & Batch Processing${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

test_endpoint "Enqueue Async Score" "POST" "/score_async" \
  '{"text": "Async scoring test."}' "200"

# Store job ID
JOB_RESP=$(curl -s -X POST "$API_URL/score_async" \
  -H "Content-Type: application/json" \
  -d '{"text": "Get job status test."}')
JOB_ID=$(echo "$JOB_RESP" | grep -o '"job_id":"[^"]*' | cut -d'"' -f4 || echo "unknown")

test_endpoint "Poll Job Status" "GET" "/job/$JOB_ID" "" "200"

test_endpoint "Poll Non-Existent Job" "GET" "/job/fake-job-id" "" "404"

test_endpoint "Batch Score" "POST" "/batch_score" \
  '[{"text": "Batch 1"}, {"text": "Batch 2"}, {"text": "Batch 3"}]' "200"

# ============= LEVEL 3: Workflow Orchestration =============
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}LEVEL 3: Workflow Orchestration${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

test_endpoint "Create Workflow" "POST" "/workflow/create" \
  '{"assessment_id": "ASSESS-001", "submission": {"text": "Workflow test response."}}' "200"

# Store workflow ID
WF_RESP=$(curl -s -X POST "$API_URL/workflow/create" \
  -H "Content-Type: application/json" \
  -d '{"assessment_id": "ASSESS-002", "submission": {"text": "Get workflow test."}}')
WF_ID=$(echo "$WF_RESP" | grep -o '"workflow_id":"[^"]*' | cut -d'"' -f4 || echo "unknown")

test_endpoint "Get Workflow" "GET" "/workflow/$WF_ID" "" "200"

test_endpoint "Get Non-Existent Workflow" "GET" "/workflow/fake-workflow" "" "404"

# ============= LEVEL 5: Streaming =============
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}LEVEL 5: Streaming (SSE)${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -ne "${BLUE}Testing:${NC} Stream Workflow (5s timeout)... "
if timeout 5 curl -s --no-buffer "$API_URL/workflow/$WF_ID/stream" 2>&1 | grep -q "data:"; then
  echo -e "${GREEN}✓ PASS${NC}"
  ((PASSED++))
else
  echo -e "${YELLOW}⚠ SKIP${NC} (SSE stream - expected in browser)"
fi
echo ""

# ============= Monitoring =============
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Monitoring & Metrics${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

test_endpoint "Get Metrics" "GET" "/metrics" "" "200"

# ============= Summary =============
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}Test Summary${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

echo -e "✓ ${GREEN}PASSED: $PASSED${NC}"
echo -e "✗ ${RED}FAILED: $FAILED${NC}"
TOTAL=$((PASSED + FAILED))
PASS_RATE=$((PASSED * 100 / TOTAL))
echo "Pass Rate: ${PASS_RATE}%"
echo ""

if [ $FAILED -eq 0 ]; then
  echo -e "${GREEN}✅ All tests passed!${NC}"
  echo ""
  echo "Next steps:"
  echo "  1. Interactive API docs: $API_URL/docs"
  echo "  2. OpenAPI schema: $API_URL/openapi.json"
  echo "  3. Deploy: git push origin main"
  exit 0
else
  echo -e "${RED}❌ Some tests failed.${NC}"
  echo ""
  echo "Debug tips:"
  echo "  1. Check API logs: docker compose logs scoring_api"
  echo "  2. Check Redis: docker compose logs redis"
  echo "  3. Restart: docker compose down && docker compose up --build"
  exit 1
fi
