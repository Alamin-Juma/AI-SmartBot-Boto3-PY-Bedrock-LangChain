# Terraform Deployment Guide

## Prerequisites

1. **Terraform**: Install version >= 1.5.0
   ```bash
   # Check version
   terraform version
   
   # Install (if needed)
   # Windows: choco install terraform
   # Mac: brew install terraform
   # Linux: Download from terraform.io
   ```

2. **AWS CLI**: Configured with credentials
   ```bash
   aws sts get-caller-identity
   ```

3. **Stripe Account**: Get test API key
   - Go to https://dashboard.stripe.com/test/apikeys
   - Copy "Secret key" (starts with `sk_test_`)

4. **AWS Bedrock Access**: Enable Llama 3.2 1B model
   ```bash
   # Check model access
   aws bedrock list-foundation-models --region us-east-1 \
     --query "modelSummaries[?contains(modelId,'llama3-2-1b')].modelId"
   
   # If empty, go to AWS Console → Bedrock → Model Access → Request Access
   ```

## Step-by-Step Deployment

### 1. Navigate to Terraform Directory
```bash
cd /c/dev/personal/AI-SmartBots-Boto3-Bedrock-LLMs/payment-smart-bot/terraform
```

### 2. Create terraform.tfvars
```bash
# Copy example file
cp terraform.tfvars.example terraform.tfvars

# Edit with your values (use your favorite editor)
nano terraform.tfvars
```

**Required changes in `terraform.tfvars`**:
```hcl
stripe_secret_key = "sk_test_YOUR_ACTUAL_STRIPE_KEY_HERE"
```

### 3. Initialize Terraform
```bash
terraform init
```

**Expected output**:
```
Initializing the backend...
Initializing provider plugins...
- Finding hashicorp/aws versions matching "~> 5.0"...
- Finding hashicorp/archive versions matching "~> 2.4"...
✓ Terraform has been successfully initialized!
```

### 4. Validate Configuration
```bash
terraform validate
```

Should output: `Success! The configuration is valid.`

### 5. Plan Deployment (Dry Run)
```bash
terraform plan
```

**Review the plan**:
- 20+ resources will be created
- Check estimated costs in output
- Verify resource names match your environment

### 6. Deploy Infrastructure
```bash
terraform apply
```

Type `yes` when prompted to confirm.

**Deployment time**: ~2-3 minutes

**Expected resources created**:
- ✅ Lambda Function
- ✅ API Gateway (REST API)
- ✅ DynamoDB Table
- ✅ Secrets Manager (Stripe key)
- ✅ KMS Key (encryption)
- ✅ IAM Roles & Policies
- ✅ CloudWatch Log Groups
- ✅ CloudWatch Alarms

### 7. Test the Deployment
```bash
# Get API endpoint from outputs
API_ENDPOINT=$(terraform output -raw api_endpoint)

# Test with curl
curl -X POST $API_ENDPOINT \
  -H "Content-Type: application/json" \
  -d '{"sessionId": "test-001", "message": "I want to make a payment"}'
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

## Terraform Outputs

After `terraform apply`, you'll see:

```
Outputs:

api_endpoint = "https://abc123.execute-api.us-east-1.amazonaws.com/dev/chat"
lambda_function_name = "payment-smart-bot-handler-dev"
dynamodb_table_name = "payment-smart-bot-sessions-dev"
cloudwatch_log_group_lambda = "/aws/lambda/payment-smart-bot-handler-dev"
curl_test_command = "curl -X POST https://..."
```

Save these for later use!

## Cost Estimate

Based on On-Demand pricing in `us-east-1`:

### Per 1,000 Customers:
- **Bedrock (Llama 3.2 1B)**: ~$0.50
- **Lambda**: ~$0.10 (5 invocations × 1s × 512MB)
- **DynamoDB**: ~$0.03 (5 read/write units per session)
- **API Gateway**: ~$0.04 (5 requests)
- **Secrets Manager**: $0.40/month (fixed)
- **KMS**: $1.00/month (fixed)
- **CloudWatch Logs**: ~$0.05

**Total**: ~$0.67 per 1,000 customers + ~$1.45/month fixed

### Free Tier (First 12 months):
- Lambda: 1M requests/month free
- DynamoDB: 25 GB storage + 200M requests/month
- API Gateway: 1M calls/month
- **Effective cost**: ~$0.50/1000 customers (Bedrock only)

## Infrastructure Management

### View Current State
```bash
# List all resources
terraform state list

# Show specific resource
terraform state show aws_lambda_function.payment_handler
```

### Update Infrastructure
```bash
# Modify terraform.tfvars or *.tf files
nano lambda.tf

# Preview changes
terraform plan

# Apply changes
terraform apply
```

### View Logs
```bash
# Lambda logs
aws logs tail /aws/lambda/payment-smart-bot-handler-dev --follow

# API Gateway logs
aws logs tail /aws/apigateway/payment-smart-bot-dev --follow
```

### Monitor Metrics
```bash
# Lambda invocations (last hour)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=payment-smart-bot-handler-dev \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

