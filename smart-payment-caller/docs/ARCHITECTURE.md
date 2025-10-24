# Architecture: PCI-Compliant IVR Payment Bot

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      PCI DSS SAQ A-EP Compliant Architecture                │
│                                                                               │
│  ┌──────────┐                                                                │
│  │  Caller  │ Voice Call                                                     │
│  │  (Phone) │─────────────┐                                                  │
│  └──────────┘             │                                                  │
│                           ▼                                                  │
│              ┌─────────────────────────┐                                     │
│              │   Amazon Connect        │                                     │
│              │  (PCI-Compliant Gateway)│                                     │
│              ├─────────────────────────┤                                     │
│              │ • Real-time Audio       │                                     │
│              │ • Speech-to-Text (STT)  │                                     │
│              │ • DTMF Capture          │                                     │
│              │ • Text-to-Speech (Polly)│                                     │
│              └────────┬────────────────┘                                     │
│                       │                                                      │
│                       │ TLS/HTTPS                                            │
│                       │ Encrypted Call Data                                  │
│                       ▼                                                      │
│              ┌─────────────────────────┐                                     │
│              │    AWS Lambda           │                                     │
│              │  (Orchestrator + Mask)  │◄──────┐                            │
│              ├─────────────────────────┤       │                            │
│              │ 1. Mask CHD Immediately │       │ IAM Auth                   │
│              │ 2. Store Masked → S3    │       │ Throttling                 │
│              │ 3. Tokenize → Stripe    │       │                            │
│              │ 4. AI Prompt (Safe)     │       │                            │
│              └────┬────┬───────┬───────┘       │                            │
│                   │    │       │               │                            │
│         ┌─────────┘    │       └───────────┐   │                            │
│         │              │                   │   │                            │
│         ▼              ▼                   ▼   │                            │
│  ┌─────────────┐ ┌──────────────┐  ┌──────────────┐                        │
│              │   Amazon     │  │   Amazon S3  │                        │
│  │   Gateway   │ │   Bedrock    │  │ (Audit Logs) │                        │
│  ├─────────────┤ ├──────────────┤  ├──────────────┤                        │
│  │ Tokenize    │ │ Custom       │  │ KMS Encrypted│                        │
│  │ Validate    │ │ Inference    │  │ Versioned    │                        │
│  │ Charge      │ │ Profile      │  │ 7yr Retention│                        │
│  │             │ │ (Isolated)   │  │              │                        │
│  │             │ │ Mistral 7B   │  │              │                        │
│  │             │ │ (No CHD!)    │  │              │                        │
│  └─────────────┘ └──────────────┘  └──────────────┘                        │
│         │              │                   │                                │
│         │              │                   │                                │
│         │              └───────────────────┼──► No CHD Data                 │
│         │                                  │                                │
│         └──► Payment Token (tok_xxx)       │                                │
│              Removes CHD from Scope        │                                │
│                                            │                                │
│                                            ▼                                │
│                                   ┌─────────────────┐                       │
│                                   │  AWS KMS Key    │                       │
│                                   │  (Encryption)   │                       │
│                                   └─────────────────┘                       │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow: CHD Masking Process

### 🔐 Key Compliance Step: CHD NEVER Reaches AI

```
Caller Says:                Lambda Receives:            Lambda Sends to Bedrock:
"My card is              →  {                        →  {
 4111 1111 1111 1111"        "cardNumber":               "userInput":
                              "4111111111111111"           "Customer provided Visa
                            }                              card ending in ****1111"
                                                        }
                            ↓
                            IMMEDIATE MASKING
                            ↓
                            {
                              "cardNumber_masked":
                                "************1111",
                              "cardNumber_hash":
                                "sha256:a3f7d..."
                            }
                            ↓
                            Store in S3 (Encrypted)
                            ↓
                            Send to Stripe for Tokenization
                            ↓
                            {
                              "stripe_token": "tok_1A2B3C",
                              "last4": "1111",
                              "brand": "visa"
                            }
```

---

## Security Layers

### Layer 1: Network (TLS Everywhere)
```
Caller ──[TLS 1.2+]──> Connect ──[HTTPS]──> Lambda ──[HTTPS]──> Stripe/Bedrock
```

### Layer 2: Data Masking (Immediate)
```python
# In Lambda (before ANY processing)
def mask_card_number(card: str) -> str:
    return "*" * (len(card) - 4) + card[-4:]

# Example:
mask_card_number("4111111111111111")  # → "************1111"
```

### Layer 3: Encryption at Rest
```
S3 Audit Logs:
├── ServerSideEncryption: AES-256 (KMS)
├── BucketVersioning: Enabled
├── PublicAccess: Blocked
└── Retention: 7 years (PCI requirement)
```

### Layer 4: IAM Least Privilege
```yaml
Lambda IAM Policy:
  - bedrock:InvokeModel     # Only Mistral model
  - s3:PutObject            # Only audit bucket
  - kms:Decrypt             # Only audit KMS key
  - ssm:GetParameter        # Only Stripe secret
```

---

## Call Flow Sequence

### Successful Payment Flow

