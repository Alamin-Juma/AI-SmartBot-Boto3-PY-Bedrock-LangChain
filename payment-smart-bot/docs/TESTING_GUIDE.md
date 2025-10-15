# Payment Backend Testing Guide 🧪

Step-by-step guide to test the payment bot backend infrastructure before building the frontend.

## Prerequisites Check

Before starting, verify you have:

```bash
# 1. AWS CLI configured
aws sts get-caller-identity
# Should show your account ID and IAM user

# 2. Terraform installed
terraform version
# Should be >= 1.5.0

# 3. Bedrock access enabled
aws bedrock list-foundation-models --region us-east-1 \
  --query "modelSummaries[?contains(modelId,'llama3-2-1b')].modelId"
# Should return: ["meta.llama3-2-1b-instruct-v1:0"]

# 4. Python installed (for local testing)
python --version
# Should be >= 3.11
```

## Step 1: Get Stripe Test Key

1. Go to https://dashboard.stripe.com/test/apikeys
2. Sign in or create free account
3. Copy the "Secret key" (starts with `sk_test_`)
4. Keep it handy - you'll add it to `terraform.tfvars`

## Step 2: Configure Terraform

```bash
cd /c/dev/personal/AI-SmartBots-Boto3-Bedrock-LLMs/payment-smart-bot/terraform

# Create config file from example
cp terraform.tfvars.example terraform.tfvars

# Edit the file
nano terraform.tfvars
```

**Edit `terraform.tfvars` with your values**:
```hcl
# REQUIRED: Add your Stripe test key
stripe_secret_key = "sk_test_YOUR_KEY_HERE"

# Optional: Keep defaults or customize
aws_region  = "us-east-1"
environment = "dev"
project_name = "payment-smart-bot"

# For testing, keep these small
lambda_memory_size = 512
lambda_timeout     = 30
api_throttle_rate  = 10
```

Save and exit (`Ctrl+X`, `Y`, `Enter` in nano).

## Step 3: Initialize Terraform

```bash
terraform init
```

**Expected output**:
```
Initializing the backend...
Initializing provider plugins...
- Finding hashicorp/aws versions matching "~> 5.0"...
- Finding hashicorp/archive versions matching "~> 2.4"...
- Installing hashicorp/aws v5.x.x...
- Installing hashicorp/archive v2.x.x...

Terraform has been successfully initialized!
```

**If you see errors**:
- `Error: No valid credential sources`: Run `aws configure`
- `Error: Failed to install provider`: Check internet connection

## Step 4: Validate Configuration

```bash
terraform validate
```

**Expected**:
```
Success! The configuration is valid.
```

## Step 5: Preview Deployment

```bash
terraform plan
```

**Review the output**:
- Should show ~20+ resources to create
- Look for: Lambda, API Gateway, DynamoDB, Secrets Manager, IAM roles, etc.
- Check estimated costs (should be minimal for dev)

**Sample output**:
```
Plan: 23 to add, 0 to change, 0 to destroy.

Changes to Outputs:
  + api_endpoint          = (known after apply)
  + lambda_function_name  = "payment-smart-bot-handler-dev"
  + dynamodb_table_name   = "payment-smart-bot-sessions-dev"
```

## Step 6: Deploy Infrastructure

```bash
terraform apply
```

Type `yes` when prompted.

**Deployment time**: ~2-3 minutes

**Watch for**:
- ✅ Green lines = resources being created
- ❌ Red lines = errors (note the message)

**On success, you'll see outputs**:
```
Apply complete! Resources: 23 added, 0 changed, 0 destroyed.

Outputs:

api_endpoint = "https://abc123xyz.execute-api.us-east-1.amazonaws.com/dev/chat"
lambda_function_name = "payment-smart-bot-handler-dev"
dynamodb_table_name = "payment-smart-bot-sessions-dev"
cloudwatch_log_group_lambda = "/aws/lambda/payment-smart-bot-handler-dev"
curl_test_command = "curl -X POST https://..."
```

**Save the `api_endpoint`** - you'll use it for testing!

## Step 7: Test API Endpoint

### Test 1: Initial Request

```bash
# Set your endpoint (get from terraform output)
export API_ENDPOINT=$(terraform output -raw api_endpoint)

# Send first message
curl -X POST $API_ENDPOINT \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "test-001",
    "message": "I want to make a payment"
  }'
```

**Expected response**:
```json
{
  "response": "Sure! Let's collect your payment info securely. What's the name on your card?",
  "status": "collecting",
  "sessionId": "test-001",
  "currentStep": "card"
}
```

✅ **If you see this, your API is working!**

### Test 2: Provide Name

```bash
curl -X POST $API_ENDPOINT \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "test-001",
    "message": "John Doe"
  }'
```

**Expected**:
```json
{
  "response": "Thanks, John Doe. Now, what's your card number?",
  "status": "collecting",
  "currentStep": "expiry"
}
```

### Test 3: Valid Card Number

```bash
curl -X POST $API_ENDPOINT \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "test-001",
    "message": "4111111111111111"
  }'
```

**Expected**: Bot asks for expiry date

### Test 4: Expiry Date

```bash
curl -X POST $API_ENDPOINT \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "test-001",
    "message": "12/2028"
  }'
```

**Expected**: Bot asks for CVV

### Test 5: CVV

```bash
curl -X POST $API_ENDPOINT \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "test-001",
    "message": "123"
  }'
```

**Expected**: Bot shows confirmation with masked data

### Test 6: Confirm Payment

```bash
curl -X POST $API_ENDPOINT \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "test-001",
    "message": "confirm"
  }'
```

**Expected**:
```json
{
  "response": "✅ Payment information collected successfully!",
  "status": "complete",
  "sessionId": "test-001"
}
```

