# Testing Guide - Smart Payment Caller

## Quick Test Options

### 🚀 Option 1: Local Testing (Fastest - 2 minutes)
Test without deploying to AWS - perfect for development.

### ☁️ Option 2: AWS Lambda Testing (5 minutes)
Test deployed Lambda function directly.

### 📞 Option 3: Full IVR Testing (15 minutes)
End-to-end test with Amazon Connect phone call.

---

## 🚀 Option 1: Local Testing (Recommended First)

### Prerequisites
```bash
# Ensure SAM CLI is installed
sam --version

# Ensure Docker is running (SAM uses Docker for local Lambda)
docker --version
```

### Step 1: Navigate to Project
```bash
cd c:/dev/personal/AI-SmartBots-Boto3-Bedrock-LLMs/smart-payment-caller
```

### Step 2: Build Lambda Package
```bash
sam build
```

**Expected output**:
```
Build Succeeded

Built Artifacts  : .aws-sam/build
Built Template   : .aws-sam/build/template.yaml
```

### Step 3: Test with Mock Event
```bash
# Test with provided test event
sam local invoke PaymentBotFunction -e events/test-event.json
```

**Expected output**:
```json
{
  "statusCode": 200,
  "response": "Thank you! I've validated your Visa card ending in 4242...",
  "sessionId": "a3f7d2e1c5b8...",
  "stripeToken": "tok_xxxxxxxxxxxxx",
  "cardBrand": "Visa",
  "last4": "4242",
  "metadata": {
    "timestamp": "2025-10-24T10:30:00.123Z",
    "intent": "validate_payment",
    "pci_compliant": true,
    "chd_masked": true
  }
}
```

### Step 4: Verify CHD Masking

Check the Lambda logs (printed to console):
```
[SESSION] ID: test-session-12345... | Hash: a3f7d2e1
[AUDIT] Stored: s3://payment-bot-audit-logs-dev-.../audit/2025/10/24/...
[STRIPE] Tokenizing card ending in ****4242
[BEDROCK] Response: Thank you! Your Visa card has been validated...
[RESPONSE] Thank you! I've validated your...
[END] Processing complete
```

✅ **Success if**: You see `****4242` (not full card number) in logs!

### Step 5: Test Different Scenarios

#### Test Success Case
```bash
sam local invoke PaymentBotFunction -e events/test-event.json
```

#### Test Declined Card
Create `events/test-declined.json`:
```json
{
  "Details": {
    "ContactData": {
      "ContactId": "test-declined-001"
    },
    "Parameters": {
      "cardNumber": "4000000000009995",
      "expiryMonth": "12",
      "expiryYear": "25",
      "cvv": "123",
      "intentType": "validate_payment",
      "userInput": "Process my payment"
    }
  }
}
```

Run test:
```bash
sam local invoke PaymentBotFunction -e events/test-declined.json
```

Expected: `"success": false` with decline message

#### Test Invalid Card
Create `events/test-invalid.json`:
```json
{
  "Details": {
    "ContactData": {
      "ContactId": "test-invalid-001"
    },
    "Parameters": {
      "cardNumber": "1234567890123456",
      "expiryMonth": "12",
      "expiryYear": "25",
      "cvv": "123",
      "intentType": "validate_payment",
      "userInput": "Process my payment"
    }
  }
}
```

Run test:
```bash
sam local invoke PaymentBotFunction -e events/test-invalid.json
```

Expected: Error message about invalid card

---

## ☁️ Option 2: AWS Lambda Testing

### Prerequisites
```bash
# Deploy first (if not already deployed)
sam deploy --guided
```

### Method 1: Using SAM CLI

#### Test Deployed Function
```bash
# Invoke deployed Lambda
sam remote invoke PaymentBotFunction \
  --stack-name payment-bot-poc \
  --event-file events/test-event.json
```

#### View Real-time Logs
```bash
# Stream logs in real-time
sam logs -n PaymentBotFunction \
  --stack-name payment-bot-poc \
  --tail
```

### Method 2: Using AWS CLI