## Updating Lambda Code

### After changing Python code:
```bash
# Terraform automatically repackages and deploys
terraform apply

# Force update even if code hash unchanged
terraform taint aws_lambda_function.payment_handler
terraform apply
```

### Manual update (faster for testing):
```bash
cd /c/dev/personal/AI-SmartBots-Boto3-Bedrock-LLMs/payment-smart-bot

# Package code
cd lambda
zip -r ../terraform/lambda_function.zip . -x "__pycache__/*" "*.pyc"
cd ../terraform

# Update Lambda
aws lambda update-function-code \
  --function-name payment-smart-bot-handler-dev \
  --zip-file fileb://lambda_function.zip
```

## Secrets Management

### Rotate Stripe Key
```bash
# Update Secrets Manager
aws secretsmanager update-secret \
  --secret-id payment-smart-bot/stripe-key-dev \
  --secret-string '{"STRIPE_SECRET_KEY":"sk_test_NEW_KEY_HERE"}'

# Lambda picks up new secret automatically (no redeploy needed)
```

### View Secret (for debugging)
```bash
aws secretsmanager get-secret-value \
  --secret-id payment-smart-bot/stripe-key-dev \
  --query SecretString \
  --output text
```

## Troubleshooting

### Issue: "Error acquiring state lock"
```bash
# Someone else is running terraform or previous run crashed
# Solution: Force unlock (use ID from error message)
terraform force-unlock <LOCK_ID>
```

### Issue: Lambda timeout
```bash
# Increase timeout in terraform.tfvars
lambda_timeout = 60  # seconds

terraform apply
```

### Issue: Bedrock throttling
```bash
# Check throttle errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/payment-smart-bot-handler-dev \
  --filter-pattern "ThrottlingException"

# Solution: Request quota increase or switch to Provisioned Throughput
```

### Issue: DynamoDB write failures
```bash
# Check capacity metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/DynamoDB \
  --metric-name ThrottledRequests \
  --dimensions Name=TableName,Value=payment-smart-bot-sessions-dev \
  --statistics Sum \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300

# Solution: Keep PAY_PER_REQUEST or increase provisioned capacity
```

## Cleanup / Destroy

### Delete all resources:
```bash
terraform destroy
```

Type `yes` to confirm.

**Warning**: This will:
- Delete DynamoDB table (sessions lost)
- Delete Lambda function
- Delete API Gateway
- Delete Secrets Manager secret (7-day recovery window)
- Keep KMS key (10-day deletion window)

### Partial cleanup (keep data):
```bash
# Remove specific resource
terraform state rm aws_dynamodb_table.sessions

# Then destroy rest
terraform destroy
```

## Production Deployment

### Changes for production:

1. **Enable API Authentication**:
   ```hcl
   # In api_gateway.tf
   authorization = "AWS_IAM"  # or add API key
   ```

2. **Enable Bedrock Guardrails**:
   ```hcl
   # In terraform.tfvars
   enable_bedrock_guardrails = true
   ```

3. **Switch to Provisioned DynamoDB** (if high volume):
   ```hcl
   dynamodb_billing_mode = "PROVISIONED"
   ```

4. **Use S3 Backend** (team collaboration):
   ```hcl
   # In main.tf
   backend "s3" {
     bucket = "your-terraform-state-bucket"
     key    = "payment-smart-bot/prod.tfstate"
     region = "us-east-1"
     encrypt = true
   }
   ```

5. **Enable VPC** (extra security):
   - Uncomment VPC config in `lambda.tf`
   - Create VPC, subnets, security groups

6. **Add SNS Alerts**:
   - Create SNS topic for alarms
   - Subscribe email/Slack webhook

7. **Use Live Stripe Key**:
   ```bash
   stripe_secret_key = "sk_live_..."  # NOT sk_test_
   ```

## CI/CD Integration

### GitHub Actions Example:
```yaml
name: Deploy Terraform
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: hashicorp/setup-terraform@v2
      
      - name: Terraform Init
        run: terraform init
        working-directory: payment-smart-bot/terraform
      
      - name: Terraform Plan
        run: terraform plan
        working-directory: payment-smart-bot/terraform
        env:
          TF_VAR_stripe_secret_key: ${{ secrets.STRIPE_SECRET_KEY }}
      
      - name: Terraform Apply
        if: github.ref == 'refs/heads/main'
        run: terraform apply -auto-approve
        working-directory: payment-smart-bot/terraform
        env:
          TF_VAR_stripe_secret_key: ${{ secrets.STRIPE_SECRET_KEY }}
```

## Support

- **Terraform Docs**: https://registry.terraform.io/providers/hashicorp/aws/latest/docs
- **AWS Bedrock**: https://docs.aws.amazon.com/bedrock/
- **Stripe API**: https://stripe.com/docs/api

---

**Need Help?** Open an issue in the GitHub repo or check CloudWatch logs for errors.
