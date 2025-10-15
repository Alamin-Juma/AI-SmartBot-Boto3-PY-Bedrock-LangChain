# Environment Variables Guide: Python vs JavaScript 🔐

## Quick Comparison

| Aspect | JavaScript/Node.js | Python |
|--------|-------------------|--------|
| **Package** | `dotenv` | `python-dotenv` |
| **Install** | `npm install dotenv` | `pip install python-dotenv` |
| **Load** | `require('dotenv').config()` | `load_dotenv()` |
| **Access** | `process.env.VAR_NAME` | `os.environ.get('VAR_NAME')` |
| **Built-in** | ❌ Need package | ✅ `os.environ` built-in |

---

## 🎯 **How Your Payment Bot Uses Environment Variables**

### **In AWS Lambda (Production)**

**Environment variables are set by Terraform automatically!**

```hcl
# terraform/lambda.tf
resource "aws_lambda_function" "payment_handler" {
  environment {
    variables = {
      BEDROCK_MODEL_ID   = var.bedrock_model_id           # From terraform.tfvars
      AWS_REGION         = var.aws_region                 # From terraform.tfvars
      DYNAMODB_TABLE     = aws_dynamodb_table.sessions.name  # Auto-generated
      STRIPE_SECRET_ARN  = aws_secretsmanager_secret.stripe_key.arn  # Auto-generated
    }
  }
}
```

**Your Python code reads them**:
```python
# payment_handler.py
MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'meta.llama3-2-1b-instruct-v1:0')
# ✅ Lambda provides this automatically - no .env file needed!
```

**Flow**:
```
terraform.tfvars → Terraform → Lambda Environment Variables → os.environ.get()
```

---

### **For Local Testing (Development)**

**Use a .env file just like JavaScript!**

#### Step 1: Install python-dotenv

```bash
cd payment-smart-bot/lambda
pip install python-dotenv
```

#### Step 2: Create .env file

```bash
cp .env.example .env
nano .env
```

**.env file** (never commit this!):
```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_PROFILE=alidev_test  # Your AWS profile

# Bedrock Model
BEDROCK_MODEL_ID=meta.llama3-2-1b-instruct-v1:0

# DynamoDB (use real table or create local one)
DYNAMODB_TABLE=payment-smart-bot-sessions-dev

# Secrets Manager ARN
STRIPE_SECRET_ARN=arn:aws:secretsmanager:us-east-1:875486186130:secret:payment-smart-bot/stripe-key-dev-XXXXXX
```

#### Step 3: Code loads .env automatically

```python
# payment_handler.py (already updated!)
from dotenv import load_dotenv
load_dotenv()  # Loads .env file if it exists

# Now these work locally!
MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'meta.llama3-2-1b-instruct-v1:0')
```

#### Step 4: Test locally

```bash
python payment_handler.py
```

**Output**:
```json
{
  "response": "Hi! I can help you make a payment. What's the name on your card?",
  "status": "collecting",
  "sessionId": "test-local-001",
  "currentStep": "card"
}
```

---

## 📁 **File Structure for Environment Variables**

```
payment-smart-bot/
├── lambda/
│   ├── payment_handler.py       # Uses os.environ.get()
│   ├── requirements.txt         # Includes python-dotenv
│   ├── .env.example             # Template (committed to git)
│   ├── .env                     # Your actual values (gitignored!)
│   └── .gitignore               # Excludes .env
├── terraform/
│   ├── lambda.tf                # Sets Lambda env vars
│   ├── terraform.tfvars.example # Template
│   └── terraform.tfvars         # Your actual values (gitignored!)
```

---

## 🔄 **Complete Flow Diagram**

### **Development (Local Testing)**
```
.env file
   ↓
load_dotenv()
   ↓
os.environ
   ↓
payment_handler.py reads with os.environ.get()
```

### **Production (AWS Lambda)**
```
terraform.tfvars
   ↓
terraform apply
   ↓
Lambda Environment Variables (set by AWS)
   ↓
payment_handler.py reads with os.environ.get()
   ↓
(no .env file needed!)
```

---

## 🛠️ **Setting Up Local Development**

### Option 1: Using .env file (Recommended)

```bash
# 1. Install dependencies
cd payment-smart-bot/lambda
pip install -r requirements.txt

# 2. Create .env file
cp .env.example .env

# 3. Edit .env with your values
nano .env

# 4. Test
python payment_handler.py
```

**.env** (your values):
```bash
AWS_REGION=us-east-1
AWS_PROFILE=alidev_test
BEDROCK_MODEL_ID=meta.llama3-2-1b-instruct-v1:0
DYNAMODB_TABLE=payment-smart-bot-sessions-dev
STRIPE_SECRET_ARN=arn:aws:secretsmanager:us-east-1:875486186130:secret:payment-smart-bot/stripe-key-dev-AbCdEf
```

### Option 2: Using Shell Environment Variables

```bash
# Set in your terminal session
export BEDROCK_MODEL_ID=meta.llama3-2-1b-instruct-v1:0
export AWS_REGION=us-east-1
export DYNAMODB_TABLE=payment-smart-bot-sessions-dev

# Run your script
python payment_handler.py
```

### Option 3: Using AWS CLI Profile

```bash
# Use your AWS profile
AWS_PROFILE=alidev_test python payment_handler.py
```

---

## 🔒 **Security Best Practices**

