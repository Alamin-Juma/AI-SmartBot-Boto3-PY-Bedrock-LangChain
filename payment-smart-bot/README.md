# Payment Smart Bot 💳🤖

A secure, intelligent payment collection bot powered by Amazon Bedrock (Meta Llama 3.2 1B) and AWS Lambda. Designed for PCI-DSS compliant payment information gathering through natural conversational AI.

## 🚀 Quick Start

### Backend Deployment

```bash
# 1. Configure your Stripe key
cd terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your Stripe test key

# 2. Build Lambda package with dependencies
python build_lambda.py

# 3. Deploy infrastructure
terraform init
terraform apply -auto-approve

# 4. Test the API
curl -X POST 'YOUR_API_ENDPOINT' \
  -H 'Content-Type: application/json' \
  -d '{"sessionId": "test-001", "message": "I want to make a payment"}'
```

### Frontend Deployment

```bash
# 1. Install frontend dependencies
cd frontend
pip install -r requirements.txt

# 2. Configure API endpoint
cp .env.example .env
# Edit .env and add your API Gateway endpoint

# 3. Run Streamlit app
streamlit run payment_bot_frontend.py

# Or use quick start script
./start.sh    # Linux/Mac
./start.ps1   # Windows
```

**📖 See [Quick Start Guide](docs/QUICK_START.md) for 5-minute deployment**  
**📘 See [Full Deployment Guide](docs/DEPLOYMENT_GUIDE.md) for detailed instructions**  
**🎨 See [Frontend README](frontend/README.md) for UI documentation**

## � Live Testing Example

![API Testing Example](docs/api-testing-example.png)

*Full payment flow testing with curl commands - collecting name, card, expiry, CVV, and confirmation.*

##  Key Features

### Backend
- **🔒 PCI-DSS Compliant**: Never stores sensitive payment data; tokenizes via Stripe
- **🤖 Small, Efficient AI**: Uses Meta Llama 3.2 1B Instruct via cross-region inference profiles
- **💬 Natural Conversations**: Multi-turn dialogue with intelligent error handling
- **✅ Real-time Validation**: Luhn algorithm for card numbers, format checks for CVV/expiry
- **⚡ Serverless**: AWS Lambda + API Gateway, auto-scales, pay-per-use
- **🛡️ Security**: Secrets Manager, KMS encryption, CloudWatch monitoring
- **📊 Cost-Effective**: ~$0.0005 per customer interaction (~$0.50/1000 customers)

### Frontend
- **🎨 Modern UI**: Beautiful Streamlit interface with gradient design and animations
- **📱 Responsive**: Works seamlessly on desktop, tablet, and mobile devices
- **🔐 Security Indicators**: Clear PCI-DSS compliance badges and security banners
- **📊 Progress Tracking**: Visual progress bar showing payment flow completion
- **🧪 Test Mode**: Easy toggle between test and production environments
- **⚡ Real-time Chat**: Instant conversational payment collection
- **🚀 Quick Actions**: One-click conversation starters for common tasks

## 📋 Table of Contents

