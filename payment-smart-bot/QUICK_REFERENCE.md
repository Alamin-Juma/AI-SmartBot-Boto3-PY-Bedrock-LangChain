# 🚀 Payment Smart Bot - Quick Reference Card

## ⚡ Quick Commands

### Backend
```bash
# Deploy
cd terraform && python build_lambda.py && terraform apply -auto-approve

# Test API
curl -X POST 'YOUR_API_ENDPOINT/chat' \
  -H 'Content-Type: application/json' \
  -d '{"sessionId":"test-001","message":"I want to make a payment"}'
```

### Frontend
```bash
# Run locally
cd frontend && ./start.sh  # or ./start.ps1 on Windows

# Docker
docker-compose up -d

# Manual
pip install -r requirements.txt && streamlit run payment_bot_frontend.py
```

---

## 📁 Project Structure

```
payment-smart-bot/
├── lambda/
│   └── payment_handler.py          ← Main Lambda function
├── terraform/
│   ├── build_lambda.py             ← Package dependencies
│   ├── main.tf                     ← Infrastructure
│   ├── iam.tf                      ← IAM policies
│   └── terraform.tfvars            ← Your config (gitignored)
├── frontend/                       ← NEW! Streamlit UI
│   ├── payment_bot_frontend.py     ← Main frontend app
│   ├── requirements.txt            ← Dependencies
│   ├── start.sh / start.ps1        ← Quick start
│   ├── Dockerfile                  ← Docker image
│   └── docker-compose.yml          ← Docker Compose
├── docs/
│   ├── QUICK_START.md              ← 5-min deployment
│   ├── DEPLOYMENT_GUIDE.md         ← Full guide
│   ├── FRONTEND_GUIDE.md           ← UI screenshots
│   ├── FRONTEND_IMPLEMENTATION.md  ← Frontend summary
│   └── TROUBLESHOOTING.md          ← Error fixes
└── README.md                       ← Project overview
```

---

## 🔗 Important URLs

| Resource | URL |
|----------|-----|
| **API Endpoint** | `https://osmgkvun82.execute-api.us-east-1.amazonaws.com/dev/chat` |
| **Frontend (local)** | `http://localhost:8501` |
| **GitHub Repo** | `github.com/Alamin-Juma/AI-SmartBot-Boto3-PY-Bedrock-LangChain` |
| **Stripe Dashboard** | `https://dashboard.stripe.com/test/payments` |

---

## 🧪 Test Cards

```
Visa Success:     4242 4242 4242 4242
Mastercard:       5555 5555 5555 4444
Amex:             3782 822463 10005
Declined Card:    4000 0000 0000 0002

Expiry: Any future date (e.g., 12/25)
CVV:    Any 3 digits (e.g., 123)
Name:   Any name
```

---

## 📊 Key Metrics

| Metric | Value |
|--------|-------|
| **Cost per request** | ~$0.0005 |
| **Lambda timeout** | 60 seconds |
| **Lambda memory** | 512 MB |
| **Package size** | 20.14 MB |
| **Model** | Meta Llama 3.2 1B Instruct |
| **Session TTL** | 1 hour |

---

## 🔐 Configuration

### Environment Variables (Backend)
```bash
# terraform/terraform.tfvars
stripe_api_key = "sk_test_YOUR_KEY_HERE"
bedrock_model_id = "us.meta.llama3-2-1b-instruct-v1:0"
```

### Environment Variables (Frontend)
```bash
# frontend/.env
PAYMENT_BOT_API_ENDPOINT=https://your-api-endpoint.com/dev/chat
```

---

## 🛠️ Common Tasks

### View Lambda Logs
```bash
aws logs tail /aws/lambda/payment-smart-bot-handler-dev --follow
```

### Redeploy Lambda Only
```bash
cd terraform
python build_lambda.py
terraform apply -auto-approve -target=aws_lambda_function.payment_handler
```

### Test Full Payment Flow
```bash
cd scripts
./test_payment_flow.sh  # or .ps1 on Windows
```

