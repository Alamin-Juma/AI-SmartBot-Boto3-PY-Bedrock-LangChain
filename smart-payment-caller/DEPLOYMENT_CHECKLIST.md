# Deployment Checklist - Smart Payment Caller

## Pre-Deployment Checklist

### ☐ AWS Account Setup
- [ ] AWS CLI installed and configured
  ```bash
  aws --version  # Should show version 2.x
  aws sts get-caller-identity  # Verify credentials
  ```
- [ ] SAM CLI installed
  ```bash
  sam --version  # Should show version 1.x
  ```
- [ ] Python 3.11 installed locally
  ```bash
  python3 --version
  ```
- [ ] Git repository initialized (optional)
  ```bash
  git init
  git add .
  git commit -m "Initial commit: PCI-compliant IVR payment bot"
  ```

### ☐ Stripe Setup
- [ ] Stripe account created at https://stripe.com
- [ ] Test mode API key obtained
  - Go to: https://dashboard.stripe.com/test/apikeys
  - Copy "Secret key" (starts with `sk_test_`)
- [ ] API key stored in AWS SSM
  ```bash
  aws ssm put-parameter \
    --name "/payment-bot/stripe-secret" \
    --value "sk_test_YOUR_KEY_HERE" \
    --type SecureString \
    --region us-east-1
  ```
- [ ] Verify parameter stored
  ```bash
  aws ssm get-parameter \
    --name "/payment-bot/stripe-secret" \
    --with-decryption
  ```

### ☐ Amazon Bedrock Setup

**IMPORTANT**: For PCI Level 1 compliance, use Custom Inference Profile (not foundation model)

#### Option 1: Foundation Model (POC Only)
- [ ] Bedrock available in your region
  ```bash
  aws bedrock list-foundation-models --region us-east-1
  ```
- [ ] Mistral 7B Instruct access requested
  - Go to: https://console.aws.amazon.com/bedrock/
  - Enable "Mistral 7B Instruct"
  - ⚠️ **Note**: Not PCI Level 1 compliant (shared compute)

#### Option 2: Custom Inference Profile (Production - RECOMMENDED)
- [ ] Custom inference profile created
  ```bash
  aws bedrock create-inference-profile \
    --inference-profile-name "payment-bot-isolated" \
    --model-source '{"copyFrom":"us.mistral.mistral-7b-instruct-v0:2"}' \
    --inference-profile-config '{"modelCopyConfig":{"targetRegion":"us-west-2","copyType":"COPY_AND_ENCRYPT"}}'
  ```
- [ ] Profile ARN obtained
  ```bash
  PROFILE_ARN=$(aws bedrock get-inference-profile \
    --inference-profile-identifier payment-bot-isolated \
    --query 'inferenceProfileArn' --output text)
  echo "Custom Profile ARN: $PROFILE_ARN"
  ```
- [ ] ARN saved for deployment (use in sam deploy --guided)
- [ ] ✅ **PCI Level 1 Compliant** (isolated compute, QSA-approvable)

See [docs/CUSTOM_MODEL_SETUP.md](docs/CUSTOM_MODEL_SETUP.md) for detailed setup
  - Go to: https://console.aws.amazon.com/bedrock/
  - Click "Model access" → "Manage model access"
  - Enable "Mistral 7B Instruct"
- [ ] Wait 2-5 minutes for approval
- [ ] Verify access granted
  ```bash
  aws bedrock list-foundation-models \
    --by-provider mistral \
    --region us-east-1 \
    --query 'modelSummaries[?modelId==`mistral.mistral-7b-instruct-v0:2`]'
  ```

---

## Deployment Steps

### ☐ Step 1: Build Lambda Package
```bash
cd c:/dev/personal/AI-SmartBots-Boto3-Bedrock-LLMs/smart-payment-caller
sam build
```

**Expected output**:
```
Build Succeeded

Built Artifacts  : .aws-sam/build
Built Template   : .aws-sam/build/template.yaml
```

