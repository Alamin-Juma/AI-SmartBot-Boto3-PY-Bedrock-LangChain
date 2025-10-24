#!/bin/bash
#
# Quick Deployment Script for PCI-Compliant IVR Payment Bot
# Usage: ./deploy.sh [environment]
# Example: ./deploy.sh dev

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT="${1:-dev}"
STACK_NAME="payment-bot-poc-${ENVIRONMENT}"
REGION="${AWS_DEFAULT_REGION:-us-east-1}"
BEDROCK_MODEL="mistral.mistral-7b-instruct-v0:2"
STRIPE_SECRET_PARAM="/payment-bot/stripe-secret"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  PCI-Compliant IVR Payment Bot${NC}"
echo -e "${GREEN}  Deployment Script${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Environment: ${YELLOW}${ENVIRONMENT}${NC}"
echo -e "Region:      ${YELLOW}${REGION}${NC}"
echo -e "Stack:       ${YELLOW}${STACK_NAME}${NC}"
echo ""

# Step 1: Check prerequisites
echo -e "${YELLOW}[1/7] Checking prerequisites...${NC}"

if ! command -v aws &> /dev/null; then
    echo -e "${RED}ERROR: AWS CLI not found. Please install: pip install awscli${NC}"
    exit 1
fi

if ! command -v sam &> /dev/null; then
    echo -e "${RED}ERROR: SAM CLI not found. Please install: pip install aws-sam-cli${NC}"
    exit 1
fi

echo -e "${GREEN}✓ AWS CLI and SAM CLI found${NC}"

# Step 2: Verify AWS credentials
echo -e "${YELLOW}[2/7] Verifying AWS credentials...${NC}"

if ! aws sts get-caller-identity &> /dev/null; then
    echo -e "${RED}ERROR: AWS credentials not configured. Run: aws configure${NC}"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✓ Authenticated as Account: ${ACCOUNT_ID}${NC}"

# Step 3: Check Bedrock access
echo -e "${YELLOW}[3/7] Verifying Bedrock model access...${NC}"

if ! aws bedrock list-foundation-models --region $REGION &> /dev/null; then
    echo -e "${RED}ERROR: Bedrock not available in region ${REGION}${NC}"
    exit 1
fi

MISTRAL_AVAILABLE=$(aws bedrock list-foundation-models \
    --region $REGION \
    --query "modelSummaries[?modelId=='${BEDROCK_MODEL}'].modelId" \
    --output text)

if [ -z "$MISTRAL_AVAILABLE" ]; then
    echo -e "${RED}ERROR: Mistral 7B not available. Request access at:${NC}"
    echo -e "${YELLOW}https://console.aws.amazon.com/bedrock/ → Model access${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Mistral 7B Instruct available${NC}"

# Step 4: Verify Stripe secret
echo -e "${YELLOW}[4/7] Checking Stripe API key...${NC}"

if ! aws ssm get-parameter --name $STRIPE_SECRET_PARAM --region $REGION &> /dev/null; then
    echo -e "${YELLOW}⚠ Stripe secret not found in SSM Parameter Store${NC}"
    echo -e "${YELLOW}Please create it:${NC}"
    echo ""
    echo -e "aws ssm put-parameter \\"
    echo -e "  --name \"$STRIPE_SECRET_PARAM\" \\"
    echo -e "  --value \"sk_test_YOUR_STRIPE_KEY\" \\"
    echo -e "  --type SecureString \\"
    echo -e "  --region $REGION"
    echo ""
    read -p "Have you created the parameter? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Exiting. Please create Stripe secret first.${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✓ Stripe secret configured${NC}"

# Step 5: Build Lambda package
echo -e "${YELLOW}[5/7] Building Lambda deployment package...${NC}"

sam build --use-container

if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: SAM build failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Lambda package built successfully${NC}"

# Step 6: Deploy stack
echo -e "${YELLOW}[6/7] Deploying CloudFormation stack...${NC}"

sam deploy \
    --stack-name $STACK_NAME \
    --region $REGION \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
    --parameter-overrides \
        Environment=$ENVIRONMENT \
        BedrockModelId=$BEDROCK_MODEL \
        StripeSecretParam=$STRIPE_SECRET_PARAM \
    --no-confirm-changeset \
    --no-fail-on-empty-changeset

if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: Deployment failed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Stack deployed successfully${NC}"

# Step 7: Get outputs
echo -e "${YELLOW}[7/7] Retrieving deployment outputs...${NC}"

LAMBDA_ARN=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`PaymentBotFunctionArn`].OutputValue' \
    --output text)

AUDIT_BUCKET=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`AuditLogsBucketName`].OutputValue' \
    --output text)

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Deployment Complete! ✓${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Lambda Function ARN:${NC}"
echo -e "  $LAMBDA_ARN"
echo ""
echo -e "${YELLOW}Audit Logs Bucket:${NC}"
echo -e "  $AUDIT_BUCKET"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo -e "  1. Test locally:"
echo -e "     ${GREEN}sam local invoke PaymentBotFunction -e events/test-event.json${NC}"
echo ""
echo -e "  2. Configure Amazon Connect:"
echo -e "     - Add Lambda function: ${GREEN}$LAMBDA_ARN${NC}"
echo -e "     - Import contact flow from: ${GREEN}connect-flows/payment-bot-flow.json${NC}"
echo ""
echo -e "  3. Monitor logs:"
echo -e "     ${GREEN}sam logs -n PaymentBotFunction --stack-name $STACK_NAME --tail${NC}"
echo ""
echo -e "  4. View audit logs:"
echo -e "     ${GREEN}aws s3 ls s3://$AUDIT_BUCKET/audit/ --recursive${NC}"
echo ""
echo -e "${GREEN}Documentation: README.md | docs/ARCHITECTURE.md${NC}"
echo ""