- [Architecture](#architecture)
- [Models Available](#models-available)
- [Cost Breakdown](#cost-breakdown)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Security](#security)
- [Testing](#testing)
- [Deployment](#deployment)

## 🏗️ Architecture

```
User → API Gateway → Lambda (Orchestrator) → Bedrock (Llama 3.2 1B)
                         ↓                           ↓
                    DynamoDB                    Validation
                   (Session)                    (Luhn, etc.)
                         ↓
                    Stripe API
                  (Tokenization)
```

### Components:

1. **Frontend**: Web chat interface (React/Streamlit) or messaging platform integration
2. **API Gateway**: Secure HTTPS endpoints for user messages
3. **Lambda Function**: Python-based orchestrator with:
   - Bedrock API calls for AI responses
   - Payment validation logic (Luhn algorithm)
   - Session management (DynamoDB)
   - Stripe integration for tokenization
4. **Amazon Bedrock**: Inference for Llama 3.2 1B Instruct
5. **DynamoDB**: Store conversation sessions (non-sensitive data only)
6. **CloudWatch**: Logging and monitoring (sensitive fields masked)

## 🤖 Models Available

### Recommended: Meta Llama 3.2 1B Instruct
- **Size**: ~1 billion parameters
- **Cost**: $0.0001 per 1,000 input/output tokens
- **Why**: Optimized for instructions, multi-turn chat, 128K context window
- **License**: Open-source (Llama Community License)

### Alternatives:
- **Llama 3.2 3B Instruct**: More capable, slightly higher cost ($0.0002/1k tokens)
- **Mistral 7B Instruct**: Task-oriented, $0.00015-$0.0002 per 1k tokens
- **Custom Models**: Qwen 1.5B via Bedrock Model Import (requires setup)

## 💰 Cost Breakdown

### Per Customer (Single Payment Collection)
Assumes 5-7 conversation turns:
- **Bedrock (Llama 3.2 1B)**: ~1,000 input + 500 output tokens = **$0.00015**
- **Lambda**: 5 invocations @ 128MB, 1s each = **<$0.00001** (free tier)
- **DynamoDB**: 5 read/write units = **<$0.00001** (free tier)
- **API Gateway**: 5 requests = **<$0.00001**
- **Guardrails** (optional): ~$0.0003
- **Stripe Tokenization**: Free (charges apply on actual transactions)

**Total per customer**: **~$0.0005** (0.05 cents)

### Monthly Estimates:
- **1,000 customers**: $0.50
- **10,000 customers**: $5.00
- **100,000 customers**: $50.00 (consider Provisioned Throughput for discounts)

### Cost Optimizations:
- Use **Prompt Caching**: Up to 90% reduction on repeated prefixes
- Switch to **Batch Inference**: 50% discount for non-real-time
- **Provisioned Throughput**: $13-$21/hour for high volume (commit 1-month+)

## 🚀 Quick Start

### Prerequisites

```bash
# AWS Account with:
- Bedrock access (enable Llama 3.2 1B in us-east-1)
- IAM role with bedrock:InvokeModel, lambda:*, dynamodb:*, apigateway:*
- Stripe account (test mode keys)

# Local Tools:
- Python 3.11+
- AWS CLI configured
- AWS SAM CLI (for deployment)
```

### Installation

```bash
# Clone and navigate
cd /c/dev/personal/AI-SmartBots-Boto3-Bedrock-LLMs/payment-smart-bot

# Install dependencies
pip install boto3 stripe python-luhn

# Set environment variables
export AWS_REGION=us-east-1
export STRIPE_SECRET_KEY=sk_test_...
export BEDROCK_MODEL_ID=meta.llama3-2-1b-instruct-v1:0
```

### Run Locally (Test Mode)

```bash
# Test the Lambda handler locally
python lambda/payment_handler.py
```

## 📁 Project Structure

```
payment-smart-bot/
├── README.md                    # This file
├── lambda/
│   ├── payment_handler.py      # Main Lambda orchestrator
│   ├── bedrock_client.py       # Bedrock API wrapper
│   ├── validation.py           # Card validation (Luhn, etc.)
│   └── requirements.txt        # Python dependencies
├── tests/
│   ├── mock_data.json          # Test payment records
│   ├── conversation_flows.json # Sample dialogues
│   └── test_handler.py         # Unit tests
├── docs/
│   ├── ARCHITECTURE.md         # Detailed design
│   ├── SECURITY.md             # PCI-DSS compliance notes
│   ├── COST_ANALYSIS.md        # Pricing details
│   └── architecture.png        # Diagram (placeholder)
├── template.yaml               # AWS SAM template
└── .env.example                # Environment variables template
```

## 🔒 Security

### PCI-DSS Compliance:
- ✅ **No storage**: Sensitive data processed transiently in Lambda memory
- ✅ **Tokenization**: Stripe handles actual card details
- ✅ **Encryption**: HTTPS in transit, KMS for DynamoDB at rest
- ✅ **Masking**: CloudWatch logs never contain full card numbers
- ✅ **IAM**: Least-privilege roles for all services
- ✅ **Guardrails**: Bedrock filters to prevent PII leaks in prompts

### Best Practices:
- Enable AWS X-Ray for tracing (without sensitive data)
- Rotate Stripe API keys regularly
- Use VPC endpoints for Lambda-to-Bedrock (optional for extra isolation)
- Implement rate limiting on API Gateway

## 🧪 Testing

### Mock Data Included:
- **5 test credit cards** (Visa, Mastercard, Amex, Discover—all safe test numbers)
- **4 conversation flows** (success, validation error, edge case, abort)
- **Luhn validation tests**

### Run Tests:

```bash
cd tests
python test_handler.py

# Expected output:
# ✅ Test 1: Successful collection (Llama 3.2 1B)
# ✅ Test 2: Invalid card detected (Luhn fail)
# ✅ Test 3: Multi-turn context maintained
# ✅ Test 4: Stripe tokenization works
```

### Load Testing:
```bash
# Simulate 100 customers
python tests/load_test.py --customers 100
# Estimated cost: $0.05
```

## 🚢 Deployment

### Using AWS SAM:

```bash
# Build
sam build

# Deploy to AWS
sam deploy --guided
# Follow prompts:
# - Stack name: payment-smart-bot
# - Region: us-east-1
# - Confirm IAM role creation: Y

# Test in cloud
curl -X POST https://<api-id>.execute-api.us-east-1.amazonaws.com/prod/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "I want to pay", "sessionId": "test-123"}'
```

### CI/CD (Optional):
- Use GitHub Actions or AWS CodePipeline
- Run tests on PR, deploy on merge to `main`

## 📊 Monitoring

### Key Metrics (CloudWatch):
- Lambda invocations, errors, duration
- Bedrock token usage, latency
- DynamoDB read/write capacity
- API Gateway 4xx/5xx errors

### Alerts:
- Set up SNS notifications for Lambda errors or high Bedrock costs

## 🛠️ Development Roadmap

- [x] Project setup
- [ ] Lambda handler with Bedrock integration
- [ ] Luhn validation + regex checks
- [ ] DynamoDB session management
- [ ] Stripe tokenization
- [ ] Streamlit frontend
- [ ] Bedrock Guardrails integration
- [ ] Unit tests + load tests
- [ ] SAM deployment template
- [ ] Production deployment
- [ ] Prompt caching optimization

## 📚 Resources

- [Amazon Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/)
- [Meta Llama 3.2 Model Card](https://huggingface.co/meta-llama/Llama-3.2-1B-Instruct)
- [Stripe Test Cards](https://stripe.com/docs/testing)
- [PCI-DSS Compliance Guide](https://www.pcisecuritystandards.org/)
- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)

## 🤝 Contributing

This is a learning project. Feel free to fork, experiment, and share improvements!

## 👨‍💻 Author

**Alamin Juma**
- GitHub: [@Alamin-Juma](https://github.com/Alamin-Juma)
- Project: Part of AI-SmartBot-Boto3-PY-Bedrock-LangChain

## 📝 License

Open for educational purposes. Payment processing uses Stripe—follow their terms of service.

---

**⚠️ Important**: This is a development/learning project. For production payment systems, undergo a full PCI-DSS audit and use certified payment processors.

**Built with ❤️ using AWS Bedrock, Lambda, and Meta Llama 3.2**