#### Invoke Lambda Directly
```bash
# Get function name
FUNCTION_NAME=$(aws cloudformation describe-stacks \
  --stack-name payment-bot-poc \
  --query 'Stacks[0].Outputs[?OutputKey==`PaymentBotFunctionName`].OutputValue' \
  --output text)

echo "Function: $FUNCTION_NAME"

# Invoke function
aws lambda invoke \
  --function-name $FUNCTION_NAME \
  --payload file://events/test-event.json \
  --cli-binary-format raw-in-base64-out \
  response.json

# View response
cat response.json | jq .
```

### Method 3: Using AWS Console

1. Go to: https://console.aws.amazon.com/lambda/
2. Search for: `payment-bot-handler-dev`
3. Click the function
4. Click "Test" tab
5. Create test event:
   - Event name: `TestPayment`
   - Copy contents from `events/test-event.json`
6. Click "Test"
7. View execution results

### Verify PCI Compliance

#### Check 1: No CHD in CloudWatch Logs
```bash
# Search for full card number (should return 0 results)
aws logs filter-log-events \
  --log-group-name /aws/lambda/payment-bot-handler-dev \
  --filter-pattern "4242424242424242" \
  --region us-east-1 \
  --max-items 10

# Expected: "events": []
```

#### Check 2: Masked Data in S3 Audit Logs
```bash
# Get bucket name
BUCKET=$(aws cloudformation describe-stacks \
  --stack-name payment-bot-poc \
  --query 'Stacks[0].Outputs[?OutputKey==`AuditLogsBucketName`].OutputValue' \
  --output text)

echo "Audit Bucket: $BUCKET"

# List audit logs
aws s3 ls s3://$BUCKET/audit/ --recursive | tail -5

# Download latest log
LATEST=$(aws s3 ls s3://$BUCKET/audit/ --recursive | tail -1 | awk '{print $4}')
aws s3 cp s3://$BUCKET/$LATEST - | jq .

# Verify: Card numbers should show as "************4242"
```

#### Check 3: Stripe Token Created
```bash
# Check response contains Stripe token
cat response.json | jq '.stripeToken'

# Expected: "tok_xxxxxxxxxxxxx"
```

---

## 📞 Option 3: Full IVR Testing with Amazon Connect

### Prerequisites
- Amazon Connect instance created
- Phone number claimed
- Lambda function added to Connect
- Contact flow imported

### Step 1: Setup Amazon Connect (First Time Only)

#### Create Connect Instance
```bash
# Open AWS Console
start https://console.aws.amazon.com/connect/
```

1. Click "Add an instance"
2. Instance alias: `payment-bot-test`
3. Create admin user
4. Default settings → Create

#### Claim Phone Number
1. Open Connect instance
2. Go to "Channels" → "Phone numbers"
3. Click "Claim a number"
4. Choose country: United States
5. Choose type: DID or Toll-free
6. Click "Claim"

**Your number**: +1-XXX-XXX-XXXX

#### Add Lambda Function
1. In Connect → "Contact flows" → "AWS Lambda"
2. Click "Add Lambda function"
3. Select region: us-east-1
4. Select function: `payment-bot-handler-dev`
5. Click "Add Lambda function"

#### Import Contact Flow
1. Go to "Contact flows" → "Create contact flow"
2. Name: `Payment Bot Test Flow`
3. Click "Save" → "Import flow (beta)"
4. Upload: `connect-flows/payment-bot-flow.json`
5. Edit "Invoke AWS Lambda function" block:
   - Function ARN: (paste your Lambda ARN)
6. Click "Save" → "Publish"

#### Assign Flow to Number
1. Go to "Channels" → "Phone numbers"
2. Click your phone number
3. Contact flow: Select `Payment Bot Test Flow`
4. Click "Save"

### Step 2: Test with Phone Call

#### Call Your Number
```
Dial: +1-XXX-XXX-XXXX (your Connect number)
```

#### Expected Call Flow

**1. Welcome Message**
```
🔊 "Welcome to our secure payment system. 
    I'll help you process your payment today. 
    All your information is encrypted and PCI compliant."
```

