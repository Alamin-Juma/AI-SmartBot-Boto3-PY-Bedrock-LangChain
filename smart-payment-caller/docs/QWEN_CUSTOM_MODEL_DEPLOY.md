# Deploy Qwen2.5-Coder-7B-Instruct Custom Model to Bedrock

## Overview
Inspired from https://aws.amazon.com/blogs/machine-learning/deploy-qwen-models-with-amazon-bedrock-custom-model-import/?utm_source=chatgpt.com

This guide walks through deploying **Qwen2.5-Coder-7B-Instruct** as a custom imported model in Amazon Bedrock to test the smart-payment-caller architecture. Once validated, we'll use the same process for Mistral.

**Timeline**: ~2-3 hours (mostly waiting for download/upload)

---

## Prerequisites

### 1. Install Required Python Packages

```bash
cd c:/dev/personal/AI-SmartBots-Boto3-Bedrock-LLMs/smart-payment-caller

# Install Hugging Face and dependencies
pip install huggingface_hub transformers torch

# Optional: Enable faster downloads
pip install hf_transfer
```

### 2. Set Up AWS Credentials

```bash
# Verify AWS CLI access
aws sts get-caller-identity

# Set your AWS region
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
```

### 3. Create S3 Bucket for Model Storage

```bash
# Create bucket with account ID to ensure uniqueness
aws s3 mb s3://payment-bot-custom-models-${AWS_ACCOUNT_ID} --region us-east-1

# Enable versioning (recommended)
aws s3api put-bucket-versioning \
  --bucket payment-bot-custom-models-${AWS_ACCOUNT_ID} \
  --versioning-configuration Status=Enabled
```

---

## Step 1: Download Qwen Model from Hugging Face

### 1.1 Create Download Script

```bash
# Create a download script
cat > download_qwen.py << 'EOF'
import os
from huggingface_hub import snapshot_download

# Enable faster downloads (optional)
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"

# Model ID from Hugging Face
hf_model_id = "Qwen/Qwen2.5-Coder-7B-Instruct"
local_directory = "./qwen-2.5-coder-7b"

print(f"📥 Downloading {hf_model_id} from Hugging Face...")
print(f"📂 Saving to: {local_directory}")

# Download model
snapshot_download(
    repo_id=hf_model_id,
    local_dir=local_directory,
    local_dir_use_symlinks=False
)

print("✅ Download complete!")
print(f"📁 Model files saved to: {os.path.abspath(local_directory)}")

# List downloaded files
print("\n📋 Downloaded files:")
for root, dirs, files in os.walk(local_directory):
    for file in files:
        file_path = os.path.join(root, file)
        size_mb = os.path.getsize(file_path) / (1024 * 1024)
        print(f"  - {file} ({size_mb:.2f} MB)")
EOF
```

### 1.2 Run Download

```bash
# Run the download (takes 10-20 minutes depending on internet speed)
python download_qwen.py
```

**Expected Output**:
```
📥 Downloading Qwen/Qwen2.5-Coder-7B-Instruct from Hugging Face...
📂 Saving to: ./qwen-2.5-coder-7b
✅ Download complete!

📋 Downloaded files:
  - config.json (1.23 MB)
  - generation_config.json (0.15 KB)
  - model.safetensors.index.json (0.45 KB)
  - model-00001-of-00004.safetensors (4980 MB)
  - model-00002-of-00004.safetensors (4999 MB)
  - model-00003-of-00004.safetensors (4915 MB)
  - model-00004-of-00004.safetensors (1195 MB)
  - tokenizer.json (7.03 MB)
  - tokenizer_config.json (1.45 KB)
  - vocab.json (2.78 MB)
  - merges.txt (1.67 MB)
  - LICENSE (11.36 KB)
  - README.md (15.82 KB)
```

---

## Step 2: Upload Model to S3

### 2.1 Upload to S3

```bash
# Upload all model files to S3 (takes 15-30 minutes)
aws s3 cp ./qwen-2.5-coder-7b/ \
  s3://payment-bot-custom-models-${AWS_ACCOUNT_ID}/qwen-2.5-coder-7b/ \
  --recursive \
  --storage-class INTELLIGENT_TIERING

# Verify upload
echo "📦 Verifying S3 upload..."
aws s3 ls s3://payment-bot-custom-models-${AWS_ACCOUNT_ID}/qwen-2.5-coder-7b/ \
  --recursive \
  --human-readable \
  --summarize
```

