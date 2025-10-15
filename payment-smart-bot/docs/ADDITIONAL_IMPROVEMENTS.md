# Additional Terraform Improvements - Implementation Guide

## Overview

This document covers the **3 additional Terraform enhancements** that were added to make the payment bot more production-ready:

1. ✅ **Bedrock Token Usage Alarm** - Monitor and alert on API costs
2. ✅ **Guardrails IAM Policy** - Enable content filtering (optional)
3. ⚠️ **S3 Backend** - Recommended for production (commented out by default)

---

## 1. Bedrock Token Usage Alarm 📊

### What It Does
Monitors daily Bedrock API token consumption and alerts when threshold is exceeded.

### Why It Matters
- **Cost Control**: Prevents unexpected bills from runaway token usage
- **Anomaly Detection**: Alerts on unusual traffic spikes
- **Budget Management**: Track API costs in real-time

### Implementation

**File**: `main.tf` (lines 42-70)

```hcl
resource "aws_cloudwatch_metric_alarm" "bedrock_token_usage" {
  alarm_name          = "${var.project_name}-bedrock-token-usage-${var.environment}"
  alarm_description   = "Alert when Bedrock input token usage exceeds daily threshold"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "InputTokenCount"
  namespace           = "AWS/Bedrock"
  period              = "86400"  # Daily (24 hours)
  statistic           = "Sum"
  threshold           = var.bedrock_token_threshold
  treat_missing_data  = "notBreaching"
  
  dimensions = {
    ModelId = var.bedrock_model_id
  }
  
  alarm_actions = []  # Add SNS topic ARN here for notifications
}
```

### Configuration

**Variable**: `bedrock_token_threshold` (default: 100,000 tokens/day)

```hcl
# In terraform.tfvars
bedrock_token_threshold = 100000  # Alert at 100k tokens/day (~$1.50)
```

**Cost Calculation**:
- Llama 3.2 1B: $0.015 per 1k input tokens
- 100k tokens = $1.50/day
- For production, adjust based on expected traffic

### Setting Up Notifications

To receive email/SMS alerts when threshold is exceeded:

1. **Create SNS Topic**:
```bash
aws sns create-topic --name payment-bot-alerts
aws sns subscribe --topic-arn arn:aws:sns:us-east-1:ACCOUNT_ID:payment-bot-alerts \
  --protocol email --notification-endpoint your-email@example.com
```

2. **Update main.tf**:
```hcl
alarm_actions = [
  "arn:aws:sns:us-east-1:${data.aws_caller_identity.current.account_id}:payment-bot-alerts"
]
```

3. **Redeploy**:
```bash
terraform apply
```

### Monitoring the Alarm

**Check alarm state**:
```bash
aws cloudwatch describe-alarms \
  --alarm-names payment-smart-bot-bedrock-token-usage-dev
```

**View token metrics**:
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name InputTokenCount \
  --dimensions Name=ModelId,Value=meta.llama3-2-1b-instruct-v1:0 \
  --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 86400 \
  --statistics Sum
