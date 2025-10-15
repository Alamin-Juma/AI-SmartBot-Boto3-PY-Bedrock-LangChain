#!/bin/bash
# Payment Bot Backend Testing Script
# Run this after deploying with Terraform

set -e  # Exit on error

echo "🚀 Payment Smart Bot - Backend Testing"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command -v terraform &> /dev/null; then
    echo -e "${RED}❌ Terraform not found. Please install: https://www.terraform.io/downloads${NC}"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found. Please install: https://aws.amazon.com/cli/${NC}"
    exit 1
fi

if ! command -v curl &> /dev/null; then
    echo -e "${RED}❌ curl not found. Please install curl.${NC}"
    exit 1
fi

if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}⚠️  jq not found. Install for prettier output: apt-get install jq${NC}"
    HAS_JQ=false
else
    HAS_JQ=true
fi

echo -e "${GREEN}✅ All prerequisites met${NC}"
echo ""

# Check AWS credentials
echo "🔐 Verifying AWS credentials..."
if aws sts get-caller-identity > /dev/null 2>&1; then
    ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
    echo -e "${GREEN}✅ Connected to AWS account: ${ACCOUNT_ID}${NC}"
else
    echo -e "${RED}❌ AWS credentials not configured. Run: aws configure${NC}"
    exit 1
fi
echo ""

# Check Bedrock access
echo "🤖 Checking Bedrock model access..."
if aws bedrock get-foundation-model \
    --model-identifier meta.llama3-2-1b-instruct-v1:0 \
    --region us-east-1 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Bedrock Llama 3.2 1B model accessible${NC}"
else
    echo -e "${RED}❌ Bedrock model not accessible. Enable in console:${NC}"
    echo "   https://console.aws.amazon.com/bedrock/home?region=us-east-1#/modelaccess"
    exit 1
fi
echo ""

# Navigate to terraform directory
cd "$(dirname "$0")/../terraform"

# Check if terraform.tfvars exists
if [ ! -f "terraform.tfvars" ]; then
    echo -e "${RED}❌ terraform.tfvars not found${NC}"
    echo ""
    echo "Please create it:"
    echo "  1. Copy: cp terraform.tfvars.example terraform.tfvars"
    echo "  2. Edit and add your Stripe test key (sk_test_...)"
    echo "  3. Get key from: https://dashboard.stripe.com/test/apikeys"
    echo ""
    exit 1
fi

# Check if Stripe key is configured
if grep -q "YOUR_STRIPE_SECRET_KEY_HERE" terraform.tfvars; then
    echo -e "${RED}❌ Stripe key not configured in terraform.tfvars${NC}"
    echo ""
    echo "Please edit terraform.tfvars and replace:"
    echo "  stripe_secret_key = \"sk_test_YOUR_STRIPE_SECRET_KEY_HERE\""
    echo ""
    echo "Get your test key from: https://dashboard.stripe.com/test/apikeys"
    echo ""
    exit 1
fi

echo -e "${GREEN}✅ terraform.tfvars configured${NC}"
echo ""

# Initialize Terraform if needed
if [ ! -d ".terraform" ]; then
    echo "📦 Initializing Terraform..."
    terraform init
    echo ""
fi

# Validate configuration
echo "✅ Validating Terraform configuration..."
terraform validate
echo ""

# Plan deployment
echo "📋 Planning infrastructure deployment..."
echo ""
terraform plan -out=tfplan
echo ""

# Ask for confirmation
read -p "🚀 Deploy infrastructure? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Deployment cancelled."
    exit 0
fi

# Apply Terraform
echo ""
echo "🏗️  Deploying infrastructure..."
terraform apply tfplan
rm tfplan
echo ""

# Get outputs
echo "📊 Retrieving deployment information..."
API_ENDPOINT=$(terraform output -raw api_endpoint)
LAMBDA_NAME=$(terraform output -raw lambda_function_name)
TABLE_NAME=$(terraform output -raw dynamodb_table_name)
echo ""

echo -e "${GREEN}✅ Deployment successful!${NC}"
echo ""
echo "📝 Infrastructure Details:"
echo "   API Endpoint: $API_ENDPOINT"
echo "   Lambda Function: $LAMBDA_NAME"
echo "   DynamoDB Table: $TABLE_NAME"
echo ""

# Wait for API to be ready
echo "⏳ Waiting for API Gateway to be ready..."
sleep 5

# Test 1: Initial request
echo ""
echo "🧪 Test 1: Initial payment request"
echo "=================================="
echo ""