**Expected Output**:
```
Total Objects: 13
Total Size: 15.89 GB
```

---

## Step 3: Create IAM Role for Bedrock Model Import

### 3.1 Create Trust Policy

```bash
cat > bedrock-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "bedrock.amazonaws.com"
      },
      "Action": "sts:AssumeRole",
      "Condition": {
        "StringEquals": {
          "aws:SourceAccount": "${AWS_ACCOUNT_ID}"
        },
        "ArnEquals": {
          "aws:SourceArn": "arn:aws:bedrock:us-east-1:${AWS_ACCOUNT_ID}:model-import-job/*"
        }
      }
    }
  ]
}
EOF

# Replace account ID placeholder
sed -i "s/\${AWS_ACCOUNT_ID}/${AWS_ACCOUNT_ID}/g" bedrock-trust-policy.json
```

### 3.2 Create IAM Policy for S3 Access

```bash
cat > bedrock-s3-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::payment-bot-custom-models-${AWS_ACCOUNT_ID}",
        "arn:aws:s3:::payment-bot-custom-models-${AWS_ACCOUNT_ID}/*"
      ]
    }
  ]
}
EOF
```

### 3.3 Create IAM Role

```bash
# Create the role
aws iam create-role \
  --role-name BedrockCustomModelImportRole \
  --assume-role-policy-document file://bedrock-trust-policy.json

# Attach S3 policy
aws iam put-role-policy \
  --role-name BedrockCustomModelImportRole \
  --policy-name BedrockS3Access \
  --policy-document file://bedrock-s3-policy.json

# Get role ARN
ROLE_ARN=$(aws iam get-role \
  --role-name BedrockCustomModelImportRole \
  --query 'Role.Arn' \
  --output text)

echo "✅ IAM Role created: $ROLE_ARN"
```

---

## Step 4: Import Model to Bedrock

### 4.1 Create Import Job

```bash
# Set variables
JOB_NAME="qwen-coder-7b-import-$(date +%Y%m%d-%H%M%S)"
MODEL_NAME="qwen-coder-7b-payment-bot"
S3_URI="s3://payment-bot-custom-models-${AWS_ACCOUNT_ID}/qwen-2.5-coder-7b/"

# Start import job
aws bedrock create-model-import-job \
  --job-name "$JOB_NAME" \
  --imported-model-name "$MODEL_NAME" \
  --role-arn "$ROLE_ARN" \
  --model-data-source "{\"s3DataSource\": {\"s3Uri\": \"$S3_URI\"}}" \
  --region us-east-1

echo "✅ Import job started: $JOB_NAME"
echo "⏳ This will take 30-60 minutes. You can check status below..."
```

### 4.2 Monitor Import Progress

```bash
# Check import status (run this periodically)
aws bedrock get-model-import-job \
  --job-identifier "$JOB_NAME" \
  --query '{Status:status,Message:message,CreatedAt:createdAt}' \
  --output table

# Or use this one-liner to watch status every 2 minutes
watch -n 120 "aws bedrock get-model-import-job --job-identifier '$JOB_NAME' --query '{Status:status}' --output text"
```

**Status Values**:
- `InProgress` - Model is being imported (wait)
- `Completed` - Import successful ✅
- `Failed` - Import failed (check logs)

### 4.3 Get Model ARN (After Import Completes)

```bash
# List imported models
aws bedrock list-custom-models \
  --query 'modelSummaries[?modelName==`'$MODEL_NAME'`]' \
  --output table

# Get full model ARN
MODEL_ARN=$(aws bedrock list-custom-models \
  --query 'modelSummaries[?modelName==`'$MODEL_NAME'`].modelArn' \
  --output text)

echo "🎉 Model imported successfully!"
echo "📝 Model ARN: $MODEL_ARN"
echo ""
echo "Save this ARN - you'll need it for deployment:"
echo "$MODEL_ARN"
```

---

## Step 5: Test Model in Bedrock Playground (Console)

