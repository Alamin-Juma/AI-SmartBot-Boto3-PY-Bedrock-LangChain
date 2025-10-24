#!/bin/bash
# Quick Deploy Script: Qwen2.5-Coder-7B to Bedrock Custom Import
# Usage: ./deploy_qwen_custom.sh

set -e  # Exit on error

echo "🚀 Qwen2.5-Coder-7B Custom Model Deployment"
echo "==========================================="
echo ""

# Get AWS account info
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export AWS_REGION=${AWS_REGION:-us-east-1}

echo "📋 Configuration:"
echo "   AWS Account: $AWS_ACCOUNT_ID"
echo "   AWS Region: $AWS_REGION"
echo ""

# Step 1: Create S3 bucket
echo "📦 Step 1/7: Creating S3 bucket..."
BUCKET_NAME="payment-bot-custom-models-${AWS_ACCOUNT_ID}"
if aws s3 ls "s3://${BUCKET_NAME}" 2>&1 | grep -q 'NoSuchBucket'; then
    aws s3 mb "s3://${BUCKET_NAME}" --region "$AWS_REGION"
    echo "   ✅ Created bucket: ${BUCKET_NAME}"
else
    echo "   ✅ Bucket already exists: ${BUCKET_NAME}"
fi

# Step 2: Download model
echo ""
echo "📥 Step 2/7: Downloading Qwen model from Hugging Face..."
echo "   ⏳ This will take 10-20 minutes (15GB download)..."
cat > download_qwen.py << 'EOF'
import os
from huggingface_hub import snapshot_download

os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
hf_model_id = "Qwen/Qwen2.5-Coder-7B-Instruct"
local_directory = "./qwen-2.5-coder-7b"

print(f"Downloading {hf_model_id}...")
snapshot_download(
    repo_id=hf_model_id,
    local_dir=local_directory,
    local_dir_use_symlinks=False
)
print("Download complete!")
EOF

if [ -d "./qwen-2.5-coder-7b" ]; then
    echo "   ⚠️  Model already downloaded, skipping..."
else
    python download_qwen.py
    echo "   ✅ Model downloaded to ./qwen-2.5-coder-7b"
fi

# Step 3: Upload to S3
echo ""
echo "☁️  Step 3/7: Uploading model to S3..."
echo "   ⏳ This will take 15-30 minutes (15GB upload)..."
aws s3 sync ./qwen-2.5-coder-7b/ \
    "s3://${BUCKET_NAME}/qwen-2.5-coder-7b/" \
    --storage-class INTELLIGENT_TIERING \
    --only-show-errors
echo "   ✅ Model uploaded to S3"

# Step 4: Create IAM role
echo ""
echo "🔐 Step 4/7: Creating IAM role for Bedrock..."

# Create trust policy (use current directory instead of /tmp for Windows compatibility)
cat > bedrock-trust-policy.json << EOF
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
          "aws:SourceArn": "arn:aws:bedrock:${AWS_REGION}:${AWS_ACCOUNT_ID}:model-import-job/*"
        }
      }
    }
  ]
}
EOF

# Create S3 policy
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
        "arn:aws:s3:::${BUCKET_NAME}",
        "arn:aws:s3:::${BUCKET_NAME}/*"
      ]
    }
  ]
}
EOF

# Create role if it doesn't exist
if aws iam get-role --role-name BedrockCustomModelImportRole 2>&1 | grep -q 'NoSuchEntity'; then
    aws iam create-role \
        --role-name BedrockCustomModelImportRole \
        --assume-role-policy-document file://bedrock-trust-policy.json \
        --output text
    echo "   ✅ Created IAM role"
else
    echo "   ✅ IAM role already exists"
fi

# Attach policy
aws iam put-role-policy \
    --role-name BedrockCustomModelImportRole \
    --policy-name BedrockS3Access \
    --policy-document file://bedrock-s3-policy.json

ROLE_ARN="arn:aws:iam::${AWS_ACCOUNT_ID}:role/BedrockCustomModelImportRole"
echo "   ✅ Role ARN: $ROLE_ARN"

# Wait for role to propagate
echo "   ⏳ Waiting 10 seconds for IAM role propagation..."
sleep 10

# Step 5: Import model to Bedrock
echo ""
echo "🤖 Step 5/7: Importing model to Bedrock..."
echo "   ⏳ This will take 30-60 minutes..."

JOB_NAME="qwen-coder-7b-import-$(date +%Y%m%d-%H%M%S)"
MODEL_NAME="qwen-coder-7b-payment-bot"
S3_URI="s3://${BUCKET_NAME}/qwen-2.5-coder-7b/"

