# Payment Smart Bot - Troubleshooting Cheatsheet

Quick reference for common issues and solutions.

---

## 🔍 Quick Diagnostics

```bash
# Check if Lambda is deployed
aws lambda get-function --function-name payment-smart-bot-handler-dev

# View recent logs (last 5 minutes)
MSYS_NO_PATHCONV=1 aws logs tail /aws/lambda/payment-smart-bot-handler-dev --since 5m

# Check API Gateway endpoint
cd terraform && terraform output api_endpoint

# Test API is responding
curl -X POST $(terraform output -raw api_endpoint) \
  -H 'Content-Type: application/json' \
  -d '{"sessionId": "diagnostic", "message": "test"}'

# Check DynamoDB table
aws dynamodb describe-table --table-name payment-smart-bot-sessions-dev

# Check Bedrock model access
aws bedrock list-foundation-models --region us-east-1 | grep llama3-2-1b
```

---

## ❌ Error: "No module named 'stripe'"

**Symptom:** Lambda returns 500 error, logs show `ImportModuleError`

**Cause:** Dependencies not included in Lambda package

**Solution:**
```bash
cd payment-smart-bot/terraform
python build_lambda.py
terraform apply -auto-approve
```

**Verify:**
```bash
# Package should be ~20MB
ls -lh lambda_function.zip
```

---

## ❌ Error: "ValidationException: Invocation of model not supported"

**Symptom:** 
```
Bedrock error: Invocation of model ID meta.llama3-2-1b-instruct-v1:0 
with on-demand throughput isn't supported. Retry with inference profile.
```

**Cause:** Using direct model ID instead of inference profile

**Solution:**

Edit `terraform/terraform.tfvars`:
```hcl
# WRONG ❌
bedrock_model_id = "meta.llama3-2-1b-instruct-v1:0"

# CORRECT ✅
bedrock_model_id = "us.meta.llama3-2-1b-instruct-v1:0"
```

```bash
terraform apply -auto-approve
```

**List Available Profiles:**
```bash
aws bedrock list-inference-profiles --region us-east-1
```

---

## ❌ Error: "AccessDeniedException" from Bedrock

**Symptom:**
```
User arn:aws:sts::XXX:assumed-role/payment-smart-bot-lambda-role-dev 
is not authorized to perform: bedrock:InvokeModel on resource: 
arn:aws:bedrock:us-west-2::foundation-model/meta.llama3-2-1b-instruct-v1:0
```

**Cause:** IAM policy doesn't allow cross-region access

**Solution:**

Check `terraform/iam.tf` has:
```hcl
Resource = [
  "arn:aws:bedrock:*::foundation-model/*",  # Note the * wildcard
  "arn:aws:bedrock:${var.aws_region}:${data.aws_caller_identity.current.account_id}:inference-profile/*"
]

Action = [
  "bedrock:InvokeModel",
  "bedrock:InvokeModelWithResponseStream",
  "bedrock:Converse",        # Required!
  "bedrock:ConverseStream"
]
```

```bash
terraform apply -auto-approve
```

---

## ❌ Error: Bedrock Model Not Available

**Symptom:** AccessDeniedException or model not found

**Cause:** Model not enabled in AWS Bedrock

**Solution:**

1. Go to AWS Console → Bedrock → Model Access
2. Click "Manage model access"
3. Enable "Meta Llama 3.2 1B Instruct"
4. Submit (usually instant approval)

**Verify:**
```bash
aws bedrock get-foundation-model \
  --model-identifier meta.llama3-2-1b-instruct-v1:0 \
  --region us-east-1
```

---

## ❌ Error: Stripe "Raw Card Not Allowed"

**Symptom:**
```
❌ Payment processing failed: Sending credit card numbers directly to 
the Stripe API is generally unsafe.
```

**Cause:** This is EXPECTED behavior in test mode

**Explanation:** 
- Stripe blocks raw card numbers for security
- This is correct PCI-DSS behavior
- Not an error in your code!

