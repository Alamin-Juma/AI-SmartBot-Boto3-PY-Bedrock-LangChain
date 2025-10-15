#!/bin/bash

# Payment Smart Bot - Test Script
# This script runs a complete payment flow test against your deployed API

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get API endpoint from Terraform output
echo -e "${BLUE}🔍 Getting API endpoint from Terraform...${NC}"
cd "$(dirname "$0")/../terraform"
API_ENDPOINT=$(terraform output -raw api_endpoint 2>/dev/null)

if [ -z "$API_ENDPOINT" ]; then
    echo -e "${RED}❌ Error: Could not get API endpoint from Terraform${NC}"
    echo -e "${YELLOW}💡 Make sure you've deployed with: terraform apply${NC}"
    exit 1
fi

echo -e "${GREEN}✅ API Endpoint: $API_ENDPOINT${NC}"
echo ""

# Generate unique session ID
SESSION_ID="test-$(date +%s)"
echo -e "${BLUE}📝 Session ID: $SESSION_ID${NC}"
echo ""

# Helper function to make API calls
make_request() {
    local message="$1"
    local step="$2"
    
    echo -e "${YELLOW}➤ Step $step: $message${NC}"
    
    response=$(curl -s -X POST "$API_ENDPOINT" \
        -H 'Content-Type: application/json' \
        -d "{\"sessionId\": \"$SESSION_ID\", \"message\": \"$message\"}")
    
    echo -e "${GREEN}Bot Response:${NC}"
    echo "$response" | jq -r '.response' 2>/dev/null || echo "$response"
    echo ""
    
    # Wait a moment between requests
    sleep 2
}

echo -e "${BLUE}🤖 Starting Payment Flow Test...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Test flow
make_request "I need to make a payment" "1/6"
make_request "Jane Doe" "2/6"
make_request "4242424242424242" "3/6"
make_request "12/27" "4/6"
make_request "456" "5/6"
make_request "confirm" "6/6"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ Test flow completed!${NC}"
echo ""
echo -e "${YELLOW}📊 Expected behavior:${NC}"
echo "  - Steps 1-5: Bot collects payment information"
echo "  - Step 6: Bot shows Stripe validation error (raw cards blocked in test mode)"
echo ""
echo -e "${YELLOW}💡 This is expected! In production:${NC}"
echo "  - Use Stripe Elements on frontend to tokenize cards"
echo "  - Send token to backend (not raw card number)"
echo ""
echo -e "${BLUE}📚 View logs:${NC}"
echo "  aws logs tail /aws/lambda/payment-smart-bot-handler-dev --since 5m"
echo ""
echo -e "${BLUE}🔍 Check DynamoDB session:${NC}"
echo "  aws dynamodb get-item \\"
echo "    --table-name payment-smart-bot-sessions-dev \\"
echo "    --key '{\"sessionId\": {\"S\": \"$SESSION_ID\"}}'"
echo ""