if [ "$HAS_JQ" = true ]; then
    curl -X POST "$API_ENDPOINT" \
      -H "Content-Type: application/json" \
      -d '{"sessionId": "test-001", "message": "I want to make a payment"}' | jq
else
    curl -X POST "$API_ENDPOINT" \
      -H "Content-Type: application/json" \
      -d '{"sessionId": "test-001", "message": "I want to make a payment"}'
fi

echo ""
echo ""
echo "✅ If you see a response asking for name, the API is working!"
echo ""

# Test 2: Provide name
echo "🧪 Test 2: Providing name"
echo "========================="
echo ""

sleep 2
if [ "$HAS_JQ" = true ]; then
    curl -X POST "$API_ENDPOINT" \
      -H "Content-Type: application/json" \
      -d '{"sessionId": "test-001", "message": "John Doe"}' | jq
else
    curl -X POST "$API_ENDPOINT" \
      -H "Content-Type: application/json" \
      -d '{"sessionId": "test-001", "message": "John Doe"}'
fi

echo ""
echo ""

# Test 3: Valid card
echo "🧪 Test 3: Valid card number"
echo "============================"
echo ""

sleep 2
if [ "$HAS_JQ" = true ]; then
    curl -X POST "$API_ENDPOINT" \
      -H "Content-Type: application/json" \
      -d '{"sessionId": "test-001", "message": "4111111111111111"}' | jq
else
    curl -X POST "$API_ENDPOINT" \
      -H "Content-Type: application/json" \
      -d '{"sessionId": "test-001", "message": "4111111111111111"}'
fi

echo ""
echo ""

# Test 4: Expiry
echo "🧪 Test 4: Expiry date"
echo "======================"
echo ""

sleep 2
if [ "$HAS_JQ" = true ]; then
    curl -X POST "$API_ENDPOINT" \
      -H "Content-Type: application/json" \
      -d '{"sessionId": "test-001", "message": "12/2028"}' | jq
else
    curl -X POST "$API_ENDPOINT" \
      -H "Content-Type: application/json" \
      -d '{"sessionId": "test-001", "message": "12/2028"}'
fi

echo ""
echo ""

# Test 5: CVV
echo "🧪 Test 5: CVV"
echo "=============="
echo ""

sleep 2
if [ "$HAS_JQ" = true ]; then
    curl -X POST "$API_ENDPOINT" \
      -H "Content-Type: application/json" \
      -d '{"sessionId": "test-001", "message": "123"}' | jq
else
    curl -X POST "$API_ENDPOINT" \
      -H "Content-Type: application/json" \
      -d '{"sessionId": "test-001", "message": "123"}'
fi

echo ""
echo ""

# Test 6: Confirm
echo "🧪 Test 6: Confirmation"
echo "======================="
echo ""

sleep 2
echo "Confirming payment (this will call Stripe API)..."
if [ "$HAS_JQ" = true ]; then
    RESULT=$(curl -X POST "$API_ENDPOINT" \
      -H "Content-Type: application/json" \
      -d '{"sessionId": "test-001", "message": "confirm"}')
    echo "$RESULT" | jq
    
    # Check if we got a payment token
    if echo "$RESULT" | jq -e '.response | contains("pm_")' > /dev/null; then
        echo ""
        echo -e "${GREEN}🎉 SUCCESS! Stripe payment token created!${NC}"
    fi
else
    curl -X POST "$API_ENDPOINT" \
      -H "Content-Type: application/json" \
      -d '{"sessionId": "test-001", "message": "confirm"}'
fi

echo ""
echo ""

# Check DynamoDB
echo "📊 Checking DynamoDB sessions..."
aws dynamodb scan \
  --table-name "$TABLE_NAME" \
  --region us-east-1 \
  --max-items 3 \
  --output table

echo ""
echo ""

# Check Lambda logs
echo "📜 Recent Lambda logs (last 5 minutes)..."
aws logs tail "/aws/lambda/$LAMBDA_NAME" --since 5m --format short

echo ""
echo ""

echo "=========================================="
echo "🎉 Backend Testing Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Review the logs above for any errors"
echo "  2. Check DynamoDB for session data"
echo "  3. Verify payment token (pm_...) was created"
echo "  4. Test with mock data: cd ../tests && ./run_mock_tests.sh"
echo "  5. Build frontend when ready"
echo ""
echo "Useful commands:"
echo "  • View logs: aws logs tail /aws/lambda/$LAMBDA_NAME --follow"
echo "  • Check sessions: aws dynamodb scan --table-name $TABLE_NAME"
echo "  • Destroy resources: cd terraform && terraform destroy"
echo ""