**For Production:**
1. Use Stripe Elements on frontend
2. Tokenize card client-side
3. Send token (not raw card) to backend

**Test Workaround:**
- Enable raw card data APIs in Stripe Dashboard (not recommended)
- Better: Test the flow up to confirmation, validate bot behavior

---

## ❌ Error: "module 'stripe' has no attribute 'error'"

**Symptom:** Lambda crashes with AttributeError

**Cause:** Using old Stripe SDK error handling

**Solution:**

Edit `lambda/payment_handler.py`:
```python
# OLD ❌
except stripe.error.CardError as e:
    error_msg = e.error.message

# NEW ✅  
except stripe.CardError as e:
    error_msg = e.user_message
```

```bash
python build_lambda.py
terraform apply -auto-approve
```

---

## ❌ Error: API Returns 500 Internal Server Error

**Diagnostic Steps:**

1. **Check Lambda logs:**
```bash
MSYS_NO_PATHCONV=1 aws logs tail /aws/lambda/payment-smart-bot-handler-dev --since 5m
```

2. **Check API Gateway logs:**
```bash
MSYS_NO_PATHCONV=1 aws logs tail /aws/apigateway/payment-smart-bot-dev --since 5m
```

3. **Test Lambda directly:**
```bash
aws lambda invoke \
  --function-name payment-smart-bot-handler-dev \
  --payload '{"body": "{\"sessionId\": \"test\", \"message\": \"hello\"}"}' \
  response.json
cat response.json
```

**Common Causes:**
- Missing Stripe API key
- Invalid Bedrock model ID
- Python syntax errors
- Missing dependencies

---

## ❌ Error: Terraform "Inconsistent dependency lock file"

**Symptom:** 
```
Error: Inconsistent dependency lock file
provider registry.terraform.io/hashicorp/local: required by this 
configuration but no version is selected
```

**Solution:**
```bash
terraform init -upgrade
terraform apply
```

---

## ❌ Error: Session Not Persisting

**Diagnostic:**
```bash
# Check if session exists
aws dynamodb get-item \
  --table-name payment-smart-bot-sessions-dev \
  --key '{"sessionId": {"S": "YOUR_SESSION_ID"}}'

# Scan all sessions
aws dynamodb scan \
  --table-name payment-smart-bot-sessions-dev \
  --limit 10
```

**Common Causes:**
1. Different sessionId used in requests
2. Session expired (TTL = 1 hour default)
3. DynamoDB IAM permissions missing

**Solution:**
- Use same sessionId across conversation
- Check IAM role has DynamoDB permissions
- Verify TTL setting in `terraform/dynamodb.tf`

---

## ❌ Error: Build Script Fails on Windows

**Symptom:** `zip: command not found` or similar

**Solution:** Use Python build script (not bash):
```bash
python terraform/build_lambda.py
```

Works on all platforms (Windows, Linux, Mac).

---

## ❌ Error: CloudWatch Logs Path Issue (Git Bash)

**Symptom:**
```
InvalidParameterException: Value 'C:/Program Files/Git/aws/lambda/...' 
failed to satisfy constraint
```

**Cause:** Git Bash converts Unix paths to Windows paths

**Solution:**
```bash
# Add MSYS_NO_PATHCONV=1
MSYS_NO_PATHCONV=1 aws logs tail /aws/lambda/payment-smart-bot-handler-dev --follow
```

**Or use PowerShell:**
```powershell
aws logs tail /aws/lambda/payment-smart-bot-handler-dev --follow
```

---

## ❌ Error: High Lambda Duration / Timeout

**Symptom:** Requests taking > 30 seconds or timing out

**Diagnostic:**
```bash
# Check Lambda metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=payment-smart-bot-handler-dev \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum
```

**Solutions:**
1. Increase Lambda timeout (current: 60s)
2. Increase Lambda memory (improves CPU)
3. Check Bedrock API latency
4. Review code for blocking operations