**Troubleshooting**:
- If build fails, ensure Python 3.11 is installed
- Check `src/requirements.txt` exists
- Verify `template.yaml` syntax

### ☐ Step 2: Test Locally (Optional)
```bash
sam local invoke PaymentBotFunction -e events/test-event.json
```

**Expected output**:
```json
{
  "statusCode": 200,
  "response": "Thank you! Your Visa card ending in 4242...",
  "stripeToken": "tok_xxxxxxxxxxxxx",
  "metadata": {
    "pci_compliant": true,
    "chd_masked": true
  }
}
```

**Troubleshooting**:
- If Stripe error: Verify SSM parameter
- If Bedrock error: Check model access
- If timeout: Increase timeout in `template.yaml`

### ☐ Step 3: Deploy to AWS
```bash
sam deploy --guided
```

**Answer prompts**:
- Stack name: `payment-bot-poc`
- AWS Region: `us-east-1`
- Parameter Environment: `dev`
- Parameter BedrockModelId: `mistral.mistral-7b-instruct-v0:2`
- Parameter StripeSecretParam: `/payment-bot/stripe-secret`
- Confirm changes: `Y`
- Allow SAM CLI IAM role creation: `Y`
- PaymentBotFunction may not have authorization defined: `Y`
- Save arguments to samconfig.toml: `Y`

**Expected output**:
```
CloudFormation stack changeset
-------------------------------------------------------------
Operation                  LogicalResourceId
-------------------------------------------------------------
+ Add                      PaymentBotFunction
+ Add                      AuditLogsBucket
+ Add                      AuditLogsKMSKey
...

Successfully created/updated stack - payment-bot-poc in us-east-1
```

**Troubleshooting**:
- If S3 bucket exists: Stack name conflict, choose different name
- If IAM permissions error: Ensure AWS credentials have admin access
- If KMS error: Check region supports KMS

### ☐ Step 4: Verify Deployment
```bash
# Get stack outputs
aws cloudformation describe-stacks \
  --stack-name payment-bot-poc \
  --query 'Stacks[0].Outputs'

# Test Lambda function
aws lambda invoke \
  --function-name payment-bot-handler-dev \
  --payload file://events/test-event.json \
  response.json

cat response.json | jq .
```

**Expected outputs**:
- Lambda ARN: `arn:aws:lambda:us-east-1:ACCOUNT:function:payment-bot-handler-dev`
- S3 Bucket: `payment-bot-audit-logs-dev-ACCOUNT`
- KMS Key: `arn:aws:kms:us-east-1:ACCOUNT:key/xxx`

---

## Post-Deployment Validation

### ☐ Security Validation

#### Test 1: CHD Masking
```bash
# Invoke Lambda with test card
aws lambda invoke \
  --function-name payment-bot-handler-dev \
  --payload file://events/test-event.json \
  response.json

# Check response contains masked card only
cat response.json | jq '.metadata.chd_masked'
# Expected: true
```

#### Test 2: No CHD in Logs
```bash
# Search CloudWatch logs for full card number
aws logs filter-log-events \
  --log-group-name /aws/lambda/payment-bot-handler-dev \
  --filter-pattern "4242424242424242" \
  --region us-east-1

# Expected: No events found (CHD is masked)
```

#### Test 3: Audit Logs Encrypted
```bash
# List audit logs
BUCKET=$(aws cloudformation describe-stacks \
  --stack-name payment-bot-poc \
  --query 'Stacks[0].Outputs[?OutputKey==`AuditLogsBucketName`].OutputValue' \
  --output text)

aws s3 ls s3://$BUCKET/audit/ --recursive

# Download and verify masking
aws s3 cp s3://$BUCKET/audit/$(date +%Y/%m/%d)/xxx.json - | jq .

# Expected: Card numbers shown as "************4242"
```

#### Test 4: Stripe Tokenization
```bash
# Check response includes Stripe token
cat response.json | jq '.stripeToken'
# Expected: "tok_xxxxxxxxxxxxx"
```

### ☐ Performance Validation

