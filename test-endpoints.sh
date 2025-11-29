#!/bin/bash
# Complete test script for PTE Scoring Engine
# Usage: bash test-endpoints.sh [http://localhost:8000]

API_URL="${1:-http://localhost:8000}"
echo "🧪 Testing PTE Scoring Engine at: $API_URL"
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Test 1: Health Check
echo -e "${BLUE}1️⃣  Testing Health Check${NC}"
curl -s "$API_URL/health" | jq . || echo "FAILED"
echo ""

# Test 2: Sync Scoring
echo -e "${BLUE}2️⃣  Testing Sync Scoring${NC}"
SYNC_RESP=$(curl -s -X POST "$API_URL/score" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "The rapid development of technology has significantly transformed our daily lives. Artificial intelligence and machine learning are revolutionizing industries and creating new opportunities. These advancements require careful management to ensure ethical and responsible implementation.",
    "metadata": {"clarity_rating": 8}
  }')
echo "$SYNC_RESP" | jq .
echo ""

# Test 3: Async Scoring
echo -e "${BLUE}3️⃣  Testing Async Scoring (Enqueue)${NC}"
ASYNC_RESP=$(curl -s -X POST "$API_URL/score_async" \
  -H "Content-Type: application/json" \
  -d '{"text": "This is a test async submission."}')
JOB_ID=$(echo "$ASYNC_RESP" | jq -r '.job_id')
echo "$ASYNC_RESP" | jq .
echo ""

# Test 4: Poll Job Status
echo -e "${BLUE}4️⃣  Testing Job Status Poll${NC}"
if [ "$JOB_ID" != "null" ]; then
  sleep 2  # Give worker time to process
  curl -s "$API_URL/job/$JOB_ID" | jq .
else
  echo "⚠️  No job_id from async request"
fi
echo ""

# Test 5: Create Assessment
echo -e "${BLUE}5️⃣  Testing Create Assessment${NC}"
ASSESS_RESP=$(curl -s -X POST "$API_URL/assessments" \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "STU-TEST-001",
    "metadata": {"test_type": "speaking", "date": "2025-11-29"}
  }')
ASSESS_ID=$(echo "$ASSESS_RESP" | jq -r '.id')
echo "$ASSESS_RESP" | jq .
echo ""

# Test 6: Get Assessment
echo -e "${BLUE}6️⃣  Testing Get Assessment${NC}"
if [ "$ASSESS_ID" != "null" ]; then
  curl -s "$API_URL/assessments/$ASSESS_ID" | jq .
else
  echo "⚠️  No assessment_id from create"
fi
echo ""

# Test 7: Batch Score
echo -e "${BLUE}7️⃣  Testing Batch Scoring${NC}"
BATCH_RESP=$(curl -s -X POST "$API_URL/batch_score" \
  -H "Content-Type: application/json" \
  -d '[
    {"text": "Sample batch submission 1."},
    {"text": "Sample batch submission 2."},
    {"text": "Sample batch submission 3."}
  ]')
echo "$BATCH_RESP" | jq .
echo ""

# Test 8: Workflow Creation
echo -e "${BLUE}8️⃣  Testing Workflow Creation${NC}"
WORKFLOW_RESP=$(curl -s -X POST "$API_URL/workflow/create" \
  -H "Content-Type: application/json" \
  -d '{
    "assessment_id": "ASSESS-TEST-001",
    "submission": {
      "text": "Advanced international English proficiency demonstrated through complex sentence structures and sophisticated vocabulary selection."
    }
  }')
WORKFLOW_ID=$(echo "$WORKFLOW_RESP" | jq -r '.workflow_id')
echo "$WORKFLOW_RESP" | jq .
echo ""

# Test 9: Get Workflow State
echo -e "${BLUE}9️⃣  Testing Get Workflow State${NC}"
if [ "$WORKFLOW_ID" != "null" ]; then
  curl -s "$API_URL/workflow/$WORKFLOW_ID" | jq .
else
  echo "⚠️  No workflow_id from creation"
fi
echo ""

# Test 10: Metrics
echo -e "${BLUE}🔟 Testing Metrics${NC}"
curl -s "$API_URL/metrics" | jq .
echo ""

echo -e "${GREEN}✅ Test suite complete!${NC}"
echo ""
echo "📚 For interactive API docs, visit: $API_URL/docs"
echo "📊 For OpenAPI schema, visit: $API_URL/openapi.json"