**2. Payment Intent**
```
🔊 "I can help you make a payment. 
    Please press 1 to continue, or 2 to speak with an agent."

👤 Press: 1
```

**3. Card Number Capture**
```
🔊 "Please enter your 16-digit card number followed by the pound key."

👤 Enter: 4242424242424242#
```

**4. Expiry Date**
```
🔊 "Thank you. Now enter the expiration date as 4 digits. 
    Month then year. For example, 1 2 2 5 for December 2025."

👤 Enter: 1225#
```

**5. CVV**
```
🔊 "Finally, enter the 3-digit security code on the back of your card."

👤 Enter: 123#
```

**6. Processing (Lambda Invoked)**
```
⏳ Lambda masks CHD → Stripe tokenizes → Bedrock responds
   (2-5 seconds)
```

**7. Confirmation**
```
🔊 "Thank you! Your Visa card ending in 4242 has been validated. 
    Your payment has been processed successfully. 
    Your confirmation number will be sent to you. 
    Thank you for your payment. Goodbye."

📞 Call ends
```

### Step 3: Verify Transaction

#### Check Lambda Logs
```bash
# View logs from the call
sam logs -n PaymentBotFunction \
  --stack-name payment-bot-poc \
  --start-time '10min ago'
```

Look for:
- `[SESSION] ID: ...`
- `[STRIPE] Tokenizing card ending in ****4242`
- `[BEDROCK] Response: ...`
- `[RESPONSE] Thank you!...`

#### Check Audit Logs
```bash
# List recent audit logs
BUCKET=$(aws cloudformation describe-stacks \
  --stack-name payment-bot-poc \
  --query 'Stacks[0].Outputs[?OutputKey==`AuditLogsBucketName`].OutputValue' \
  --output text)

aws s3 ls s3://$BUCKET/audit/$(date +%Y/%m/%d)/ | tail -5
```

#### Check Connect Metrics
1. Go to Connect console → "Metrics and quality"
2. View "Real-time metrics"
3. Check:
   - Calls handled
   - Lambda invocations
   - Average call duration

---

## 🧪 Test Scenarios

### Test Case 1: Successful Payment (Visa)
**Input**:
- Card: `4242424242424242`
- Expiry: `1225`
- CVV: `123`

**Expected**:
- ✅ Stripe token created
- ✅ "Your Visa card... validated"
- ✅ No CHD in logs

### Test Case 2: Declined Card
**Input**:
- Card: `4000000000009995`
- Expiry: `1225`
- CVV: `123`

**Expected**:
- ❌ Stripe returns decline
- 🔊 "Card validation failed. Please verify your card details."

### Test Case 3: Expired Card
**Input**:
- Card: `4000000000000069`
- Expiry: `1225`
- CVV: `123`

**Expected**:
- ❌ Stripe returns "card expired"
- 🔊 "Card validation failed..."

### Test Case 4: Mastercard
**Input**:
- Card: `5555555555554444`
- Expiry: `1225`
- CVV: `123`

**Expected**:
- ✅ "Your Mastercard... validated"

### Test Case 5: Amex (4-digit CVV)
**Input**:
- Card: `378282246310005`
- Expiry: `1225`
- CVV: `1234`

**Expected**:
- ✅ "Your American Express... validated"

---

## 🐛 Troubleshooting

### Issue: Local Test Fails with Stripe Error

**Error**: `stripe.error.AuthenticationError`

**Solution**:
```bash
# Check SSM parameter exists
aws ssm get-parameter \
  --name /payment-bot/stripe-secret \
  --with-decryption

# If missing, create it
aws ssm put-parameter \
  --name "/payment-bot/stripe-secret" \
  --value "sk_test_YOUR_KEY" \
  --type SecureString
```

### Issue: Bedrock Access Denied

**Error**: `AccessDeniedException: Could not access model`

**Solution**:
1. Go to: https://console.aws.amazon.com/bedrock/
2. Click "Model access" → "Manage model access"
3. Enable "Mistral 7B Instruct"
4. Wait 2-5 minutes

