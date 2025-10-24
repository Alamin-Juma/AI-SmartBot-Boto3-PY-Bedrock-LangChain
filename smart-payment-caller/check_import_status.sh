#!/bin/bash
# Monitor Qwen Model Import Job
# Usage: ./check_import_status.sh

JOB_NAME="qwen-coder-7b-import-20251024-131653"

echo "🔍 Checking Bedrock Model Import Status"
echo "========================================"
echo ""

# Get current status
STATUS=$(aws bedrock get-model-import-job \
    --job-identifier "$JOB_NAME" \
    --query 'status' \
    --output text)

echo "Job Name: $JOB_NAME"
echo "Status: $STATUS"
echo ""

# Get detailed info
aws bedrock get-model-import-job \
    --job-identifier "$JOB_NAME" \
    --query '{
        Status: status,
        CreatedAt: createdAt,
        LastModified: lastModifiedTime,
        ModelName: importedModelName,
        Message: message
    }' \
    --output table

echo ""

if [ "$STATUS" = "Completed" ]; then
    echo "🎉 Import completed successfully!"
    echo ""
    echo "Getting model ARN..."
    MODEL_ARN=$(aws bedrock list-custom-models \
        --query "modelSummaries[?modelName=='qwen-coder-7b-payment-bot'].modelArn" \
        --output text)
    
    echo "Model ARN: $MODEL_ARN"
    echo "$MODEL_ARN" > qwen_model_arn.txt
    echo "✅ Saved to: qwen_model_arn.txt"
    echo ""
    echo "Next steps:"
    echo "  1. sam build"
    echo "  2. sam deploy --parameter-overrides BedrockModelId=\"$MODEL_ARN\""
    
elif [ "$STATUS" = "InProgress" ]; then
    echo "⏳ Import still in progress..."
    echo ""
    echo "Tip: Run this script again in a few minutes:"
    echo "  ./check_import_status.sh"
    echo ""
    echo "Or watch continuously (checks every 2 minutes):"
    echo "  watch -n 120 ./check_import_status.sh"
    
elif [ "$STATUS" = "Failed" ]; then
    echo "❌ Import failed!"
    echo ""
    echo "Checking failure details..."
    aws bedrock get-model-import-job \
        --job-identifier "$JOB_NAME" \
        --query '{Status:status,Message:message,FailureMessage:failureMessage}' \
        --output json
    
else
    echo "Status: $STATUS"
fi