## Step 8: Test Validation Logic

### Test Invalid Card (Luhn Failure)

```bash
curl -X POST $API_ENDPOINT \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "test-invalid",
    "message": "I want to pay"
  }'

# Then send invalid card
curl -X POST $API_ENDPOINT \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "test-invalid",
    "message": "1234567890123456"
  }'
```

**Expected**: Error message about invalid card

### Test Expired Date

```bash
curl -X POST $API_ENDPOINT \
  -H "Content-Type: application/json" \
  -d '{
    "sessionId": "test-expired",
    "message": "01/2020"
  }'
```

**Expected**: Error about expired date

## Step 9: Verify DynamoDB

```bash
# List sessions
aws dynamodb scan \
  --table-name payment-smart-bot-sessions-dev \
  --region us-east-1

# Get specific session
aws dynamodb get-item \
  --table-name payment-smart-bot-sessions-dev \
  --key '{"sessionId": {"S": "test-001"}}' \
  --region us-east-1
```

**Check for**:
- ✅ Sessions are being created
- ✅ Conversation history is stored
- ✅ Current step is tracked
- ⚠️ Sensitive data should be masked or absent

## Step 10: Check Lambda Logs

```bash
# Tail logs in real-time
aws logs tail /aws/lambda/payment-smart-bot-handler-dev --follow

# Or view recent logs
aws logs tail /aws/lambda/payment-smart-bot-handler-dev --since 10m
```

**Look for**:
- ✅ `Initializing AI SmartBot...` on cold start
- ✅ Bedrock API calls succeeding
- ✅ Card numbers are masked (`****1111`)
- ❌ No errors or exceptions

## Step 11: Verify Secrets Manager

```bash
# Check secret exists
aws secretsmanager describe-secret \
  --secret-id payment-smart-bot/stripe-key-dev \
  --region us-east-1

# Verify Lambda can access it (check logs for "fetching Stripe key")
aws logs filter-log-events \
  --log-group-name /aws/lambda/payment-smart-bot-handler-dev \
  --filter-pattern "Stripe key" \
  --region us-east-1
```

## Step 12: Test Mock Data

Run automated tests with the provided mock data:

```bash
cd /c/dev/personal/AI-SmartBots-Boto3-Bedrock-LLMs/payment-smart-bot/tests

# Install jq for JSON parsing (optional but helpful)
# Windows: choco install jq
# Mac: brew install jq
# Linux: apt-get install jq

# Test all mock cards
for i in {1..5}; do
  echo "Testing mock session $i..."
  curl -X POST $API_ENDPOINT \
    -H "Content-Type: application/json" \
    -d "{\"sessionId\": \"mock-00$i\", \"message\": \"I want to pay\"}" | jq
  sleep 2
done
```

## Step 13: Performance Test

```bash
# Simple load test (10 concurrent requests)
for i in {1..10}; do
  (curl -X POST $API_ENDPOINT \
    -H "Content-Type: application/json" \
    -d "{\"sessionId\": \"load-test-$i\", \"message\": \"test\"}" &)
done
wait

echo "Check CloudWatch for metrics..."
```

## Step 14: Cost Monitoring

```bash
# Check Lambda invocations
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=payment-smart-bot-handler-dev \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum \
  --region us-east-1

# Estimate cost for your tests
# Lambda invocations × $0.20 per 1M requests
# Bedrock tokens × $0.0001 per 1k tokens
# Should be <$0.01 for testing
```

## Troubleshooting

### Issue: API returns 502 Bad Gateway

**Check Lambda errors**:
```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/payment-smart-bot-handler-dev \
  --filter-pattern "ERROR" \
  --region us-east-1
```

**Common causes**:
- Lambda timeout (increase in `terraform.tfvars`)
- Missing IAM permissions (check `terraform plan` output)
- Bedrock model not accessible (check model access in console)

### Issue: DynamoDB ProvisionedThroughputExceededException

**Solution**:
```hcl
# In terraform.tfvars
dynamodb_billing_mode = "PAY_PER_REQUEST"  # Should already be set
```

### Issue: Bedrock AccessDeniedException

**Check model access**:
```bash
aws bedrock get-foundation-model \
  --model-identifier meta.llama3-2-1b-instruct-v1:0 \
  --region us-east-1
```

**Fix**: Go to AWS Console → Bedrock → Model Access → Request access

### Issue: Secrets Manager permission denied

**Check IAM policy**:
```bash
terraform state show aws_iam_role_policy.lambda_secrets
```

Should include `secretsmanager:GetSecretValue` action.

## Success Criteria ✅

Before proceeding to frontend, verify:

- [x] Terraform apply completed without errors
- [x] API endpoint returns 200 status
- [x] Bot responds with conversational messages
- [x] Multi-turn conversation works (name → card → expiry → CVV)
- [x] Luhn validation catches invalid cards
- [x] DynamoDB stores sessions correctly
- [x] CloudWatch logs show no errors
- [x] Secrets Manager integration works
- [x] API handles 10+ concurrent requests
- [x] Estimated cost is <$0.05 for all tests

## Cleanup (Optional)

If you want to tear down and restart:

```bash
# Delete all resources
terraform destroy

# Type 'yes' to confirm

# Then redeploy
terraform apply
```

## Next Steps

Once all tests pass:

1. ✅ Backend is production-ready
2. 🚀 Move to frontend development
3. 📊 Add Streamlit UI or React app
4. 🔗 Connect frontend to `api_endpoint`
5. 🎨 Build user-friendly chat interface

---

**Testing Time**: ~30 minutes  
**Cost**: <$0.05 (mostly Bedrock tokens)  
**Resources Created**: 23 AWS resources

**Need help?** Check Lambda logs first, then review IAM policies.