### Issue: Lambda Timeout

**Error**: `Task timed out after 30.00 seconds`

**Solution**:
```yaml
# Edit template.yaml line 15
Timeout: 60  # Increase to 60 seconds
```

Then redeploy:
```bash
sam build && sam deploy
```

### Issue: Connect Can't Invoke Lambda

**Error**: Lambda not listed in Connect

**Solution**:
```bash
# Add Lambda permission for Connect
FUNCTION_NAME=$(aws cloudformation describe-stacks \
  --stack-name payment-bot-poc \
  --query 'Stacks[0].Outputs[?OutputKey==`PaymentBotFunctionName`].OutputValue' \
  --output text)

aws lambda add-permission \
  --function-name $FUNCTION_NAME \
  --statement-id AllowConnectInvoke \
  --action lambda:InvokeFunction \
  --principal connect.amazonaws.com
```

### Issue: No Audio on Call

**Error**: Silence after dialing

**Solution**:
1. Check contact flow is published (not just saved)
2. Verify flow is assigned to phone number
3. Test with different phone (some carriers block)

---

## 📊 Performance Benchmarks

### Expected Metrics

| Metric | Target | Measured |
|--------|--------|----------|
| Lambda Cold Start | < 3s | ___ |
| Lambda Warm | < 1s | ___ |
| Stripe Tokenization | < 500ms | ___ |
| Bedrock Response | < 2s | ___ |
| Total Call Duration | < 2 min | ___ |

### Measure Performance

```bash
# Get Lambda duration metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=payment-bot-handler-dev \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Average,Maximum \
  --region us-east-1
```

---

## ✅ Success Checklist

After testing, verify:

- [ ] Local test returns `statusCode: 200`
- [ ] Stripe token created (`tok_xxxxx`)
- [ ] No CHD in CloudWatch logs
- [ ] Masked data in S3 audit logs (`****4242`)
- [ ] Bedrock returns natural language
- [ ] Connect call completes successfully
- [ ] Audio quality is clear
- [ ] All test cards work correctly

---

## 🎯 Quick Test Commands (Copy & Paste)

### Test Locally (Fastest)
```bash
cd c:/dev/personal/AI-SmartBots-Boto3-Bedrock-LLMs/smart-payment-caller
sam build
sam local invoke PaymentBotFunction -e events/test-event.json
```

### Test on AWS
```bash
sam remote invoke PaymentBotFunction \
  --stack-name payment-bot-poc \
  --event-file events/test-event.json
```

### Check Logs
```bash
sam logs -n PaymentBotFunction --stack-name payment-bot-poc --tail
```

### Verify CHD Masking
```bash
aws logs filter-log-events \
  --log-group-name /aws/lambda/payment-bot-handler-dev \
  --filter-pattern "4242424242424242" \
  --region us-east-1
# Expected: No results (CHD is masked)
```

---

## 📞 Test Without Deploying Amazon Connect

If you don't want to set up Connect yet, you can simulate the flow:

```bash
# Create test event that mimics Connect
cat > events/test-connect-simulation.json << 'EOF'
{
  "Details": {
    "ContactData": {
      "ContactId": "simulated-call-001",
      "CustomerEndpoint": {
        "Address": "+15551234567",
        "Type": "TELEPHONE_NUMBER"
      }
    },
    "Parameters": {
      "cardNumber": "4242424242424242",
      "expiryMonth": "12",
      "expiryYear": "25",
      "cvv": "123",
      "intentType": "validate_payment",
      "userInput": "I want to make a payment"
    }
  }
}
EOF

# Test
sam local invoke PaymentBotFunction -e events/test-connect-simulation.json
```

---

## 🎓 Next Steps After Testing

1. **If tests pass**: Deploy to production environment
2. **If tests fail**: Check [Troubleshooting](#-troubleshooting) section
3. **For production**: Complete [PCI Compliance Checklist](docs/PCI_COMPLIANCE_CHECKLIST.md)

---

**Need help?** Check:
- [README.md](README.md) - Full documentation
- [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md) - Deployment steps
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - System architecture