```
1. [Caller]
   ↓ Dials Connect number
   
2. [Connect: Welcome Message]
   → "Welcome to secure payment system..."
   ↓
   
3. [Connect: Capture Card Number]
   → "Please enter 16-digit card number"
   ← Caller enters: 4242424242424242#
   ↓
   
4. [Connect: Capture Expiry]
   → "Enter expiration as MMYY"
   ← Caller enters: 1225#
   ↓
   
5. [Connect: Capture CVV]
   → "Enter 3-digit security code"
   ← Caller enters: 123#
   ↓
   
6. [Connect → Lambda]
   Payload: {
     "cardNumber": "4242424242424242",
     "expiryMonth": "12",
     "expiryYear": "25",
     "cvv": "123"
   }
   ↓
   
7. [Lambda: MASK CHD]
   masked_card = "************4242"
   ↓
   
8. [Lambda → S3: Store Audit]
   s3://audit/2025/10/23/session-xxx.json
   {
     "cardNumber": "************4242",
     "timestamp": "2025-10-23T10:30:00Z",
     "pci_compliant": true
   }
   ↓
   
9. [Lambda → Stripe: Tokenize]
   POST /v1/tokens
   Response: {
     "id": "tok_1A2B3C",
     "card": {
       "brand": "visa",
       "last4": "4242"
     }
   }
   ↓
   
10. [Lambda → Bedrock: AI Response]
    Prompt: "Customer validated Visa ending 4242. Confirm payment."
    Response: "Thank you! Your Visa card has been validated..."
    ↓
    
11. [Lambda → Connect]
    {
      "response": "Thank you! Your payment is confirmed.",
      "stripeToken": "tok_1A2B3C"
    }
    ↓
    
12. [Connect → Polly: Speak]
    → "Thank you! Your payment has been processed successfully."
    ↓
    
13. [Caller]
    ← Hears confirmation
    → Call ends
```

---

## Component Responsibilities

### Amazon Connect
**Role**: Voice gateway and DTMF capture  
**Handles**:
- Call routing
- DTMF digit collection (card number, expiry, CVV)
- Text-to-speech (Polly)
- Lambda invocation

**Does NOT Handle**:
- CHD storage
- Payment processing
- AI inference

### AWS Lambda
**Role**: Orchestrator and compliance enforcer  
**Handles**:
- **IMMEDIATE CHD masking** (before any other processing)
- S3 audit log creation
- Stripe tokenization
- Bedrock AI invocation (with SAFE prompts only)
- Response generation

**CRITICAL**: This is the PCI compliance boundary.

### Amazon Bedrock (Custom Inference Profile - Mistral 7B)
**Role**: Conversational AI (NO CHD ACCESS)  
**Model Type**: Cross-Region Inference Profile (Isolated Compute)

**Handles**:
- Natural language response generation
- Intent understanding (from masked data)
- Friendly confirmation messages

**PCI Level 1 Compliance**:
- ✅ Dedicated inference endpoint (not shared)
- ✅ No cross-account data access
- ✅ Isolated compute resources
- ✅ QSA-approvable architecture

**NEVER Receives**:
- Full card numbers
- CVV codes
- Unmasked expiry dates

### Stripe
**Role**: Payment tokenization  
**Handles**:
- Card validation
- Token generation (removes CHD from scope)
- Fraud detection

**PCI Benefit**: Once tokenized, CHD is Stripe's responsibility.

### Amazon S3 + KMS
**Role**: Encrypted audit trail  
**Handles**:
- Immutable transaction logs (masked)
- 7-year retention (PCI requirement)
- Versioning and lifecycle policies

---

## PCI DSS Scope Reduction

### Traditional Architecture (In-Scope)
```
┌─────────────────────────────────────┐
│  YOUR ENTIRE ENVIRONMENT IN SCOPE   │
│  ✗ Servers store CHD                │
│  ✗ Databases contain CHD            │
│  ✗ Logs may leak CHD                │
│  ✗ AI models see CHD                │
│  ✗ Annual QSA audit required        │
└─────────────────────────────────────┘
```

### This Architecture (Out-of-Scope)
```
┌──────────────────────────────────────┐
│  MINIMAL SCOPE (SAQ A-EP)            │
│  ✓ CHD masked immediately            │
│  ✓ AI never sees CHD                 │
│  ✓ Stripe handles tokenization       │
│  ✓ Only Lambda touches raw CHD       │
│  ✓ Self-assessment questionnaire     │
└──────────────────────────────────────┘
```

---

## Cost Breakdown (Monthly)

### POC Phase (30 test calls)
```
Service                  Usage                       Cost
───────────────────────────────────────────────────────────
Amazon Connect           30 calls × 3 min × $0.018   $1.62
Lambda                   30 × 512MB × 5s              Free
Bedrock (Custom Profile) 30 × 150 tokens × $0.00026   $1.17
S3 Storage               30 logs × 5KB                $0.01
KMS                      1 key                        $1.00
CloudWatch               1GB logs                     Free
SSM Parameter            1 SecureString               Free
───────────────────────────────────────────────────────────
TOTAL                                                 $3.80
```