### Update Frontend
```bash
cd frontend
git pull
pip install -r requirements.txt --upgrade
streamlit run payment_bot_frontend.py
```

---

## 🐛 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| **500 Error** | Check CloudWatch logs for Lambda errors |
| **No module 'stripe'** | Run `python build_lambda.py` again |
| **Bedrock AccessDenied** | Check IAM permissions in `iam.tf` |
| **Frontend won't start** | Install deps: `pip install -r requirements.txt` |
| **API endpoint error** | Configure in frontend sidebar or `.env` |

---

## 📖 Documentation Quick Links

| Guide | When to Use |
|-------|-------------|
| **[QUICK_START.md](QUICK_START.md)** | Deploy in 5 minutes |
| **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** | Detailed deployment |
| **[Frontend README](../frontend/README.md)** | Frontend setup |
| **[FRONTEND_GUIDE.md](FRONTEND_GUIDE.md)** | UI walkthrough |
| **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** | Fix errors |

---

## 🎯 Deployment Checklist

### Backend
- [ ] AWS credentials configured
- [ ] Stripe test key obtained
- [ ] `terraform.tfvars` created
- [ ] Lambda package built (`build_lambda.py`)
- [ ] Infrastructure deployed (`terraform apply`)
- [ ] API endpoint tested

### Frontend
- [ ] Dependencies installed
- [ ] `.env` configured with API endpoint
- [ ] Test mode verified
- [ ] Full payment flow tested
- [ ] Production deployment (optional)

---

## 🚀 Next Steps

### Immediate
1. **Test locally**: Run frontend with test cards
2. **Review logs**: Check CloudWatch for any errors
3. **Monitor costs**: Check AWS Cost Explorer

### Short-term
1. **Add monitoring**: Set up CloudWatch alarms
2. **Production Stripe**: Switch to live keys
3. **Custom domain**: Add custom domain to API Gateway

### Long-term
1. **Stripe Elements**: Integrate for PCI compliance
2. **Multi-currency**: Support international payments
3. **Analytics**: Add tracking and insights
4. **Load testing**: Validate production scalability

---

## 💡 Tips & Best Practices

### Backend
- ✅ Always test with test cards first
- ✅ Monitor CloudWatch logs regularly
- ✅ Use inference profiles for Bedrock (not direct model IDs)
- ✅ Keep Lambda package under 50 MB
- ✅ Set appropriate Lambda timeout (60s)

### Frontend
- ✅ Use test mode for development
- ✅ Configure API endpoint in `.env`
- ✅ Clear browser cache if UI not updating
- ✅ Check browser console for errors
- ✅ Use HTTPS for production

### Security
- ✅ Never commit API keys
- ✅ Use AWS Secrets Manager for sensitive data
- ✅ Enable CloudWatch logging
- ✅ Review IAM policies regularly
- ✅ Rotate API keys periodically

---

## 📞 Support

| Issue Type | Resource |
|------------|----------|
| **Deployment errors** | [TROUBLESHOOTING.md](TROUBLESHOOTING.md) |
| **API errors** | CloudWatch Logs + [TROUBLESHOOTING.md](TROUBLESHOOTING.md) |
| **Frontend issues** | [Frontend README](../frontend/README.md) |
| **General questions** | [GitHub Issues](https://github.com/Alamin-Juma/AI-SmartBot-Boto3-PY-Bedrock-LangChain/issues) |

---

## 📊 Status Dashboard

### Current State
✅ Backend deployed (30 AWS resources)  
✅ Lambda function operational (20.14 MB)  
✅ API Gateway live  
✅ DynamoDB sessions table active  
✅ Bedrock inference profile configured  
✅ Stripe integration working  
✅ Frontend implemented (Streamlit)  
✅ Docker deployment ready  
✅ Documentation complete  

### Next Deployment
⏳ Frontend to production (optional)  
⏳ Custom domain setup (optional)  
⏳ Monitoring alerts (recommended)  

---

**Last Updated:** 2025-01-15  
**Version:** 1.0.0  
**Status:** ✅ Production Ready