```

**Set custom threshold**:
```hcl
# In terraform.tfvars for high-volume production
bedrock_token_threshold = 1000000  # 1M tokens/day (~$15)
```

---

## 2. Bedrock Guardrails IAM Policy 🛡️

### What It Does
Grants Lambda permission to use Bedrock Guardrails for content filtering.

### Why It Matters
- **PII Protection**: Filters out credit card numbers, SSNs, etc. from logs
- **Content Moderation**: Blocks harmful/inappropriate content
- **Compliance**: Helps meet regulatory requirements (GDPR, CCPA, PCI-DSS)

### Implementation

**File**: `iam.tf` (lines 151-175)

```hcl
resource "aws_iam_role_policy" "lambda_guardrails" {
  count = var.enable_bedrock_guardrails ? 1 : 0
  
  name = "${var.project_name}-lambda-guardrails-${var.environment}"
  role = aws_iam_role.lambda_role.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:ApplyGuardrail",
          "bedrock:GetGuardrail",
          "bedrock:ListGuardrails"
        ]
        Resource = "*"
      }
    ]
  })
}
```

### Enabling Guardrails

**Step 1: Enable in terraform.tfvars**:
```hcl
enable_bedrock_guardrails = true
```

**Step 2: Create Guardrail in AWS Console**:
1. Go to: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/guardrails
2. Click "Create guardrail"
3. Configure filters:
   - **PII Filter**: Block credit cards, SSN, phone numbers
   - **Content Filter**: Block harmful content (hate speech, violence)
   - **Word Filter**: Block specific sensitive terms
   - **Topic Filter**: Restrict to payment-related topics only

**Step 3: Update Lambda handler** (payment_handler.py):
```python
# Add guardrailIdentifier and guardrailVersion to bedrock call
response = bedrock_runtime.converse(
    modelId=MODEL_ID,
    messages=messages,
    system=[{"text": SYSTEM_PROMPT}],
    guardrailConfig={
        "guardrailIdentifier": "your-guardrail-id",  # From console
        "guardrailVersion": "DRAFT"  # or specific version
    },
    inferenceConfig={
        "temperature": 0.5,
        "maxTokens": 512,
        "topP": 0.9
    }
)
```

**Step 4: Deploy**:
```bash
terraform apply
```

### Cost Impact

- **Guardrails**: $0.15 per 1,000 text units
- **1 text unit** = ~1,000 characters
- **Average message**: 200 chars = 0.2 units = $0.00003
- **1,000 messages**: $0.30 (plus base Bedrock costs)

**Enable if**:
- Production environment
- Handling sensitive data
- Compliance requirements
- Customer-facing bot

**Disable if**:
- Development/testing
- Cost-sensitive application
- Low-risk content

---

## 3. S3 Backend for Terraform State ☁️

### What It Does
Stores Terraform state file in S3 instead of locally.

### Why It Matters
- **Team Collaboration**: Multiple developers can share state
- **State Locking**: Prevents concurrent modifications (with DynamoDB)
- **Backup & Recovery**: State is versioned and backed up
- **Security**: State can be encrypted (contains secrets)

### Current Status
**Commented out by default** to simplify initial setup.

**File**: `main.tf` (lines 18-23)

```hcl
# Optional: Use S3 backend for state management
# backend "s3" {
#   bucket = "your-terraform-state-bucket"
#   key    = "payment-smart-bot/terraform.tfstate"
#   region = "us-east-1"
# }
```

### Enabling S3 Backend (Recommended for Production)

**Step 1: Create S3 bucket**:
```bash
# Replace with your bucket name
BUCKET_NAME="your-company-terraform-state"
REGION="us-east-1"

# Create bucket
aws s3 mb s3://${BUCKET_NAME} --region ${REGION}

# Enable versioning (critical for rollback)
aws s3api put-bucket-versioning \
  --bucket ${BUCKET_NAME} \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket ${BUCKET_NAME} \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# Block public access
aws s3api put-public-access-block \
  --bucket ${BUCKET_NAME} \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

**Step 2: Create DynamoDB table for locking**:
```bash
aws dynamodb create-table \
  --table-name terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region ${REGION}
```

**Step 3: Uncomment and configure backend in main.tf**:
```hcl
backend "s3" {
  bucket         = "your-company-terraform-state"
  key            = "payment-smart-bot/terraform.tfstate"
  region         = "us-east-1"
  encrypt        = true
  dynamodb_table = "terraform-state-lock"
}
```

**Step 4: Migrate existing state**:
```bash
cd payment-smart-bot/terraform

# Initialize new backend
terraform init -migrate-state

# Terraform will ask: "Do you want to migrate all workspaces to "s3"?"
# Type: yes
```

**Step 5: Verify**:
```bash
# State should now be in S3
aws s3 ls s3://your-company-terraform-state/payment-smart-bot/

# Output: terraform.tfstate
```

### Benefits

| Feature | Local State | S3 Backend |
|---------|------------|------------|
| Team collaboration | ❌ No | ✅ Yes |
| State locking | ❌ No | ✅ Yes (with DynamoDB) |
| Versioning | ❌ Manual | ✅ Automatic |
| Encryption | ❌ No | ✅ Yes |
| Backup | ❌ Manual | ✅ Automatic |
| Remote access | ❌ No | ✅ Yes |

### Best Practices

1. **Use one bucket per AWS account**:
   - Structure: `s3://COMPANY-terraform-state/PROJECT/ENV/terraform.tfstate`
   - Example: `s3://acme-terraform-state/payment-bot/dev/terraform.tfstate`

2. **Enable MFA delete** (production):
```bash
aws s3api put-bucket-versioning \
  --bucket ${BUCKET_NAME} \
  --versioning-configuration Status=Enabled,MFADelete=Enabled \
  --mfa "arn:aws:iam::ACCOUNT:mfa/root-account-mfa-device TOTP_CODE"
```

