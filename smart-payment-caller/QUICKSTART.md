# Quick Start Guide - PCI-Compliant IVR Payment Bot

## ⚡ 5-Minute POC Deployment

### Prerequisites
```bash
# Install tools
pip install awscli aws-sam-cli

# Configure AWS credentials
aws configure
```

### Step 1: Store Stripe Secret
```bash
aws ssm put-parameter \
  --name "/payment-bot/stripe-secret" \
  --value "sk_test_YOUR_STRIPE_TEST_KEY" \
  --type SecureString \
  --region us-east-1
```

Get your key from: https://dashboard.stripe.com/test/apikeys

### Step 2: Set Up Bedrock Model

**For POC (Quick Test)**:
1. Go to: https://console.aws.amazon.com/bedrock/
2. Click "Model access" → "Manage model access"
3. Enable "Mistral 7B Instruct" (foundation model)
4. Wait 2-5 minutes

**For Production (PCI Level 1)**:
```bash
# Create custom inference profile (10 minutes)
aws bedrock create-inference-profile \
  --inference-profile-name "payment-bot-isolated" \
  --model-source '{"copyFrom":"us.mistral.mistral-7b-instruct-v0:2"}'

# Get ARN for deployment
aws bedrock get-inference-profile \
  --inference-profile-identifier payment-bot-isolated \
  --query 'inferenceProfileArn'
```

See [docs/CUSTOM_MODEL_SETUP.md](docs/CUSTOM_MODEL_SETUP.md) for complete setup.

### Step 3: Deploy
```bash
cd c:/dev/personal/AI-SmartBots-Boto3-Bedrock-LLMs/smart-payment-caller

# Build
sam build

# Deploy
sam deploy --guided
```

### Step 4: Test Locally
```bash
sam local invoke PaymentBotFunction -e events/test-event.json
```

### Step 5: Test with Amazon Connect (Optional)
1. Create Connect instance: https://console.aws.amazon.com/connect/
2. Claim a phone number
3. Add Lambda function (from SAM output)
4. Import `connect-flows/payment-bot-flow.json`
5. Call your number!

---

## 📊 Expected Output

```json
{
  "statusCode": 200,
  "response": "Thank you! Your Visa card ending in 4242 has been validated...",
  "stripeToken": "tok_xxxxxxxxxxxxx",
  "cardBrand": "Visa",
  "last4": "4242",
  "metadata": {
    "pci_compliant": true,
    "chd_masked": true
  }
}
```

---

## 🧪 Test Cards

| Card Number | Result |
|-------------|--------|
| 4242424242424242 | ✅ Success |
| 4000000000009995 | ❌ Declined |
| 5555555555554444 | ✅ Mastercard |

Use any future expiry (e.g., 12/25) and any CVV (e.g., 123)

---

## 🔍 Verify PCI Compliance

### Check 1: CHD Masked in Logs
```bash
# Should return NO results
aws logs filter-log-events \
  --log-group-name /aws/lambda/payment-bot-handler-dev \
  --filter-pattern "4242424242424242"
```

### Check 2: Audit Logs Encrypted
```bash
# View masked audit logs
BUCKET=$(aws cloudformation describe-stacks \
  --stack-name payment-bot-poc \
  --query 'Stacks[0].Outputs[?OutputKey==`AuditLogsBucketName`].OutputValue' \
  --output text)

aws s3 ls s3://$BUCKET/audit/ --recursive
aws s3 cp s3://$BUCKET/audit/.../xxx.json - | jq .
```

### Check 3: Lambda Only Sees Masked Data
```bash
# View recent Lambda logs
sam logs -n PaymentBotFunction --stack-name payment-bot-poc --tail
```

You should see:
- ✅ `[AUDIT] Stored: s3://...`
- ✅ `[STRIPE] Tokenizing card ending in ****4242`
- ✅ `[BEDROCK] Response: ...`
- ❌ NO full card numbers

---

## 📚 Documentation

- **Setup**: [README.md](README.md)
- **Architecture**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **PCI Compliance**: [docs/PCI_COMPLIANCE_CHECKLIST.md](docs/PCI_COMPLIANCE_CHECKLIST.md)

---

## 💰 Cost Estimate

**POC (30 test calls)**: ~$3.31/month
- Bedrock (Custom Profile): $1.17
- Lambda: Free tier
- Connect: $1.62
- S3/KMS: $1.01

---

## 🆘 Troubleshooting

### Error: Bedrock access denied
**Solution**: Request model access at https://console.aws.amazon.com/bedrock/

### Error: Stripe key not found
**Solution**: Recreate SSM parameter (see Step 1)

### Error: Lambda timeout
**Solution**: Increase timeout in `template.yaml` (line 15) to 60 seconds

---

## 🚀 Production Checklist

Before going live:
- [ ] Deploy VPC with private subnets
- [ ] Enable AWS WAF
- [ ] Configure GuardDuty
- [ ] Schedule penetration test
- [ ] Complete QSA audit

See: [docs/PCI_COMPLIANCE_CHECKLIST.md](docs/PCI_COMPLIANCE_CHECKLIST.md)

---

## 📞 Support

Questions? Check:
1. CloudWatch Logs: `/aws/lambda/payment-bot-handler-dev`
2. S3 Audit Logs: `s3://payment-bot-audit-logs-*/audit/`
3. Local test: `sam local invoke -e events/test-event.json`
