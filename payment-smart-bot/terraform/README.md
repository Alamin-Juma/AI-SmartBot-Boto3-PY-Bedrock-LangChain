# Terraform Infrastructure Setup ✅

Complete Infrastructure-as-Code for Payment Smart Bot using Terraform.

## 🎯 What Terraform Manages

### Core Resources
- ✅ **Lambda Function** - Payment handler with automatic code packaging
- ✅ **API Gateway** - REST API with CORS, throttling, and logging
- ✅ **DynamoDB** - Session storage with TTL and encryption
- ✅ **Secrets Manager** - Secure Stripe API key storage
- ✅ **KMS** - Encryption keys for DynamoDB and Secrets
- ✅ **IAM** - Roles and policies (least-privilege)
- ✅ **CloudWatch** - Log groups, alarms, and metrics

### Security Features
- 🔒 Encryption at rest (KMS)
- 🔒 Encryption in transit (HTTPS/TLS)
- 🔒 Secrets rotation support
- 🔒 IAM least-privilege policies
- 🔒 Optional X-Ray tracing
- 🔒 API rate limiting

## 📂 File Structure

```
terraform/
├── main.tf                    # Provider and backend config
├── variables.tf               # Input variables
├── outputs.tf                 # Output values
├── lambda.tf                  # Lambda function + CloudWatch
├── api_gateway.tf             # API Gateway + CORS + throttling
├── dynamodb.tf                # DynamoDB + KMS + Secrets Manager
├── iam.tf                     # IAM roles and policies
├── terraform.tfvars.example   # Example configuration
└── .gitignore                 # Ignore secrets and state files
```

## 🚀 Quick Start

```bash
# 1. Navigate to terraform directory
cd payment-smart-bot/terraform

# 2. Copy and configure variables
cp terraform.tfvars.example terraform.tfvars
nano terraform.tfvars  # Add your Stripe key

# 3. Initialize Terraform
terraform init

# 4. Preview changes
terraform plan

# 5. Deploy infrastructure
terraform apply

# 6. Test the API
curl -X POST $(terraform output -raw api_endpoint) \
  -H "Content-Type: application/json" \
  -d '{"sessionId": "test-001", "message": "I want to pay"}'
```

## 📝 Required Configuration

Edit `terraform.tfvars`:

```hcl
# REQUIRED
stripe_secret_key = "sk_test_YOUR_KEY_HERE"  # From Stripe Dashboard

# OPTIONAL (has defaults)
aws_region              = "us-east-1"
environment             = "dev"
lambda_memory_size      = 512
lambda_timeout          = 30
api_throttle_rate       = 10
enable_xray_tracing     = true
enable_bedrock_guardrails = false
```

## 💰 Cost Estimates

### Development (Low Volume)
- **Free Tier Eligible**: Lambda, DynamoDB, API Gateway
- **Bedrock**: ~$0.50 per 1,000 customers
- **Fixed Costs**: ~$1.45/month (Secrets Manager + KMS)
- **Total**: ~$2/month for testing

### Production (10K customers/month)
- **Bedrock**: $5
- **Lambda**: $1
- **DynamoDB**: $0.30
- **API Gateway**: $0.40
- **Fixed**: $1.45
- **Total**: ~$8.15/month

## 🔄 Common Operations

### Update Lambda Code
```bash
# Modify lambda/payment_handler.py
# Then run:
terraform apply
```

### Rotate Stripe Key
```bash
aws secretsmanager update-secret \
  --secret-id payment-smart-bot/stripe-key-dev \
  --secret-string '{"STRIPE_SECRET_KEY":"sk_test_NEW_KEY"}'
```

### View Logs
```bash
aws logs tail /aws/lambda/payment-smart-bot-handler-dev --follow
```

### Scale Up
```hcl
# In terraform.tfvars
lambda_memory_size = 1024
api_throttle_rate  = 100
```

### Destroy Everything
```bash
terraform destroy
```

## 🛡️ Security Best Practices

1. **Never commit terraform.tfvars** - It contains secrets
2. **Use S3 backend** for team collaboration (state locking)
3. **Enable MFA** for AWS account
4. **Rotate keys** regularly via Secrets Manager
5. **Review IAM policies** periodically
6. **Enable CloudTrail** for audit logs
7. **Use API keys** in production (currently disabled)

## 📊 Monitoring

### Built-in Alarms
- Lambda errors >5 in 5 minutes
- Lambda duration >25 seconds (near timeout)

### Custom Metrics
```bash
# Bedrock token usage
aws cloudwatch get-metric-statistics \
  --namespace AWS/Bedrock \
  --metric-name InputTokenCount \
  --dimensions Name=ModelId,Value=meta.llama3-2-1b-instruct-v1:0 \
  --statistics Sum \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600
```

## 🔧 Troubleshooting

### Issue: "Resource already exists"
```bash
# Import existing resource
terraform import aws_dynamodb_table.sessions payment-smart-bot-sessions-dev
```

### Issue: State lock
```bash
terraform force-unlock <LOCK_ID>
```

### Issue: API returns 502
```bash
# Check Lambda logs
aws logs tail /aws/lambda/payment-smart-bot-handler-dev --since 1h
```

## 🚀 Advanced: Multi-Environment

```bash
# Development
terraform workspace new dev
terraform apply -var-file="dev.tfvars"

# Staging
terraform workspace new staging
terraform apply -var-file="staging.tfvars"

# Production
terraform workspace new prod
terraform apply -var-file="prod.tfvars"
```

## 📖 Documentation

- [Deployment Guide](../docs/TERRAFORM_DEPLOYMENT.md) - Detailed step-by-step
- [Architecture](../docs/ARCHITECTURE.md) - System design
- [Main README](../README.md) - Project overview

## 🤝 Contributing

When adding new resources:
1. Add variables in `variables.tf`
2. Create resource in appropriate `.tf` file
3. Add outputs in `outputs.tf`
4. Update `.tfvars.example`
5. Document in this README

## 📞 Support

- Terraform Docs: https://registry.terraform.io/providers/hashicorp/aws/latest/docs
- AWS Support: https://console.aws.amazon.com/support/
- GitHub Issues: Open an issue in the repo

---

**Managed by**: Terraform >= 1.5.0  
**AWS Provider**: ~> 5.0  
**Last Updated**: October 2025