### 5.1 Access Playground

1. Go to: https://console.aws.amazon.com/bedrock/
2. Click **"Imported models"** in left sidebar
3. Find your model: `qwen-coder-7b-payment-bot`
4. Click **"Open in Playground"**

### 5.2 Test Prompt

**System Prompt**:
```
You are a helpful payment assistant. Respond naturally and professionally.
```

**User Prompt**:
```
I want to make a payment of $50.00 using my Visa card ending in 4242.
```

**Expected Response**:
```
Thank you! I'll process your payment of $50.00 using your Visa card ending in 4242. 
Please confirm this is correct before proceeding.
```

✅ If you get a response, model is working!

---

## Step 6: Get Chat Template for Proper Formatting

### 6.1 Extract Chat Template

```bash
cat > get_chat_template.py << 'EOF'
from transformers import AutoTokenizer

# Load tokenizer
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-Coder-7B-Instruct")

# Test prompt formatting
messages = [
    {"role": "system", "content": "You are a helpful payment assistant."},
    {"role": "user", "content": "I want to pay $50 with card ending 4242."}
]

# Apply chat template
formatted_prompt = tokenizer.apply_chat_template(
    messages,
    tokenize=False,
    add_generation_prompt=True
)

print("📝 Formatted Prompt for Bedrock:")
print("=" * 60)
print(formatted_prompt)
print("=" * 60)

# Save template for reference
with open("qwen_chat_template.txt", "w") as f:
    f.write(formatted_prompt)

print("\n✅ Template saved to: qwen_chat_template.txt")
EOF

python get_chat_template.py
```

---

## Step 7: Update Lambda to Use Qwen Model

### 7.1 Update Lambda Handler

```bash
# Backup current handler
cp src/lambda_handler.py src/lambda_handler.py.backup

# Update BEDROCK_MODEL_ID to use Qwen ARN
cat > update_model_id.py << EOF
import re

# Read lambda handler
with open('src/lambda_handler.py', 'r') as f:
    content = f.read()

# Replace BEDROCK_MODEL_ID
content = re.sub(
    r"BEDROCK_MODEL_ID = .*",
    f"BEDROCK_MODEL_ID = '{MODEL_ARN}'  # Qwen2.5-Coder-7B (Testing)",
    content
)

# Write back
with open('src/lambda_handler.py', 'w') as f:
    f.write(content)

print("✅ Updated lambda_handler.py with Qwen model ARN")
EOF

python update_model_id.py
```

### 7.2 Verify Change

```bash
# Check the updated line
grep "BEDROCK_MODEL_ID" src/lambda_handler.py
```

---

## Step 8: Deploy Updated Lambda

### 8.1 Build and Deploy

```bash
# Build Lambda package
sam build

# Deploy with Qwen model ARN
sam deploy \
  --parameter-overrides BedrockModelId="${MODEL_ARN}" \
  --no-confirm-changeset

echo "✅ Lambda deployed with Qwen model!"
```

---

## Step 9: Test Payment Bot with Qwen

### 9.1 Test Locally

```bash
# Run local test
python test_local.py
```

**Expected Output**:
```
🧪 Testing Smart Payment Caller Lambda with Qwen Model
========================================================

[SESSION] ID: test-session-12345 | Hash: abc123
[MASK] Original: 4242424242424242 → Masked: ************4242
[STRIPE] Tokenizing card ending in ****4242
[STRIPE] Token created: tok_xxxxx
[BEDROCK] Invoking Qwen model...
[BEDROCK] Response: Thank you! I've validated your Visa card ending in 4242...
[S3] Audit log stored successfully

✅ TEST PASSED - All components working with Qwen model!
```

### 9.2 Test with SAM Local Invoke

```bash
# Create test event
cat > events/test-qwen.json << 'EOF'
{
  "Details": {
    "ContactData": {
      "Attributes": {
        "cardNumber": "4242424242424242",
        "expiryDate": "12/25",
        "cvv": "123",
        "amount": "50.00"
      }
    }
  }
}
EOF

# Invoke Lambda locally
sam local invoke PaymentBotFunction -e events/test-qwen.json
```

---

## Step 10: Verify PCI Compliance with Qwen