3. **Set lifecycle policy** (optional):
```bash
# Keep 90 days of old versions
aws s3api put-bucket-lifecycle-configuration \
  --bucket ${BUCKET_NAME} \
  --lifecycle-configuration file://lifecycle.json
```

lifecycle.json:
```json
{
  "Rules": [{
    "Id": "DeleteOldVersions",
    "Status": "Enabled",
    "NoncurrentVersionExpiration": {
      "NoncurrentDays": 90
    }
  }]
}
```

4. **IAM permissions**:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": [
        "arn:aws:s3:::BUCKET_NAME",
        "arn:aws:s3:::BUCKET_NAME/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:DeleteItem"
      ],
      "Resource": "arn:aws:dynamodb:*:*:table/terraform-state-lock"
    }
  ]
}
```

---

## Summary of All Improvements ✅

### Lambda Handler
- [x] Stripe payment tokenization
- [x] Improved expiry validation (last day of month)
- [x] Thread-safe secret caching
- [x] Enhanced Bedrock error handling
- [x] Expanded cancellation synonyms

### Terraform Infrastructure
- [x] Bedrock token usage CloudWatch alarm
- [x] Guardrails IAM policy (conditional)
- [x] Increased Lambda timeout (30s → 60s)
- [x] Configurable token threshold variable
- [x] S3 backend documented (commented out by default)

### Documentation
- [x] IMPROVEMENTS.md - Technical details
- [x] ADDITIONAL_IMPROVEMENTS.md - This file
- [x] test_backend.sh - Automated testing
- [x] README_IMPROVEMENTS.md - User guide

---

## Testing the New Features

### Test 1: Bedrock Token Alarm

```bash
# Trigger alarm by sending many requests
for i in {1..100}; do
  curl -X POST $API_ENDPOINT \
    -H "Content-Type: application/json" \
    -d "{\"sessionId\": \"test-$i\", \"message\": \"test\"}"
  sleep 1
done

# Check alarm state (should change to ALARM if threshold exceeded)
aws cloudwatch describe-alarms \
  --alarm-names payment-smart-bot-bedrock-token-usage-dev
```

### Test 2: Guardrails (if enabled)

```bash
# Send message with PII
curl -X POST $API_ENDPOINT \
  -H "Content-Type: application/json" \
  -d '{"sessionId": "test-pii", "message": "My SSN is 123-45-6789"}'

# Response should be filtered/rejected by Guardrail
```

### Test 3: S3 Backend

```bash
# After migrating to S3 backend
terraform plan

# Verify state in S3
aws s3 cp s3://your-bucket/payment-smart-bot/terraform.tfstate - | jq .version

# Test locking
terraform plan &  # Start in background
terraform plan    # Should fail with lock error
```

---

## Cost Summary

| Feature | Cost | Notes |
|---------|------|-------|
| **Bedrock Token Alarm** | $0 | CloudWatch alarms are free (first 10) |
| **Guardrails** | $0.15/1k units | ~$0.30 per 1k messages |
| **S3 Backend** | ~$0.023/month | $0.023/GB + requests ($0.0004/1k GET) |
| **DynamoDB Lock** | ~$0.25/month | Pay-per-request, minimal usage |

**Total additional cost**: ~$0.30/month (without Guardrails)

---

## Next Steps

1. **Deploy improvements**:
```bash
cd payment-smart-bot/terraform
terraform plan
terraform apply
```

2. **Verify new resources**:
```bash
# Check alarm exists
aws cloudwatch describe-alarms --alarm-name-prefix payment-smart-bot

# Check IAM policy (if Guardrails enabled)
aws iam get-role-policy \
  --role-name payment-smart-bot-lambda-role-dev \
  --policy-name payment-smart-bot-lambda-guardrails-dev
```

3. **Monitor token usage**:
```bash
# View metrics in CloudWatch console
# Or use CLI
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name InputTokenCount \
  --dimensions Name=ModelId,Value=meta.llama3-2-1b-instruct-v1:0 \
  --start-time $(date -u -d '1 day ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum
```

4. **Consider S3 backend** (for production):
   - Follow steps in section 3
   - Migrate state: `terraform init -migrate-state`

---

**All suggested improvements now implemented!** 🚀

You're ready to deploy and test the production-ready payment bot.