#### Test 1: Lambda Duration
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=payment-bot-handler-dev \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum \
  --region us-east-1

# Expected: Average < 5000ms, Maximum < 10000ms
```

#### Test 2: Bedrock Usage
```bash
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name Invocations \
  --dimensions Name=ModelId,Value=mistral.mistral-7b-instruct-v0:2 \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum \
  --region us-east-1
```

---

## Amazon Connect Integration (Optional)

### ☐ Step 1: Create Connect Instance
- [ ] Go to: https://console.aws.amazon.com/connect/
- [ ] Click "Add an instance"
- [ ] Choose "Store users within Amazon Connect"
- [ ] Instance alias: `payment-bot-poc`
- [ ] Create administrator account
- [ ] Default settings → Create instance

### ☐ Step 2: Claim Phone Number
- [ ] Open Connect instance
- [ ] Go to "Channels" → "Phone numbers"
- [ ] Click "Claim a number"
- [ ] Choose country (e.g., United States)
- [ ] Choose number type (DID or Toll-free)
- [ ] Click "Claim"

### ☐ Step 3: Add Lambda Function
- [ ] In Connect console → "Contact flows" → "AWS Lambda"
- [ ] Click "Add Lambda function"
- [ ] Select: `payment-bot-handler-dev`
- [ ] Click "Add Lambda function"

### ☐ Step 4: Import Contact Flow
- [ ] Go to "Contact flows" → "Create contact flow"
- [ ] Name: `Payment Bot Flow`
- [ ] Click "Save" → "Import flow (beta)"
- [ ] Upload: `connect-flows/payment-bot-flow.json`
- [ ] Edit "Invoke AWS Lambda function" block:
  - Replace `REPLACE_WITH_YOUR_LAMBDA_ARN` with actual ARN
- [ ] Edit "Transfer to queue" block:
  - Replace `REPLACE_WITH_YOUR_QUEUE_ARN` with actual queue ARN
- [ ] Click "Save" → "Publish"

### ☐ Step 5: Assign Flow to Number
- [ ] Go to "Channels" → "Phone numbers"
- [ ] Click your claimed number
- [ ] Under "Contact flow / IVR", select `Payment Bot Flow`
- [ ] Click "Save"

### ☐ Step 6: Test End-to-End
- [ ] Call your Connect phone number
- [ ] Follow voice prompts:
  - "Welcome to secure payment system..."
  - Press 1 to continue
  - Enter card: `4242424242424242#`
  - Enter expiry: `1225#`
  - Enter CVV: `123#`
  - Hear confirmation: "Your payment has been processed..."
- [ ] Verify transaction in audit logs

---

## Monitoring Setup

### ☐ CloudWatch Alarms
```bash
# Lambda error alarm (auto-created by SAM)
aws cloudwatch describe-alarms \
  --alarm-names payment-bot-lambda-errors-dev

# Lambda duration alarm (auto-created by SAM)
aws cloudwatch describe-alarms \
  --alarm-names payment-bot-lambda-duration-dev
```

### ☐ CloudWatch Dashboard (Optional)
```bash
# Create custom dashboard
aws cloudwatch put-dashboard \
  --dashboard-name payment-bot-poc \
  --dashboard-body file://cloudwatch-dashboard.json
```

### ☐ Log Insights Queries (Optional)
```bash
# Query for all payment transactions
aws logs start-query \
  --log-group-name /aws/lambda/payment-bot-handler-dev \
  --start-time $(date -u -d '1 day ago' +%s) \
  --end-time $(date -u +%s) \
  --query-string 'fields @timestamp, sessionId, intentType | filter intentType = "validate_payment"'
```

---

## Clean Up (If Needed)

### ☐ Delete Stack
```bash
# Delete CloudFormation stack
sam delete --stack-name payment-bot-poc --region us-east-1

# Verify deletion
aws cloudformation describe-stacks \
  --stack-name payment-bot-poc \
  --region us-east-1
# Expected: Stack not found
```