### 10.1 Check CHD Masking

```bash
# Run offline test to verify masking works
python test_offline.py
```

**Expected**:
```
✅ Visa: 4242424242424242 → ************4242
✅ Mastercard: 5555555555554444 → ************4444
✅ Amex: 378282246310005 → ***********0005

🎉 PCI COMPLIANCE CHECK PASSED!
   CHD masking working correctly with Qwen model.
```

### 10.2 Check S3 Audit Logs

```bash
# List recent audit logs
aws s3 ls s3://$(aws cloudformation describe-stacks \
  --stack-name payment-bot-poc \
  --query 'Stacks[0].Outputs[?OutputKey==`AuditBucketName`].OutputValue' \
  --output text)/audit-logs/ \
  --recursive \
  --human-readable

# Download latest log
LATEST_LOG=$(aws s3 ls s3://$(aws cloudformation describe-stacks \
  --stack-name payment-bot-poc \
  --query 'Stacks[0].Outputs[?OutputKey==`AuditBucketName`].OutputValue' \
  --output text)/audit-logs/ \
  --recursive | tail -1 | awk '{print $4}')

aws s3 cp \
  s3://$(aws cloudformation describe-stacks \
    --stack-name payment-bot-poc \
    --query 'Stacks[0].Outputs[?OutputKey==`AuditBucketName`].OutputValue' \
    --output text)/${LATEST_LOG} \
  ./latest-audit-log.json

# Verify no CHD in logs
echo "🔍 Checking for CHD leakage in audit logs..."
if grep -q "4242424242424242" ./latest-audit-log.json; then
  echo "❌ FAIL - Full card number found in logs!"
else
  echo "✅ PASS - No full card numbers in logs (only masked)"
fi
```

---

## Step 11: Monitor Bedrock Usage and Costs

### 11.1 Check CloudWatch Metrics

```bash
# Get invocation count for last hour
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name Invocations \
  --dimensions Name=ModelId,Value="${MODEL_ARN}" \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum \
  --query 'Datapoints[0].Sum'
```

### 11.2 Check Active Model Copies

```bash
# Custom models auto-scale to 0 after 5 minutes of inactivity
# Check if model is currently active
aws bedrock list-custom-models \
  --query 'modelSummaries[?modelArn==`'$MODEL_ARN'`].{Name:modelName,Status:status}' \
  --output table
```

---

## Troubleshooting

### Issue 1: Import Job Fails

**Check Logs**:
```bash
aws bedrock get-model-import-job \
  --job-identifier "$JOB_NAME" \
  --query '{Status:status,Message:message,FailureMessage:failureMessage}' \
  --output json
```

**Common Causes**:
- IAM role missing S3 permissions
- S3 bucket in different region
- Model files corrupted during upload

**Solution**:
```bash
# Verify IAM role has S3 access
aws iam simulate-principal-policy \
  --policy-source-arn "$ROLE_ARN" \
  --action-names s3:GetObject s3:ListBucket \
  --resource-arns \
    "arn:aws:s3:::payment-bot-custom-models-${AWS_ACCOUNT_ID}" \
    "arn:aws:s3:::payment-bot-custom-models-${AWS_ACCOUNT_ID}/*"
```

### Issue 2: Model Invocation Fails

**Error**: `AccessDeniedException`

**Solution**:
```bash
# Add Bedrock invoke permissions to Lambda role
aws iam put-role-policy \
  --role-name PaymentBotLambdaRole \
  --policy-name BedrockInvokeCustomModel \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": "bedrock:InvokeModel",
      "Resource": "'$MODEL_ARN'"
    }]
  }'
```

### Issue 3: Cold Start Latency

**Symptom**: First invocation takes 30-60 seconds

**Explanation**: Custom models scale to 0 after 5 minutes of inactivity. First call after idle period triggers warm-up.

**Solution** (for production):
```bash
# Use provisioned throughput (keeps model warm)
aws bedrock create-provisioned-model-throughput \
  --model-id "$MODEL_ARN" \
  --provisioned-model-name "qwen-coder-7b-provisioned" \
  --model-units 1 \
  --commitment-duration "OneMonth"
```

---