aws bedrock create-model-import-job \
    --job-name "$JOB_NAME" \
    --imported-model-name "$MODEL_NAME" \
    --role-arn "$ROLE_ARN" \
    --model-data-source "{\"s3DataSource\": {\"s3Uri\": \"$S3_URI\"}}" \
    --region "$AWS_REGION" \
    --output text

echo "   ✅ Import job started: $JOB_NAME"
echo ""
echo "   ⏳ Waiting for import to complete..."
echo "      (This takes 30-60 minutes - status updates every 2 min)"
echo ""

# Wait for import to complete
while true; do
    STATUS=$(aws bedrock get-model-import-job \
        --job-identifier "$JOB_NAME" \
        --query 'status' \
        --output text)
    
    echo "      [$(date +%H:%M:%S)] Status: $STATUS"
    
    if [ "$STATUS" = "Completed" ]; then
        echo "   ✅ Model import completed!"
        break
    elif [ "$STATUS" = "Failed" ]; then
        echo "   ❌ Model import failed!"
        aws bedrock get-model-import-job \
            --job-identifier "$JOB_NAME" \
            --query '{Status:status,Message:message,FailureMessage:failureMessage}' \
            --output json
        exit 1
    fi
    
    sleep 120  # Check every 2 minutes
done

# Step 6: Get model ARN
echo ""
echo "📝 Step 6/7: Getting model ARN..."
MODEL_ARN=$(aws bedrock list-custom-models \
    --query "modelSummaries[?modelName=='$MODEL_NAME'].modelArn" \
    --output text)

if [ -z "$MODEL_ARN" ]; then
    echo "   ❌ Failed to get model ARN"
    exit 1
fi

echo "   ✅ Model ARN: $MODEL_ARN"
echo ""

# Save ARN to file
echo "$MODEL_ARN" > qwen_model_arn.txt
echo "   💾 Saved to: qwen_model_arn.txt"

# Step 7: Update Lambda configuration
echo ""
echo "🔧 Step 7/7: Updating Lambda configuration..."

# Update environment variable in SAM template
if grep -q "BEDROCK_MODEL_ID" template.yaml; then
    echo "   📝 Add this to your sam deploy command:"
    echo ""
    echo "      sam deploy --parameter-overrides BedrockModelId=\"$MODEL_ARN\""
    echo ""
fi

# Create summary
cat > qwen_deployment_summary.txt << EOF
🎉 Qwen2.5-Coder-7B Deployment Complete!

Deployment Details:
===================
Date:           $(date)
AWS Account:    $AWS_ACCOUNT_ID
AWS Region:     $AWS_REGION
S3 Bucket:      s3://${BUCKET_NAME}/qwen-2.5-coder-7b/
IAM Role:       $ROLE_ARN
Model Name:     $MODEL_NAME
Model ARN:      $MODEL_ARN

Next Steps:
===========
1. Update Lambda with new model ARN:
   sam build
   sam deploy --parameter-overrides BedrockModelId="$MODEL_ARN"

2. Test the model:
   python test_local.py

3. Test in Bedrock Console:
   https://console.aws.amazon.com/bedrock/home?region=${AWS_REGION}#/imported-models

4. Monitor usage:
   aws cloudwatch get-metric-statistics \\
     --namespace AWS/Bedrock \\
     --metric-name Invocations \\
     --dimensions Name=ModelId,Value="$MODEL_ARN" \\
     --start-time \$(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \\
     --end-time \$(date -u +%Y-%m-%dT%H:%M:%S) \\
     --period 3600 \\
     --statistics Sum

Cost Estimate (On-Demand):
===========================
- Per active minute: ~\$0.012
- 30 test calls (2 min each): ~\$0.72
- 1000 calls/month (2 min each): ~\$24.00
- Auto-scales to \$0 after 5 min idle

Notes:
======
- First invocation after idle: 30-60s (cold start)
- Subsequent invocations: ~2s
- Model auto-scales to 0 after 5 minutes of inactivity
- Use provisioned throughput for production (keeps warm 24/7)

For production Mistral deployment:
===================================
Use the same process with:
  - Model: mistralai/Mistral-7B-Instruct-v0.3
  - Same S3 bucket
  - Same IAM role
  - Import time: ~30-60 minutes

Documentation:
==============
Full guide: docs/QWEN_CUSTOM_MODEL_DEPLOY.md
EOF

cat qwen_deployment_summary.txt

echo ""
echo "💾 Summary saved to: qwen_deployment_summary.txt"
echo ""
echo "🎉 DEPLOYMENT COMPLETE!"
echo ""
echo "Next: Run 'sam build && sam deploy --parameter-overrides BedrockModelId=\"$MODEL_ARN\"'"
echo ""