Edit `terraform/terraform.tfvars`:
```hcl
lambda_timeout = 120  # Increase if needed
lambda_memory_size = 1024  # More memory = more CPU
```

---

## 🔍 Debugging Commands

### Lambda Function
```bash
# Get function configuration
aws lambda get-function-configuration \
  --function-name payment-smart-bot-handler-dev

# Get environment variables
aws lambda get-function-configuration \
  --function-name payment-smart-bot-handler-dev \
  --query 'Environment.Variables'

# Download deployment package
aws lambda get-function \
  --function-name payment-smart-bot-handler-dev \
  --query 'Code.Location' --output text | xargs curl -o lambda.zip

# Test invoke
aws lambda invoke \
  --function-name payment-smart-bot-handler-dev \
  --payload file://test_event.json \
  --cli-binary-format raw-in-base64-out \
  response.json
```

### API Gateway
```bash
# Get API details
aws apigateway get-rest-api --rest-api-id $(cd terraform && terraform output -raw api_gateway_id)

# Get deployment
aws apigateway get-deployment \
  --rest-api-id $(cd terraform && terraform output -raw api_gateway_id) \
  --deployment-id $(aws apigateway get-stages --rest-api-id $(cd terraform && terraform output -raw api_gateway_id) --query 'item[0].deploymentId' --output text)
```

### DynamoDB
```bash
# Get table description
aws dynamodb describe-table --table-name payment-smart-bot-sessions-dev

# Query by session ID
aws dynamodb query \
  --table-name payment-smart-bot-sessions-dev \
  --key-condition-expression "sessionId = :sid" \
  --expression-attribute-values '{":sid": {"S": "test-001"}}'

# Count items
aws dynamodb scan \
  --table-name payment-smart-bot-sessions-dev \
  --select COUNT
```

### CloudWatch Alarms
```bash
# List all alarms
aws cloudwatch describe-alarms \
  --alarm-name-prefix payment-smart-bot

# Get alarm history
aws cloudwatch describe-alarm-history \
  --alarm-name payment-smart-bot-lambda-errors-dev \
  --max-records 10
```

### Secrets Manager
```bash
# Get secret value (requires IAM permissions)
aws secretsmanager get-secret-value \
  --secret-id payment-smart-bot/stripe-key-dev \
  --query 'SecretString' --output text
```

---

## 🧹 Cleanup Commands

```bash
# Destroy all infrastructure
cd terraform
terraform destroy -auto-approve

# Remove local build artifacts
rm -rf build/ lambda_function.zip

# Clear CloudWatch logs
aws logs delete-log-group --log-group-name /aws/lambda/payment-smart-bot-handler-dev
aws logs delete-log-group --log-group-name /aws/apigateway/payment-smart-bot-dev
```

---

## 📊 Performance Monitoring

```bash
# Get Lambda invocation count
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=payment-smart-bot-handler-dev \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum

# Get error rate
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=payment-smart-bot-handler-dev \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum

# Get throttles
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Throttles \
  --dimensions Name=FunctionName,Value=payment-smart-bot-handler-dev \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum
```

---

## 🆘 Emergency Rollback

If deployment breaks:

```bash
cd terraform

# View last working state
terraform show

# Revert to previous code
git log --oneline
git checkout <previous-commit-hash> lambda/payment_handler.py

# Rebuild and redeploy
python build_lambda.py
terraform apply -auto-approve
```

---

## 📞 Getting Help

1. **Check logs first** - 90% of issues visible in CloudWatch
2. **Review documentation** - See DEPLOYMENT_GUIDE.md
3. **Search error message** - Copy exact error to Google/ChatGPT
4. **AWS Support** - For Bedrock/infrastructure issues
5. **Stripe Support** - For payment processing issues
6. **GitHub Issues** - Report bugs or ask questions

---

**Last Updated:** October 15, 2025  
**Version:** 1.0.0