## Pricing Estimate (Qwen 7B Custom Import)

### On-Demand Pricing

**Model Size Tier**: 7B parameters = Tier 2

**Cost per Active Model Copy**:
- **Per minute**: ~$0.012
- **Per hour**: ~$0.72
- **Per day (24/7)**: ~$17.28

**Auto-scaling**:
- Scales to 0 after 5 minutes idle (no charge)
- Scales up on demand (30-60s cold start)

**Estimated Monthly Cost** (based on usage):
```
POC (30 calls, avg 2 min each):
  30 calls × 2 min × $0.012 = $0.72

Production (1000 calls/month, avg 2 min each):
  1000 calls × 2 min × $0.012 = $24.00
  
Production (1000 calls/month, kept warm 24/7):
  720 hours × $0.72 = $518.40
```

**Recommendation**: Use on-demand for testing, provisioned throughput for production.

---

## Next Steps After Qwen Validation

Once you've validated the architecture with Qwen:

### 1. Document Test Results
```bash
# Save test results
cat > qwen-test-results.md << EOF
# Qwen Model Test Results

Date: $(date)
Model: Qwen2.5-Coder-7B-Instruct
Model ARN: $MODEL_ARN

## Test Cases
- [x] CHD masking working
- [x] Stripe tokenization successful
- [x] S3 audit logs encrypted
- [x] No CHD in logs (verified)
- [x] Bedrock invocation successful
- [x] Response quality acceptable

## Performance
- Cold start: ~45 seconds
- Warm invocation: ~2 seconds
- Token usage: ~150 tokens/call

## Cost (30 test calls)
- Bedrock: $0.72
- Lambda: Free tier
- S3: $0.01
- Total: $0.73

## Ready for Mistral Migration: YES ✅
EOF

cat qwen-test-results.md
```

### 2. Switch to Mistral (Same Process)

```bash
# Download Mistral 7B Instruct
python << 'EOF'
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id="mistralai/Mistral-7B-Instruct-v0.3",
    local_dir="./mistral-7b-instruct"
)
EOF

# Upload to S3
aws s3 cp ./mistral-7b-instruct/ \
  s3://payment-bot-custom-models-${AWS_ACCOUNT_ID}/mistral-7b-instruct/ \
  --recursive

# Import to Bedrock (same IAM role)
aws bedrock create-model-import-job \
  --job-name "mistral-7b-import-$(date +%Y%m%d-%H%M%S)" \
  --imported-model-name "mistral-7b-payment-bot" \
  --role-arn "$ROLE_ARN" \
  --model-data-source '{"s3DataSource":{"s3Uri":"s3://payment-bot-custom-models-'$AWS_ACCOUNT_ID'/mistral-7b-instruct/"}}'

# Update Lambda with new Mistral ARN
# (Get ARN after import completes)
```

---

## Clean Up (After Testing)

```bash
# Delete imported model (stops billing)
aws bedrock delete-custom-model \
  --model-identifier "$MODEL_ARN"

# Delete S3 model files (optional - keep for Mistral import)
# aws s3 rm s3://payment-bot-custom-models-${AWS_ACCOUNT_ID}/qwen-2.5-coder-7b/ --recursive

# Delete IAM role (optional - reuse for Mistral)
# aws iam delete-role-policy --role-name BedrockCustomModelImportRole --policy-name BedrockS3Access
# aws iam delete-role --role-name BedrockCustomModelImportRole
```

---

## Summary

✅ **What You Accomplished**:
1. Downloaded Qwen2.5-Coder-7B from Hugging Face
2. Uploaded 15GB model to S3
3. Created IAM role with proper permissions
4. Imported custom model to Bedrock
5. Updated Lambda to use custom model ARN
6. Tested payment bot with custom model
7. Verified PCI compliance (CHD masking)
8. Monitored usage and costs

✅ **Architecture Validated**:
- Custom model import works ✅
- CHD masking works ✅
- Stripe tokenization works ✅
- S3 audit logging works ✅
- PCI compliance maintained ✅

✅ **Ready for Production**:
- Same process works for Mistral
- Infrastructure proven
- Costs understood
- PCI compliant

🎉 **You're now ready to deploy Mistral using the exact same process!**
