# Payment Smart Bot - Deployment Guide

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Configuration](#configuration)
4. [Building the Lambda Package](#building-the-lambda-package)
5. [Infrastructure Deployment](#infrastructure-deployment)
6. [Testing the API](#testing-the-api)
7. [Making Changes and Redeployment](#making-changes-and-redeployment)
8. [Monitoring and Logs](#monitoring-and-logs)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Tools

- **Python 3.11+** - Lambda runtime version
- **Terraform 1.0+** - Infrastructure as Code tool
- **AWS CLI** - Configured with credentials
- **Stripe Account** - Test API key required
- **Git Bash** or **PowerShell** (Windows) / **Bash** (Linux/Mac)

### AWS Requirements

- AWS Account with appropriate permissions
- IAM permissions to create:
  - Lambda functions
  - API Gateway
  - DynamoDB tables
  - CloudWatch logs and alarms
  - Secrets Manager secrets
  - KMS keys
  - IAM roles and policies
- **Amazon Bedrock Model Access**: Enable `meta.llama3-2-1b-instruct-v1:0` in your AWS region

### Enable Bedrock Model Access

1. Go to AWS Console → Amazon Bedrock → Model Access
2. Click "Manage model access"
3. Enable: **Meta Llama 3.2 1B Instruct**
4. Submit access request (usually instant approval)

---

## Initial Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/Alamin-Juma/AI-SmartBot-Boto3-PY-Bedrock-LangChain.git
cd AI-SmartBot-Boto3-PY-Bedrock-LangChain/payment-smart-bot
```

### Step 2: Verify Directory Structure

```
payment-smart-bot/
├── lambda/
│   └── payment_handler.py          # Main Lambda function
├── terraform/
│   ├── main.tf                     # Terraform configuration
│   ├── variables.tf                # Input variables
│   ├── outputs.tf                  # Output values
│   ├── lambda.tf                   # Lambda configuration
│   ├── api_gateway.tf              # API Gateway setup
│   ├── dynamodb.tf                 # DynamoDB table
│   ├── iam.tf                      # IAM roles and policies
│   ├── secrets.tf                  # Secrets Manager
│   ├── monitoring.tf               # CloudWatch alarms
│   ├── build_lambda.py             # Lambda build script
│   └── terraform.tfvars.example    # Example configuration
├── docs/
│   └── DEPLOYMENT_GUIDE.md         # This file
└── requirements.txt                # Python dependencies
```

---

## Configuration

### Step 1: Get Stripe Test API Key

1. Go to [Stripe Dashboard](https://dashboard.stripe.com/test/apikeys)
2. Copy your **Secret key** (starts with `sk_test_...`)
3. Keep this handy for the next step

### Step 2: Create `terraform.tfvars`

Navigate to the terraform directory:

```bash
cd terraform
```

Create `terraform.tfvars` from the example:

```bash
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your values:

```hcl
# AWS Configuration
aws_region  = "us-east-1"
environment = "dev"

# Project Settings
project_name      = "payment-smart-bot"
bedrock_model_id = "us.meta.llama3-2-1b-instruct-v1:0"  # Inference profile ID

# Stripe API Key (REQUIRED)
stripe_secret_key = "sk_test_YOUR_STRIPE_TEST_KEY_HERE"

# Lambda Configuration
lambda_memory_size = 512
lambda_timeout     = 60

# DynamoDB Configuration
dynamodb_billing_mode = "PAY_PER_REQUEST"

# Session Configuration
session_ttl_hours = 1

# Monitoring
bedrock_token_threshold = 100000

# Tags
tags = {
  Application = "PaymentBot"
  Environment = "dev"
  Team        = "DevOps"
  CostCenter  = "Engineering"
}
```

**Important:** Replace `sk_test_YOUR_STRIPE_TEST_KEY_HERE` with your actual Stripe test key!

---

## Building the Lambda Package

### Why Build?

The Lambda function requires Python dependencies (stripe, boto3, etc.) to be packaged with the code. Terraform's basic `archive_file` doesn't install dependencies, so we use a custom build script.

### Step 1: Build the Lambda Deployment Package

From the terraform directory:

```bash
python build_lambda.py
```

**Expected Output:**

```
🔨 Building Lambda deployment package...
🧹 Cleaning up previous build...
📁 Creating build directory...
📦 Installing Python dependencies...
📄 Copying Lambda function code...
🗑️  Removing unnecessary files...
📦 Creating deployment package...

✅ Lambda deployment package created successfully!
📊 Package size: 20.14 MB
📍 Location: C:\dev\personal\AI-SmartBots-Boto3-Bedrock-LLMs\payment-smart-bot\terraform\lambda_function.zip

🎉 Build complete!
```

### What the Build Script Does

1. **Cleans up** previous build artifacts
2. **Installs dependencies** from `requirements.txt` to a temporary directory:
   - boto3 (AWS SDK)
   - stripe (Payment processing)
   - python-dateutil (Date handling)
   - python-dotenv (Environment variables)
3. **Copies** `payment_handler.py` to the build directory
4. **Removes** unnecessary files (`__pycache__`, `.pyc`, tests)
5. **Creates ZIP** file: `lambda_function.zip` (~20 MB)

### Build Script Location

```
terraform/build_lambda.py
```

---

## Infrastructure Deployment

### Step 1: Initialize Terraform

Initialize Terraform providers and modules:

```bash
terraform init
```

**Expected Output:**

```
Initializing the backend...
Initializing provider plugins...
- Finding latest version of hashicorp/aws...
- Installing hashicorp/aws v5.x.x...

Terraform has been successfully initialized!
```

### Step 2: Review the Deployment Plan

Preview what resources will be created:

```bash
terraform plan
```

**Expected Resources (30 total):**

- 1 Lambda function
- 1 API Gateway REST API
- 1 API Gateway deployment and stage
- 1 DynamoDB table
- 1 Secrets Manager secret
- 1 KMS key
- 5 IAM roles and policies
- 3 CloudWatch log groups
- 3 CloudWatch metric alarms
- Various API Gateway resources (methods, integrations, etc.)

### Step 3: Deploy the Infrastructure

Apply the Terraform configuration:

```bash
terraform apply
```

Or auto-approve to skip confirmation:

```bash
terraform apply -auto-approve
```

**Expected Output:**

```
Apply complete! Resources: 30 added, 0 changed, 0 destroyed.

Outputs:

api_endpoint = "https://XXXXX.execute-api.us-east-1.amazonaws.com/dev/chat"
dynamodb_table_name = "payment-smart-bot-sessions-dev"
lambda_function_name = "payment-smart-bot-handler-dev"
cloudwatch_log_group_lambda = "/aws/lambda/payment-smart-bot-handler-dev"
```

**Deployment Time:** Approximately 2-3 minutes

### Step 4: Note Your API Endpoint

Save the `api_endpoint` output - you'll use it for testing:

```bash
terraform output api_endpoint
```

Example output:
```
"https://osmgkvun82.execute-api.us-east-1.amazonaws.com/dev/chat"
```

---

## Testing the API

### Test Overview

The payment bot follows a conversational flow:

1. **Initial Request** → Bot asks for name
2. **Provide Name** → Bot asks for card number
3. **Provide Card** → Bot asks for expiry date
4. **Provide Expiry** → Bot asks for CVV
5. **Provide CVV** → Bot asks for confirmation
6. **Confirm** → Bot processes payment

### Complete Test Flow

Replace `<YOUR_API_ENDPOINT>` with your actual API endpoint from Terraform outputs.

#### Step 1: Initiate Payment

```bash
curl -X POST 'https://osmgkvun82.execute-api.us-east-1.amazonaws.com/dev/chat' \
  -H 'Content-Type: application/json' \
  -d '{"sessionId": "test-001", "message": "I need to make a payment"}'
```

**Expected Response:**

```json
{
  "response": "Thank you for choosing our service. To complete your payment, I need to collect some information from you...\n\nLet's get started. Here's what I need from you:\n\n1. **Name on card**: Can you please tell me your full name as it appears on your card?",
  "status": "collecting",
  "sessionId": "test-001"
}
```

#### Step 2: Provide Cardholder Name

```bash
curl -X POST 'https://osmgkvun82.execute-api.us-east-1.amazonaws.com/dev/chat' \
  -H 'Content-Type: application/json' \
  -d '{"sessionId": "test-001", "message": "Jane Doe"}'
```

**Expected Response:**

```json
{
  "response": "Thank you, Jane Doe. Your full name is now masked for security purposes.\n\nNext, I need to verify your card details...\n\n1. **Card number**: Can you please tell me the 16-digit card number?",
  "status": "collecting",
  "sessionId": "test-001"
}
```

#### Step 3: Provide Card Number

Use Stripe's test card number:

```bash
curl -X POST 'https://osmgkvun82.execute-api.us-east-1.amazonaws.com/dev/chat' \
  -H 'Content-Type: application/json' \
  -d '{"sessionId": "test-001", "message": "4242424242424242"}'
```

**Expected Response:**

```json
{
  "response": "Thank you, Jane Doe. Your card details are now masked for security purposes.\n\nNext, I need to confirm your card's expiration date. Can you please tell me the expiration date (MM/YY format)?",
  "status": "collecting",
  "sessionId": "test-001"
}
```

#### Step 4: Provide Expiry Date

```bash
curl -X POST 'https://osmgkvun82.execute-api.us-east-1.amazonaws.com/dev/chat' \
  -H 'Content-Type: application/json' \
  -d '{"sessionId": "test-001", "message": "12/27"}'
```

**Expected Response:**

```json
{
  "response": "Thank you, Jane Doe. Your card details are now masked for security purposes.\n\nNext, I need to confirm your card's CVV (3 digits)...",
  "status": "collecting",
  "sessionId": "test-001"
}
```

#### Step 5: Provide CVV

```bash
curl -X POST 'https://osmgkvun82.execute-api.us-east-1.amazonaws.com/dev/chat' \
  -H 'Content-Type: application/json' \
  -d '{"sessionId": "test-001", "message": "456"}'
```

**Expected Response:**

```json
{
  "response": "Please confirm:\nName: Jane Doe\nCard: ****4242\nExpiry: 12/27\nCVV: ***\nReply 'confirm' to proceed or 'cancel' to start over.",
  "status": "confirming",
  "sessionId": "test-001"
}
```

#### Step 6: Confirm Payment

```bash
curl -X POST 'https://osmgkvun82.execute-api.us-east-1.amazonaws.com/dev/chat' \
  -H 'Content-Type: application/json' \
  -d '{"sessionId": "test-001", "message": "confirm"}'
```

**Expected Response:**

```json
{
  "response": "❌ Payment processing failed: Sending credit card numbers directly to the Stripe API is generally unsafe. We suggest you use test tokens...",
  "status": "error",
  "sessionId": "test-001"
}
```

**Note:** This error is **expected behavior**. Stripe requires using test tokens or Stripe Elements in test mode for security. In production, you would tokenize cards on the frontend using Stripe.js.

### Test Cancellation Flow

At any step, you can cancel:

```bash
curl -X POST 'https://osmgkvun82.execute-api.us-east-1.amazonaws.com/dev/chat' \
  -H 'Content-Type: application/json' \
  -d '{"sessionId": "test-002", "message": "I want to make a payment"}'

# Then cancel
curl -X POST 'https://osmgkvun82.execute-api.us-east-1.amazonaws.com/dev/chat' \
  -H 'Content-Type: application/json' \
  -d '{"sessionId": "test-002", "message": "cancel"}'
```

**Cancellation Keywords:** cancel, quit, exit, stop, nevermind, forget it

---

## Making Changes and Redeployment

### Scenario 1: Code Changes Only

If you modify `lambda/payment_handler.py`:

#### Step 1: Rebuild Lambda Package

```bash
python '/c/dev/personal/AI-SmartBots-Boto3-Bedrock-LLMs/payment-smart-bot/terraform/build_lambda.py'
```

#### Step 2: Redeploy Lambda

```bash
cd /c/dev/personal/AI-SmartBots-Boto3-Bedrock-LLMs/payment-smart-bot/terraform
terraform apply -auto-approve
```

Terraform will detect the changed ZIP file and update only the Lambda function.

### Scenario 2: Infrastructure Changes

If you modify Terraform files (`*.tf`):

#### Step 1: Review Changes

```bash
terraform plan
```

#### Step 2: Apply Changes

```bash
terraform apply
```

### Scenario 3: Dependency Changes

If you modify `requirements.txt`:

#### Step 1: Rebuild Package

```bash
python build_lambda.py
```

#### Step 2: Redeploy

```bash
terraform apply -auto-approve
```

### Quick Redeployment Command

For rapid iterations:

```bash
# One-liner for code changes
python build_lambda.py && terraform apply -auto-approve
```

---

## Monitoring and Logs

### CloudWatch Logs

#### View Lambda Logs

```bash
# Using AWS CLI
aws logs tail /aws/lambda/payment-smart-bot-handler-dev --follow

# View last 5 minutes
aws logs tail /aws/lambda/payment-smart-bot-handler-dev --since 5m
```

**On Windows Git Bash:**

```bash
# Prevent path conversion
MSYS_NO_PATHCONV=1 aws logs tail /aws/lambda/payment-smart-bot-handler-dev --follow
```

#### View API Gateway Logs

```bash
aws logs tail /aws/apigateway/payment-smart-bot-dev --follow
```

### CloudWatch Alarms

The deployment includes three alarms:

1. **Lambda Errors** - Triggers when Lambda function errors occur
2. **Lambda Duration** - Triggers when execution time > 45 seconds
3. **Bedrock Token Usage** - Triggers when token usage > 100,000 per hour

#### Check Alarm Status

```bash
aws cloudwatch describe-alarms \
  --alarm-names \
    payment-smart-bot-lambda-errors-dev \
    payment-smart-bot-lambda-duration-dev \
    payment-smart-bot-bedrock-token-usage-dev
```

### DynamoDB Sessions

#### View Active Sessions

```bash
aws dynamodb scan \
  --table-name payment-smart-bot-sessions-dev \
  --limit 10
```

#### Get Specific Session

```bash
aws dynamodb get-item \
  --table-name payment-smart-bot-sessions-dev \
  --key '{"sessionId": {"S": "test-001"}}'
```

### X-Ray Tracing

X-Ray is enabled for the Lambda function. View traces in AWS Console:

1. Go to AWS X-Ray Console
2. Select Service Map
3. Click on `payment-smart-bot-handler-dev`

---

## Troubleshooting

### Issue 1: "No module named 'stripe'" Error

**Cause:** Lambda package doesn't include dependencies.

**Solution:**

```bash
# Rebuild the Lambda package
python build_lambda.py

# Redeploy
terraform apply -auto-approve
```

### Issue 2: "AccessDeniedException" from Bedrock

**Cause:** Bedrock model not enabled or IAM permissions missing.

**Solutions:**

1. **Enable Bedrock Model:**
   - Go to AWS Console → Bedrock → Model Access
   - Enable "Meta Llama 3.2 1B Instruct"

2. **Check IAM Policy:**
   - Verify Lambda role has `bedrock:Converse` permission
   - Resource ARN must include inference profiles

### Issue 3: "ValidationException: Invocation of model ID not supported"

**Cause:** Using direct model ID instead of inference profile ID.

**Solution:**

Edit `terraform.tfvars`:

```hcl
# ❌ Wrong - Direct model ID
bedrock_model_id = "meta.llama3-2-1b-instruct-v1:0"

# ✅ Correct - Inference profile ID
bedrock_model_id = "us.meta.llama3-2-1b-instruct-v1:0"
```

Then redeploy:

```bash
terraform apply -auto-approve
```

### Issue 4: "Access Denied to foundation-model in us-west-2"

**Cause:** Cross-region inference routes to different regions, but IAM policy only allows specific region.

**Solution:**

Check `terraform/iam.tf` has wildcard region:

```hcl
Resource = [
  "arn:aws:bedrock:*::foundation-model/*",  # Note the * for region
  "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:inference-profile/*"
]
```

### Issue 5: API Returns 500 Internal Server Error

**Check Lambda Logs:**

```bash
MSYS_NO_PATHCONV=1 aws logs tail /aws/lambda/payment-smart-bot-handler-dev --since 5m
```

**Common Causes:**

- Missing Stripe API key
- Invalid Bedrock model ID
- Python syntax errors
- Missing dependencies

### Issue 6: Stripe "Raw Card Not Allowed" Error

**This is expected behavior!** Stripe requires tokenization for security.

**For Testing:**

The bot correctly shows this error message. In production:

1. Use Stripe Elements on frontend
2. Tokenize card client-side
3. Send token to backend (not raw card)

### Issue 7: Session Not Persisting

**Check DynamoDB:**

```bash
aws dynamodb get-item \
  --table-name payment-smart-bot-sessions-dev \
  --key '{"sessionId": {"S": "YOUR_SESSION_ID"}}'
```

**Common Causes:**

- Session expired (TTL = 1 hour by default)
- DynamoDB IAM permissions missing
- Different sessionId used

---

## Key Configuration Files

### terraform.tfvars

```hcl
# Main configuration file
# Location: terraform/terraform.tfvars
# Required: stripe_secret_key
```

### build_lambda.py

```python
# Lambda package builder
# Location: terraform/build_lambda.py
# Run: python build_lambda.py
```

### payment_handler.py

```python
# Main Lambda function
# Location: lambda/payment_handler.py
# Handles: Bedrock, Stripe, DynamoDB
```

### requirements.txt

```
# Python dependencies
boto3>=1.28.0
stripe>=7.0.0
python-dateutil>=2.8.0
python-dotenv>=1.0.0
```

---

## Production Deployment Checklist

- [ ] Change `environment = "prod"` in terraform.tfvars
- [ ] Use production Stripe API key (`sk_live_...`)
- [ ] Update `bedrock_model_id` to production model
- [ ] Increase `lambda_timeout` if needed
- [ ] Set up SNS topic for alarm notifications
- [ ] Configure API Gateway custom domain
- [ ] Enable API Gateway access logging
- [ ] Set up VPC for Lambda (if required)
- [ ] Review and adjust CloudWatch alarm thresholds
- [ ] Implement API key or OAuth authentication
- [ ] Set up DynamoDB backups
- [ ] Configure KMS key rotation
- [ ] Review IAM permissions (principle of least privilege)
- [ ] Enable AWS WAF for API Gateway
- [ ] Set up CI/CD pipeline
- [ ] Implement frontend with Stripe Elements

---

## Architecture Summary

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ POST /chat
       │
┌──────▼──────────────────────────────────────────┐
│  API Gateway                                     │
│  - REST API                                      │
│  - /chat endpoint                                │
│  - CORS enabled                                  │
└──────┬──────────────────────────────────────────┘
       │ Invoke
       │
┌──────▼──────────────────────────────────────────┐
│  Lambda Function                                 │
│  - payment-smart-bot-handler-dev                 │
│  - Runtime: Python 3.11                          │
│  - Memory: 512 MB                                │
│  - Timeout: 60 seconds                           │
│  - X-Ray: Enabled                                │
└──┬───┬───┬───┬───────────────────────────────────┘
   │   │   │   │
   │   │   │   └──────────────────────┐
   │   │   │                          │
┌──▼───▼───▼─────────┐    ┌───────────▼───────────┐
│  Amazon Bedrock    │    │  DynamoDB             │
│  - Llama 3.2 1B    │    │  - Sessions table     │
│  - Inference       │    │  - TTL: 1 hour        │
│    Profile         │    │  - Pay-per-request    │
└────────────────────┘    └───────────────────────┘
         │
         │
┌────────▼────────────┐    ┌───────────────────────┐
│  Secrets Manager    │    │  Stripe API           │
│  - Stripe API key   │───▶│  - Payment tokens     │
│  - KMS encrypted    │    │  - Test mode          │
└─────────────────────┘    └───────────────────────┘
```

---

## Cost Estimate (Development)

**Monthly costs for moderate testing:**

| Service | Usage | Cost |
|---------|-------|------|
| Lambda | 10,000 requests | $0.00 (Free tier) |
| API Gateway | 10,000 requests | $0.04 |
| DynamoDB | Pay-per-request | ~$0.25 |
| Bedrock | 1M tokens | ~$0.15 |
| CloudWatch Logs | 5 GB | $2.50 |
| Secrets Manager | 1 secret | $0.40 |
| **Total** | | **~$3.34/month** |

**Note:** Actual costs may vary. Always monitor using AWS Cost Explorer.

---

## Additional Resources

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Bedrock Inference Profiles Guide](https://docs.aws.amazon.com/bedrock/latest/userguide/cross-region-inference.html)
- [Stripe API Documentation](https://stripe.com/docs/api)
- [Stripe Testing Cards](https://stripe.com/docs/testing)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)

---

## Support

For issues and questions:

- GitHub Issues: [Repository Issues](https://github.com/Alamin-Juma/AI-SmartBot-Boto3-PY-Bedrock-LangChain/issues)
- AWS Support: For Bedrock and infrastructure issues
- Stripe Support: For payment processing questions

---

**Last Updated:** October 15, 2025  
**Version:** 1.0.0