### ☐ Manual Cleanup
```bash
# Delete SSM parameter
aws ssm delete-parameter --name /payment-bot/stripe-secret

# Delete S3 bucket (if not auto-deleted)
BUCKET=$(aws cloudformation describe-stacks \
  --stack-name payment-bot-poc \
  --query 'Stacks[0].Outputs[?OutputKey==`AuditLogsBucketName`].OutputValue' \
  --output text)

aws s3 rm s3://$BUCKET --recursive
aws s3 rb s3://$BUCKET
```

---

## Troubleshooting Guide

### Issue: Bedrock Access Denied
**Symptom**: `AccessDeniedException: Could not access model`

**Solution**:
1. Go to: https://console.aws.amazon.com/bedrock/
2. Click "Model access" → "Manage model access"
3. Enable "Mistral 7B Instruct"
4. Wait 2-5 minutes
5. Retry deployment

### Issue: Stripe API Error
**Symptom**: `stripe.error.AuthenticationError`

**Solution**:
1. Verify SSM parameter:
   ```bash
   aws ssm get-parameter --name /payment-bot/stripe-secret --with-decryption
   ```
2. Check API key format: Should start with `sk_test_`
3. Verify key is valid in Stripe dashboard

### Issue: Lambda Timeout
**Symptom**: `Task timed out after 30.00 seconds`

**Solution**:
1. Edit `template.yaml` line 15:
   ```yaml
   Timeout: 60  # Increase to 60 seconds
   ```
2. Redeploy:
   ```bash
   sam build && sam deploy
   ```

### Issue: S3 Bucket Already Exists
**Symptom**: `BucketAlreadyExists`

**Solution**:
1. Change stack name:
   ```bash
   sam deploy --stack-name payment-bot-poc-v2
   ```
2. Or use unique bucket name in `template.yaml`

---

## Success Criteria

### ✅ POC Complete When:
- [x] Lambda function deployed successfully
- [x] Test invocation returns `statusCode: 200`
- [x] Stripe token created (`tok_xxxxx`)
- [x] CHD masked in all logs (`****4242`)
- [x] Audit logs stored in S3 (encrypted)
- [x] Bedrock responds with natural language
- [x] CloudWatch alarms created
- [x] No CHD found in CloudWatch logs

### ✅ Production Ready When:
- [ ] VPC with private subnets deployed
- [ ] AWS WAF configured
- [ ] GuardDuty enabled
- [ ] Penetration test completed
- [ ] Incident response plan documented
- [ ] Staff security training completed
- [ ] QSA pre-audit passed

---

## Next Steps After Successful Deployment

1. **Test with Real Calls** (if Connect configured)
   - Call your Connect number
   - Test all payment scenarios
   - Verify end-to-end flow

2. **Monitor Performance**
   - Review CloudWatch metrics
   - Check Lambda duration
   - Verify Bedrock token usage

3. **Review Audit Logs**
   - Download sample S3 audit logs
   - Verify masking is correct
   - Check encryption is enabled

4. **Plan Production Migration**
   - Review [docs/PCI_COMPLIANCE_CHECKLIST.md](docs/PCI_COMPLIANCE_CHECKLIST.md)
   - Address missing requirements
   - Schedule security assessments

5. **Document & Share**
   - Share Lambda ARN with team
   - Document Connect phone number
   - Update runbooks

---

## Support & Resources

- **Documentation**: [README.md](README.md)
- **Quick Start**: [QUICKSTART.md](QUICKSTART.md)
- **Architecture**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Compliance**: [docs/PCI_COMPLIANCE_CHECKLIST.md](docs/PCI_COMPLIANCE_CHECKLIST.md)
- **Diagrams**: [docs/DIAGRAMS.md](docs/DIAGRAMS.md)

**For issues**: Check CloudWatch Logs first, then S3 audit logs.

---

**Deployment Date**: _________________  
**Deployed By**: _________________  
**Environment**: POC / Dev / Staging / Production  
**Status**: ✅ Success / ⚠️ Issues / ❌ Failed