### Production (1000 calls/month)
```
Service                  Usage                       Cost
───────────────────────────────────────────────────────────
Amazon Connect           1000 × 3 min × $0.018       $54.00
Lambda                   1000 × 512MB × 5s            $0.42
Bedrock (Custom Profile) 1000 × 150 tokens × $0.00026 $39.00
S3 Storage               1000 logs × 5KB              $0.03
KMS                      1 key                        $1.00
CloudWatch               5GB logs                     $0.50
WAF (optional)           1M requests                  $5.00
───────────────────────────────────────────────────────────
TOTAL                                                $99.95
```

**Note**: Custom Inference Profile pricing is ~1.7x foundation model pricing but provides
PCI Level 1 compliant isolation. Foundation model: $0.00015/token vs Custom: $0.00026/token.

---

## Compliance Evidence Package

### For QSA Audit (When Ready)

1. **Network Diagram**: This document
2. **Data Flow Diagram**: Above sections
3. **IAM Policies**: Exported from AWS Console
4. **Encryption Proof**: KMS key policies + S3 settings
5. **Audit Logs**: Sample S3 objects (masked)
6. **Penetration Test**: Third-party security scan
7. **Incident Response Plan**: (To be created)
8. **Staff Training Records**: (To be created)

---

## Scaling Considerations

### Current Design (Up to 100 concurrent calls)
```
Lambda Concurrency:  Reserved = 10
Bedrock Throughput:  On-demand (no limits)
Connect:             No limits
Stripe:              100 requests/second (test mode)
```

### For > 100 concurrent calls
```
1. Increase Lambda reserved concurrency
2. Request Bedrock provisioned throughput
3. Upgrade Stripe to production mode
4. Add CloudFront for Connect assets
5. Enable AWS WAF rate limiting
```

---

## Disaster Recovery

### Backup Strategy
```
Component          Backup Method              RPO      RTO
──────────────────────────────────────────────────────────
Lambda Code        SAM template (Git)         0 min    5 min
S3 Audit Logs      Cross-region replication   <1 min   1 min
Connect Flows      Manual export (JSON)       24 hrs   30 min
Stripe Config      Stripe backup              24 hrs   10 min
IAM Policies       Terraform state            0 min    5 min
```

### Failover Plan
```
1. Primary region fails → Lambda auto-retries (3x)
2. If still failing → Connect routes to backup queue
3. Manual intervention: Deploy to secondary region (us-west-2)
4. Update DNS/Connect routing
5. Verify Stripe API in secondary region
```

---

## Security Hardening Roadmap

### Phase 1: POC (Current)
- [x] CHD masking
- [x] Encrypted S3
- [x] IAM least privilege
- [x] Secrets Manager for API keys

### Phase 2: Production
- [ ] VPC with private subnets
- [ ] VPC endpoints (no internet egress)
- [ ] AWS WAF with rate limiting
- [ ] GuardDuty threat detection
- [ ] CloudTrail event logging

### Phase 3: Certification
- [ ] Third-party penetration test
- [ ] QSA validation
- [ ] SOC 2 Type II audit
- [ ] Annual compliance review

---

## Monitoring & Alerting

### CloudWatch Alarms
```
Alarm                      Threshold    Action
────────────────────────────────────────────────
Lambda Errors             > 1/minute    SNS alert
Lambda Duration           > 25 seconds  SNS alert
Bedrock Throttles         > 5/hour      Scale up
S3 PutObject Failures     > 0           SNS alert
Stripe API Errors         > 2%          Page oncall
Connect Call Failures     > 5%          Page oncall
```

### Dashboards
1. **Real-time Call Volume**: Connect metrics
2. **Lambda Performance**: Duration, errors, concurrency
3. **Bedrock Usage**: Token consumption, throttles
4. **Stripe Success Rate**: Token creation, validation
5. **PCI Compliance**: CHD masking rate, audit log count

---

## API Reference

### Lambda Event Structure (From Connect)
```json
{
  "Details": {
    "ContactData": {
      "ContactId": "string",
      "CustomerEndpoint": {
        "Address": "string",
        "Type": "TELEPHONE_NUMBER"
      },
      "Channel": "VOICE"
    },
    "Parameters": {
      "cardNumber": "string",
      "expiryMonth": "string",
      "expiryYear": "string",
      "cvv": "string",
      "intentType": "validate_payment",
      "userInput": "string"
    }
  }
}
```

### Lambda Response Structure (To Connect)
```json
{
  "statusCode": 200,
  "response": "string (Text-to-speech content)",
  "sessionId": "string (hashed)",
  "stripeToken": "string (tok_xxx)",
  "cardBrand": "string (visa|mastercard|amex)",
  "last4": "string (4 digits)",
  "metadata": {
    "timestamp": "ISO 8601",
    "pci_compliant": true,
    "chd_masked": true
  }
}
```

---

## References

- [PCI DSS v4.0 Standard](https://www.pcisecuritystandards.org/document_library)
- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Amazon Connect Developer Guide](https://docs.aws.amazon.com/connect/)
- [Stripe API Reference](https://stripe.com/docs/api)
- [AWS Security Best Practices](https://aws.amazon.com/security/best-practices/)
