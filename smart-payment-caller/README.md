# PCI-Compliant IVR Payment Bot - Setup Guide

## 🎯 Project Overview

This is a **PCI DSS SAQ A-EP compliant** IVR payment system using:
- **Amazon Connect** (voice gateway with DTMF capture)
- **AWS Lambda** (masks CHD before AI processing)
- **Amazon Bedrock** (Mistral 7B for conversational AI)
- **Stripe** (tokenization to remove CHD from scope)
- **S3 + KMS** (encrypted audit trail)

### Key Compliance Feature
**Cardholder Data (CHD) NEVER reaches the AI model.**  
All card numbers are masked/tokenized BEFORE being sent to Bedrock.

---

## 📋 Prerequisites

1. **AWS Account** with Bedrock access enabled
2. **Stripe Test Account** (get API key from [dashboard.stripe.com](https://dashboard.stripe.com))
3. **AWS CLI** configured with credentials
4. **SAM CLI** installed: `pip install aws-sam-cli`
5. **Python 3.11** installed locally
6. **Amazon Connect instance** (optional for full testing)

---

## 🚀 Quick Start (15 minutes)

### Step 1: Set Up Bedrock Model (Two Options)

#### **Option A: Foundation Model (POC Only - Quick Setup)**

⚠️ **Note**: Foundation models are suitable for POC but may not meet PCI Level 1 requirements.

```bash
# Enable Mistral 7B foundation model
# Go to: https://console.aws.amazon.com/bedrock/
# Enable "Mistral 7B Instruct" (takes 2-5 minutes)

# Verify access
aws bedrock list-foundation-models \
  --by-provider mistral \
  --region us-east-1 \
  --query 'modelSummaries[?modelId==`mistral.mistral-7b-instruct-v0:2`]'
```

#### **Option B: Custom Inference Profile (Production - PCI Level 1)**

✅ **Recommended for production**: Complete data isolation, QSA-approvable.

```bash
# Create custom inference profile with dedicated compute
aws bedrock create-inference-profile \
  --inference-profile-name "payment-bot-isolated" \
  --model-source '{"copyFrom":"us.mistral.mistral-7b-instruct-v0:2"}' \
  --inference-profile-config '{"modelCopyConfig":{"targetRegion":"us-west-2","copyType":"COPY_AND_ENCRYPT"}}'

# Get the profile ARN (use this instead of foundation model ID)
PROFILE_ARN=$(aws bedrock get-inference-profile \
  --inference-profile-identifier payment-bot-isolated \
  --query 'inferenceProfileArn' --output text)

echo "Use this ARN: $PROFILE_ARN"
```

**See [docs/CUSTOM_MODEL_SETUP.md](docs/CUSTOM_MODEL_SETUP.md) for detailed setup options.**

### Step 2: Store Stripe Secret Key

```bash
# Get your Stripe test key from: https://dashboard.stripe.com/test/apikeys
# Store it securely in AWS Systems Manager Parameter Store

aws ssm put-parameter \
  --name "/payment-bot/stripe-secret" \
  --value "sk_test_YOUR_STRIPE_TEST_KEY_HERE" \
  --type SecureString \
  --region us-east-1 \
  --description "Stripe test API key for payment bot"

# Verify it's stored
aws ssm get-parameter \
  --name "/payment-bot/stripe-secret" \
  --with-decryption \
  --region us-east-1
```

### Step 3: Deploy with SAM

```bash
# Navigate to project directory
cd c:/dev/personal/AI-SmartBots-Boto3-Bedrock-LLMs/smart-payment-caller

# Build the Lambda package
sam build

# Deploy (first time with guided setup)
sam deploy --guided

# Answer the prompts:
#   Stack name: payment-bot-poc
#   AWS Region: us-east-1
#   Parameter Environment: dev
#   Parameter BedrockModelId: <YOUR_CUSTOM_INFERENCE_PROFILE_ARN>
#       For POC: mistral.mistral-7b-instruct-v0:2 (foundation model)
#       For Production: arn:aws:bedrock:us-east-1:ACCOUNT:inference-profile/PROFILE_NAME
#   Parameter StripeSecretParam: /payment-bot/stripe-secret
#   Confirm changes: Y
#   Allow SAM CLI IAM role creation: Y
#   Disable rollback: N
#   Save arguments to samconfig.toml: Y

# Note: See docs/CUSTOM_MODEL_SETUP.md for creating custom inference profile
```

### Step 4: Test Locally (Without Amazon Connect)

```bash
# Test the Lambda function with test event
sam local invoke PaymentBotFunction -e events/test-event.json

# Expected output:
# {
#   "statusCode": 200,
#   "response": "Thank you! I've validated your Visa card ending in 4242...",
#   "stripeToken": "tok_xxxxxxxxxxxxx",
#   "cardBrand": "Visa",
#   "last4": "4242",
#   "metadata": {
#     "pci_compliant": true,
#     "chd_masked": true
#   }
# }
```

### Step 5: Verify PCI Compliance

```bash
# Check CloudWatch logs for CHD leakage
aws logs filter-log-events \
  --log-group-name /aws/lambda/payment-bot-handler-dev \
  --filter-pattern "4242424242424242" \
  --region us-east-1

# Expected: No events found (CHD is masked)

# Check S3 audit logs
aws s3 ls s3://payment-bot-audit-logs-dev-YOUR_ACCOUNT_ID/audit/ --recursive

# Download and verify masking
aws s3 cp s3://payment-bot-audit-logs-dev-YOUR_ACCOUNT_ID/audit/2025/10/23/test-session-xxx.json - | jq .
```

---

## 🎤 Amazon Connect Integration (Optional Full IVR Test)

### Step 1: Create Amazon Connect Instance

1. Go to: https://console.aws.amazon.com/connect/
2. Click "Add an instance"
3. Choose "Store users within Amazon Connect"
4. Instance name: `payment-bot-poc`
5. Create administrator account
6. Default settings for rest
7. Click "Create instance"

### Step 2: Claim Phone Number

1. Open your Connect instance
2. Go to "Channels" → "Phone numbers"
3. Click "Claim a number"
4. Choose country and type (DID or Toll-free)
5. Click "Claim"

### Step 3: Add Lambda Function to Connect

1. In Connect console, go to "Contact flows" → "AWS Lambda"
2. Click "Add Lambda function"
3. Select: `payment-bot-handler-dev`
4. Click "Add Lambda function"

### Step 4: Import Contact Flow

1. Go to "Contact flows" → "Create contact flow"
2. Click "Save" → "Import flow (beta)"
3. Upload: `connect-flows/payment-bot-flow.json`
4. Edit the "Invoke AWS Lambda function" block:
   - Replace `REPLACE_WITH_YOUR_LAMBDA_ARN` with actual ARN from SAM output
5. Edit "Transfer to queue" block:
   - Replace `REPLACE_WITH_YOUR_QUEUE_ARN` with your queue ARN
6. Click "Save" → "Publish"

### Step 5: Assign Contact Flow to Phone Number

1. Go to "Channels" → "Phone numbers"
2. Click your claimed number
3. Under "Contact flow / IVR", select your new flow
4. Click "Save"

### Step 6: Test End-to-End

```bash
# Call your Connect phone number
# Expected flow:
# 1. "Welcome to our secure payment system..."
# 2. "Please say YES to continue..."
# 3. "Please enter your 16-digit card number..." → Enter: 4242424242424242#
# 4. "Enter expiration date..." → Enter: 1225#
# 5. "Enter security code..." → Enter: 123#
# 6. Lambda processes (masks CHD, calls Bedrock, tokenizes with Stripe)
# 7. "Your payment has been processed successfully..."
```

---

## 🧪 Test Cards (Stripe Test Mode)

| Card Number | Result | Expected Behavior |
|-------------|--------|-------------------|
| 4242424242424242 | Success | Token created, payment validated |
| 4000000000009995 | Declined | Stripe returns "insufficient funds" |
| 4000000000000069 | Expired | Stripe returns "card expired" |
| 5555555555554444 | Success | Mastercard token |
| 378282246310005 | Success | Amex token (4-digit CVV) |

All test cards use:
- **Expiry**: Any future date (e.g., 12/25)
- **CVV**: Any 3 digits (or 4 for Amex)

---

## 📊 Cost Estimate (POC Phase - 1 Month)

| Service | Usage | Cost |
|---------|-------|------|
| **Bedrock (Mistral 7B)** | 30 calls × 150 tokens × $0.00015/1k | $0.68 |
| **Lambda** | 30 invocations × 512MB × 5s | Free tier |
| **S3 Storage** | 30 audit logs × 5KB | $0.01 |
| **KMS** | 1 key | $1.00 |
| **Connect** | 30 calls × 3 min × $0.018/min | $1.62 |
| **SSM Parameter** | 1 SecureString | Free |
| **CloudWatch Logs** | 1GB | Free tier |
| **Total** | | **~$3.31/month** |

---

## 🔒 PCI Compliance Checklist

### ✅ Implemented in POC

- [x] **CHD masking before AI** (Lambda masks immediately)
- [x] **Encrypted storage** (S3 with KMS encryption)
- [x] **No CHD in logs** (CloudWatch scrubbed)
- [x] **Stripe tokenization** (removes CHD from scope)
- [x] **Audit trail** (all transactions logged)
- [x] **IAM least privilege** (Lambda role scoped)
- [x] **Secrets management** (SSM Parameter Store)

### 🚧 Required for Production (Not in POC)

- [ ] **Network isolation** (VPC with private subnets)
- [ ] **WAF protection** (rate limiting, IP blocking)
- [ ] **DTMF encryption** (Connect native encryption)
- [ ] **MFA for admin access** (AWS IAM)
- [ ] **Regular security scans** (Inspector, GuardDuty)
- [ ] **Incident response plan** (documented procedures)
- [ ] **QSA validation** (third-party audit)

---

## 📈 Monitoring & Debugging

### View Lambda Logs

```bash
# Stream logs in real-time
sam logs -n PaymentBotFunction --stack-name payment-bot-poc --tail

# Search for errors
aws logs filter-log-events \
  --log-group-name /aws/lambda/payment-bot-handler-dev \
  --filter-pattern "ERROR" \
  --region us-east-1
```

### Check Bedrock Usage

```bash
# View Bedrock metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name Invocations \
  --dimensions Name=ModelId,Value=mistral.mistral-7b-instruct-v0:2 \
  --start-time 2025-10-23T00:00:00Z \
  --end-time 2025-10-23T23:59:59Z \
  --period 3600 \
  --statistics Sum \
  --region us-east-1
```

### Verify Stripe Tokens

```bash
# List recent Stripe tokens (in Stripe dashboard or CLI)
stripe tokens list --limit 10
```

---

## 🐛 Troubleshooting

### Issue: Bedrock access denied

**Error**: `AccessDeniedException: Could not access model`

**Solution**:
```bash
# Verify model access is granted
aws bedrock list-foundation-models --region us-east-1 | grep mistral

# Request access in console if not available
# https://console.aws.amazon.com/bedrock/ → Model access
```

### Issue: Stripe key not found

**Error**: `ParameterNotFound: /payment-bot/stripe-secret`

**Solution**:
```bash
# Recreate the parameter
aws ssm put-parameter \
  --name "/payment-bot/stripe-secret" \
  --value "sk_test_YOUR_KEY" \
  --type SecureString \
  --region us-east-1
```

### Issue: S3 bucket already exists

**Error**: `BucketAlreadyExists`

**Solution**: Update `template.yaml` line 31 to use unique name:
```yaml
BucketName: !Sub payment-bot-audit-logs-${Environment}-${AWS::AccountId}-v2
```

### Issue: Lambda timeout

**Error**: `Task timed out after 30.00 seconds`

**Solution**: Increase timeout in `template.yaml`:
```yaml
Globals:
  Function:
    Timeout: 60  # Increase to 60 seconds
```

---

## 🎓 Next Steps

1. **✅ POC Validated** → Test with real Connect phone call
2. **Add DTMF direct-to-Stripe** → Bypass Lambda entirely for CHD
3. **Terraform migration** → Replace SAM with IaC for production
4. **Security hardening** → Add VPC, WAF, GuardDuty
5. **QSA audit prep** → Generate compliance evidence package

---

## 📚 Additional Resources

- [Amazon Connect Documentation](https://docs.aws.amazon.com/connect/)
- [Amazon Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)
- [Stripe API Reference](https://stripe.com/docs/api)
- [PCI DSS SAQ A-EP](https://www.pcisecuritystandards.org/document_library)
- [AWS Security Best Practices](https://aws.amazon.com/security/best-practices/)

---

## 🆘 Support

For issues or questions:
1. Check CloudWatch logs: `/aws/lambda/payment-bot-handler-dev`
2. Review S3 audit logs: `s3://payment-bot-audit-logs-dev-*/audit/`
3. Test locally: `sam local invoke -e events/test-event.json`

**Project Structure**:
```
smart-payment-caller/
├── src/
│   ├── lambda_handler.py      # Main Lambda function
│   └── requirements.txt        # Python dependencies
├── events/
│   └── test-event.json        # Test event for local testing
├── connect-flows/
│   └── payment-bot-flow.json  # Amazon Connect flow
├── terraform/                  # (Future) Terraform modules
├── docs/                       # Documentation
└── template.yaml              # SAM template for deployment
```
