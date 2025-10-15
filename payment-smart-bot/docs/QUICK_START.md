# Payment Smart Bot - Quick Start Guide

## ⚡ 5-Minute Deployment

### 1. Prerequisites

- Python 3.11+, Terraform, AWS CLI
- AWS account with Bedrock model access enabled
- Stripe test API key

### 2. Configuration

```bash
cd payment-smart-bot/terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`:
```hcl
stripe_secret_key = "sk_test_YOUR_KEY_HERE"
```

### 3. Deploy

```bash
# Build Lambda package
python build_lambda.py

# Initialize and deploy
terraform init
terraform apply -auto-approve
```

### 4. Test

Replace `YOUR_API_ENDPOINT` with output from Terraform:

```bash
# Get API endpoint
terraform output api_endpoint

# Test the bot
curl -X POST 'YOUR_API_ENDPOINT' \
  -H 'Content-Type: application/json' \
  -d '{"sessionId": "test-001", "message": "I want to make a payment"}'
```

---

## 🔄 Redeployment (After Code Changes)

```bash
# Rebuild and redeploy in one command
python build_lambda.py && terraform apply -auto-approve
```

---

## 🧪 Complete Test Flow

```bash
# Replace YOUR_API_ENDPOINT with your actual endpoint
API_ENDPOINT="https://XXXXX.execute-api.us-east-1.amazonaws.com/dev/chat"

# Step 1: Initiate
curl -X POST "$API_ENDPOINT" \
  -H 'Content-Type: application/json' \
  -d '{"sessionId": "test-001", "message": "I need to make a payment"}'

# Step 2: Name
curl -X POST "$API_ENDPOINT" \
  -H 'Content-Type: application/json' \
  -d '{"sessionId": "test-001", "message": "Jane Doe"}'

# Step 3: Card
curl -X POST "$API_ENDPOINT" \
  -H 'Content-Type: application/json' \
  -d '{"sessionId": "test-001", "message": "4242424242424242"}'

# Step 4: Expiry
curl -X POST "$API_ENDPOINT" \
  -H 'Content-Type: application/json' \
  -d '{"sessionId": "test-001", "message": "12/27"}'

# Step 5: CVV
curl -X POST "$API_ENDPOINT" \
  -H 'Content-Type: application/json' \
  -d '{"sessionId": "test-001", "message": "456"}'

# Step 6: Confirm
curl -X POST "$API_ENDPOINT" \
  -H 'Content-Type: application/json' \
  -d '{"sessionId": "test-001", "message": "confirm"}'
```

---

## 📊 View Logs

```bash
# Lambda logs (last 5 minutes)
aws logs tail /aws/lambda/payment-smart-bot-handler-dev --since 5m

# Follow live logs
aws logs tail /aws/lambda/payment-smart-bot-handler-dev --follow
```

**On Windows Git Bash:**
```bash
MSYS_NO_PATHCONV=1 aws logs tail /aws/lambda/payment-smart-bot-handler-dev --follow
```

---

## 🔧 Common Issues

### "No module named 'stripe'"
```bash
python build_lambda.py
terraform apply -auto-approve
```

### "ValidationException: Invocation of model not supported"
Edit `terraform.tfvars`:
```hcl
bedrock_model_id = "us.meta.llama3-2-1b-instruct-v1:0"  # Must use inference profile
```

### "AccessDeniedException" from Bedrock
1. Enable Bedrock model in AWS Console
2. Check IAM policy includes inference profiles

---

## 🗑️ Cleanup

```bash
terraform destroy
```

---

## 📚 Full Documentation

See [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for detailed instructions.

---

## 🎯 API Endpoint Structure

```
POST /chat
Content-Type: application/json

{
  "sessionId": "unique-session-id",
  "message": "user message"
}
```

**Response:**
```json
{
  "response": "bot response text",
  "status": "collecting|confirming|completed|error",
  "sessionId": "unique-session-id"
}
```

---

## 🔑 Key Files

| File | Purpose |
|------|---------|
| `terraform/terraform.tfvars` | Configuration (Stripe key, etc.) |
| `terraform/build_lambda.py` | Build Lambda package |
| `lambda/payment_handler.py` | Main Lambda function |
| `terraform/main.tf` | Infrastructure definition |

---

## 💡 Tips

- Use unique `sessionId` for each conversation
- Sessions expire after 1 hour
- Bot supports cancellation: "cancel", "quit", "exit"
- Stripe raw cards blocked in test mode (expected)
- Cross-region inference provides higher throughput

---

**Quick Links:**
- [Full Deployment Guide](./DEPLOYMENT_GUIDE.md)
- [AWS Bedrock Inference Profiles](https://docs.aws.amazon.com/bedrock/latest/userguide/cross-region-inference.html)
- [Stripe Testing](https://stripe.com/docs/testing)
