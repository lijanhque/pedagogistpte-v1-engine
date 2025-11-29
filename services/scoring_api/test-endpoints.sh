#!/bin/bash
# PTE Scoring API — Route Testing Script
# Usage: bash test-endpoints.sh [base_url]
# Default base_url: http://localhost:8000

BASE_URL="${1:-http://localhost:8000}"
PASS_COUNT=0
FAIL_COUNT=0

echo "=========================================="
echo "PTE Scoring API — Route Test Suite"
echo "=========================================="
echo "Base URL: $BASE_URL"
echo ""

# Helper function to test endpoint
test_endpoint() {
  local test_name="$1"
  local method="$2"
  local endpoint="$3"
  local data="$4"
  local expected_status="${5:-200}"

  echo -n "Testing $test_name... "

  if [ "$method" = "GET" ]; then
    response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint")
  else
    response=$(curl -s -w "\n%{http_code}" -X "$method" \
      -H "Content-Type: application/json" \
      -d "$data" \
      "$BASE_URL$endpoint")
  fi

  status_code=$(echo "$response" | tail -1)
  body=$(echo "$response" | head -n -1)

  if [ "$status_code" = "$expected_status" ]; then
    echo "✓ PASS (Status: $status_code)"
    PASS_COUNT=$((PASS_COUNT + 1))
  else
    echo "✗ FAIL (Expected: $expected_status, Got: $status_code)"
    echo "  Response: $body"
    FAIL_COUNT=$((FAIL_COUNT + 1))
  fi
}

# Test 1: Health Check
echo "--- Level 1: CRUD & Basics ---"
test_endpoint "Health Check" "GET" "/health" "" 200

# Test 2: OpenAPI Docs
test_endpoint "OpenAPI Docs" "GET" "/docs" "" 200

# Test 3: Create Assessment
echo ""
echo "--- Level 1: Assessments ---"
test_endpoint "Create Assessment" "POST" "/assessments" \
  '{"student_id": "student_001", "metadata": {"test_type": "speaking"}}' 200

# Test 4: Score (Local)
echo ""
echo "--- Level 1 & 4: Scoring ---"
test_endpoint "Score Submission (Local)" "POST" "/score" \
  '{
    "assessment_id": "test_001",
    "student_id": "student_001",
    "text": "This is a comprehensive test of the PTE Academic scoring engine demonstrating fluency, lexical range, and grammatical accuracy across multiple dimensions.",
    "metadata": {"source": "test"}
  }' 200

# Test 5: Score with AI (may fail gracefully if no key)
test_endpoint "Score with AI Agent" "POST" "/score/with-ai" \
  '{
    "assessment_id": "test_ai_001",
    "student_id": "student_001",
    "text": "The rapid advancement of artificial intelligence has transformed multiple sectors. Machine learning models now enable unprecedented levels of automation.",
    "metadata": {}
  }' 200

# Test 6: Create Job
echo ""
echo "--- Level 2-3: Background Jobs & Orchestration ---"
test_endpoint "Create Scoring Job" "POST" "/jobs" \
  '{
    "assessment_id": "job_test_001",
    "text": "Speaking fluently is important for effective communication in professional environments.",
    "metadata": {"job_type": "scoring"}
  }' 200

# Test 7: Metrics
echo ""
echo "--- Admin & Monitoring ---"
test_endpoint "Get Metrics" "GET" "/metrics" "" 200

# Summary
echo ""
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo "✓ Passed: $PASS_COUNT"
echo "✗ Failed: $FAIL_COUNT"
echo "Total: $((PASS_COUNT + FAIL_COUNT))"

if [ $FAIL_COUNT -eq 0 ]; then
  echo ""
  echo "✓ All tests passed!"
  exit 0
else
  echo ""
  echo "✗ Some tests failed. Review output above."
  exit 1
fi
