#!/bin/bash

echo "==================================="
echo "Testing Insights API Endpoints"
echo "==================================="

BASE_URL="http://localhost:8000"

echo -e "\n1. GET /api/v1/insights/ - List insights"
curl -s "$BASE_URL/api/v1/insights/" | jq .

echo -e "\n2. GET /api/v1/insights/2 - Client detail"
curl -s "$BASE_URL/api/v1/insights/2" | jq .

echo -e "\n3. GET /api/v1/insights/stats/global - Global stats"
curl -s "$BASE_URL/api/v1/insights/stats/global" | jq .

echo -e "\n4. GET /api/v1/insights/search/?q=machine - Search"
curl -s "$BASE_URL/api/v1/insights/search/?q=machine" | jq .

echo -e "\n5. GET /api/v1/insights/latest/ - Latest insights"
curl -s "$BASE_URL/api/v1/insights/latest/" | jq .

echo -e "\n==================================="
echo "Tests completed"
echo "==================================="