### ✅ **DO:**
- Use `.env` for local testing
- Add `.env` to `.gitignore`
- Use Secrets Manager for sensitive values (Stripe keys)
- Use Terraform to set Lambda environment variables
- Provide default values: `os.environ.get('VAR', 'default')`

### ❌ **DON'T:**
- Commit `.env` files to git
- Hard-code secrets in your code
- Share `.env` files in Slack/email
- Use same values for dev and prod

---

## 🎓 **Understanding os.environ.get()**

```python
# Syntax
value = os.environ.get('VAR_NAME', 'default_value')
```

**How it works**:

1. **Checks environment variables** (set by OS/Lambda/Docker)
2. **Returns value** if found
3. **Returns default** if not found
4. **Never raises error** (unlike `os.environ['VAR']`)

**Example**:
```python
# If BEDROCK_MODEL_ID is set to "meta.llama3-2-1b-instruct-v1:0"
MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'fallback-model')
# MODEL_ID = "meta.llama3-2-1b-instruct-v1:0"

# If BEDROCK_MODEL_ID is NOT set
MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'fallback-model')
# MODEL_ID = "fallback-model"
```

---

## 🧪 **Testing Different Environments**

### **Test 1: Local with .env**

```bash
cd payment-smart-bot/lambda

# Create .env
echo "BEDROCK_MODEL_ID=meta.llama3-2-1b-instruct-v1:0" > .env
echo "AWS_REGION=us-east-1" >> .env

# Run
python payment_handler.py
```

### **Test 2: Local with Shell Variables**

```bash
BEDROCK_MODEL_ID=meta.llama3-2-1b-instruct-v1:0 \
AWS_REGION=us-east-1 \
python payment_handler.py
```

### **Test 3: Verify Lambda Will Work**

```python
# Check what Lambda will receive
import os
print("Environment Variables:")
print(f"MODEL_ID: {os.environ.get('BEDROCK_MODEL_ID', 'NOT SET')}")
print(f"REGION: {os.environ.get('AWS_REGION', 'NOT SET')}")
print(f"TABLE: {os.environ.get('DYNAMODB_TABLE', 'NOT SET')}")
print(f"STRIPE_ARN: {os.environ.get('STRIPE_SECRET_ARN', 'NOT SET')}")
```

---

## 📝 **Common Patterns**

### **Pattern 1: Required Variable (No Default)**
```python
# Will raise error if not set
MODEL_ID = os.environ['BEDROCK_MODEL_ID']
```

### **Pattern 2: Optional with Default**
```python
# Safe, provides fallback
MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'meta.llama3-2-1b-instruct-v1:0')
```

### **Pattern 3: Type Conversion**
```python
# Convert to int
TIMEOUT = int(os.environ.get('LAMBDA_TIMEOUT', '60'))

# Convert to bool
DEBUG = os.environ.get('DEBUG', 'false').lower() == 'true'

# Convert to list
ALLOWED_ORIGINS = os.environ.get('ALLOWED_ORIGINS', '*').split(',')
```

### **Pattern 4: Validation**
```python
MODEL_ID = os.environ.get('BEDROCK_MODEL_ID')
if not MODEL_ID:
    raise ValueError("BEDROCK_MODEL_ID environment variable must be set")
```

---

## 🆚 **JavaScript vs Python: Side-by-Side**

### **JavaScript (Node.js)**
```javascript
// Install
npm install dotenv

// Load .env file
require('dotenv').config();

// Access variables
const modelId = process.env.BEDROCK_MODEL_ID || 'default-model';
const region = process.env.AWS_REGION;
const timeout = parseInt(process.env.TIMEOUT || '60');

// Check if set
if (!process.env.STRIPE_KEY) {
  throw new Error('STRIPE_KEY not set');
}
```

### **Python**
```python
# Install
pip install python-dotenv

# Load .env file
from dotenv import load_dotenv
load_dotenv()

# Access variables
model_id = os.environ.get('BEDROCK_MODEL_ID', 'default-model')
region = os.environ.get('AWS_REGION')
timeout = int(os.environ.get('TIMEOUT', '60'))

# Check if set
if not os.environ.get('STRIPE_KEY'):
    raise ValueError('STRIPE_KEY not set')
```

**Almost identical!** 🎉

---

## 📚 **Summary**

1. **In Lambda**: Environment variables are set by Terraform automatically
   - No .env file needed
   - `os.environ.get()` reads them directly

2. **For Local Testing**: Use `.env` file with `python-dotenv`
   - Install: `pip install python-dotenv`
   - Load: `load_dotenv()`
   - Access: `os.environ.get('VAR')`

3. **Your Code**: Already updated to support both!
   - Tries to load `.env` if available
   - Falls back to system environment variables
   - Works locally AND in Lambda ✅

---

## 🚀 **Next Steps**

1. **Install python-dotenv** (for local testing):
```bash
cd payment-smart-bot/lambda
pip install python-dotenv
```

2. **Create .env file** (optional, for local testing):
```bash
cp .env.example .env
# Edit with your AWS credentials
```

3. **Deploy to Lambda** (uses Terraform env vars):
```bash
cd ../terraform
terraform apply
# Environment variables set automatically!
```

---

**Your payment_handler.py now supports both local .env files AND Lambda environment variables!** ✅

Ready to test locally or deploy to Lambda?
