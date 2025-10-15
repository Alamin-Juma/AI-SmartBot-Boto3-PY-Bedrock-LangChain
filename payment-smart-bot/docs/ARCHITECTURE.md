# Payment Smart Bot - Architecture Overview

## System Design

### High-Level Architecture

```
┌─────────────┐
│   User/UI   │
│  (Browser)  │
└──────┬──────┘
       │ HTTPS
       ▼
┌─────────────────────┐
│   API Gateway       │
│  (REST API)         │
└──────┬──────────────┘
       │
       ▼
┌────────────────────────────────────────┐
│         AWS Lambda Function            │
│  (Python 3.11 - payment_handler.py)   │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │  1. Session Management           │ │
│  │     - Get/Create session         │ │
│  │     - Load conversation history  │ │
│  └──────────────────────────────────┘ │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │  2. Input Processing             │ │
│  │     - Extract payment data       │ │
│  │     - Validate formats           │ │
│  └──────────────────────────────────┘ │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │  3. AI Invocation                │ │
│  │     - Build prompt               │ │
│  │     - Call Bedrock API           │ │
│  └──────────────────────────────────┘ │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │  4. Validation                   │ │
│  │     - Luhn algorithm (card)      │ │
│  │     - Date validation (expiry)   │ │
│  │     - Format checks (CVV)        │ │
│  └──────────────────────────────────┘ │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │  5. Payment Processing           │ │
│  │     - Stripe tokenization        │ │
│  │     - (Optional) charge API      │ │
│  └──────────────────────────────────┘ │
└────────┬─────────────┬────────────────┘
         │             │
         ▼             ▼
┌─────────────┐   ┌──────────────┐
│  DynamoDB   │   │   Bedrock    │
│  (Sessions) │   │  Llama 3.2   │
└─────────────┘   └──────────────┘
         │
         ▼
┌─────────────────┐
│  Stripe API     │
│  (Tokenize)     │
└─────────────────┘
```

## Component Details

### 1. API Gateway
- **Type**: REST API with HTTP endpoints
- **Endpoints**:
  - `POST /chat` - Main conversation endpoint
  - `GET /session/{id}` - Retrieve session status
  - `DELETE /session/{id}` - Cancel/delete session
- **Security**:
  - API key authentication (optional)
  - Rate limiting: 10 req/sec per IP
  - CORS enabled for web clients
- **Integration**: Lambda proxy integration

### 2. Lambda Function (Orchestrator)
- **Runtime**: Python 3.11
- **Memory**: 512 MB (adjust based on load)
- **Timeout**: 30 seconds
- **Concurrency**: Reserved 10 (or auto-scale)
- **Environment Variables**:
  - `BEDROCK_MODEL_ID`: Model identifier
  - `DYNAMODB_TABLE`: Session table name
  - `STRIPE_SECRET_KEY`: Stripe API key
  - `AWS_REGION`: us-east-1

#### Key Functions:
1. **`lambda_handler`**: Main entry point
2. **`invoke_bedrock`**: Call AI model
3. **`luhn_checksum`**: Card validation
4. **`validate_expiry`**: Date checks
5. **`validate_cvv`**: CVV format
6. **`extract_payment_info`**: Parse user input
7. **`get_session`/`save_session`**: DynamoDB ops

### 3. Amazon Bedrock
- **Model**: Meta Llama 3.2 1B Instruct (`meta.llama3-2-1b-instruct-v1:0`)
- **API**: Converse API (new, supports multi-turn)
- **Configuration**:
  - Temperature: 0.5 (deterministic for payment tasks)
  - Max Tokens: 512 (sufficient for responses)
  - Top P: 0.9
- **System Prompt**: Embedded in Lambda (see `SYSTEM_PROMPT`)
- **Context Window**: Up to 128K tokens (not needed for payment flows)

#### Pricing (Llama 3.2 1B):
- Input: $0.0001 per 1,000 tokens
- Output: $0.0001 per 1,000 tokens
- Batch (50% off): $0.00005/1k tokens
- Provisioned: ~$13/hour per model unit

### 4. DynamoDB
- **Table Name**: `payment-bot-sessions`
- **Primary Key**: `sessionId` (String)
- **Attributes**:
  ```json
  {
    "sessionId": "uuid-v4",
    "conversationHistory": [
      {"role": "user|assistant", "text": "..."}
    ],
    "collectedData": {
      "name": "...",
      "card": "...",  // Stored temporarily
      "expiry": "...",
      "cvv": "..."
    },
    "currentStep": "name|card|expiry|cvv|confirm",
    "status": "collecting|awaiting_confirmation|complete|cancelled",
    "lastUpdated": "ISO-8601 timestamp"
  }
  ```
- **TTL**: 1 hour (auto-delete old sessions)
- **Capacity**: On-Demand (pay-per-request)
- **Encryption**: KMS at rest

**Important**: Sensitive data (card, CVV) are only stored transiently during collection and purged after tokenization. Never log full values.

### 5. Stripe Integration
- **SDK**: `stripe` Python library
- **Operations**:
  - `PaymentMethod.create()`: Tokenize card
  - `PaymentIntent.create()`: Process charge (optional)
- **Test Mode**: Use `sk_test_...` keys in development
- **Security**: Lambda environment variables (encrypted with KMS)

### 6. CloudWatch Logging
- **Log Group**: `/aws/lambda/payment-smart-bot`
- **Retention**: 7 days (or custom)
- **Masking**: All card numbers logged as `****XXXX`
- **Metrics**:
  - Invocation count
  - Error rate
  - Duration (p50, p99)
  - Bedrock latency

### 7. X-Ray Tracing (Optional)
- Trace Lambda → Bedrock → DynamoDB flow
- Identify bottlenecks
- No sensitive data in traces

## Data Flow

### Happy Path (Successful Payment Collection):
1. User sends: `"I want to pay"`
2. API Gateway → Lambda
3. Lambda creates session in DynamoDB
4. Lambda calls Bedrock with system prompt + user message
5. Bedrock returns: `"Sure! What's the name on your card?"`
6. Lambda stores conversation in session, returns response
7. User sends: `"John Doe"`
8. Lambda extracts name, updates session (`currentStep: "card"`)
9. Lambda calls Bedrock with updated history
10. Bedrock: `"Thanks John. Card number?"`
11. User sends: `"4111111111111111"`
12. Lambda validates with Luhn → Pass
13. Updates session (`currentStep: "expiry"`)
14. Bedrock: `"Expiry date (MM/YY)?"`
15. User: `"12/2028"` → Validates → Pass
16. Bedrock: `"CVV?"`
17. User: `"123"` → Validates → Pass
18. Lambda shows confirmation (masked data)
19. User: `"confirm"`
20. Lambda calls Stripe API → Tokenize
21. Return success + payment method ID
22. DynamoDB session marked `complete`
23. Session auto-deleted after 1 hour (TTL)

### Error Handling:
- **Invalid Card**: Luhn fails → Lambda: `"Invalid card, try again"` (Bedrock re-prompts politely)
- **Expired Date**: `validate_expiry` fails → Re-ask
- **Wrong CVV**: Format check fails → Re-ask
- **Bedrock Timeout**: Retry once, fallback to generic error
- **User Cancels**: Any message with "cancel" → End session
- **DynamoDB Error**: Retry 3x, return 500 if all fail

## Security Considerations

### PCI-DSS Compliance:
1. **No Storage**: Card/CVV purged from DynamoDB after tokenization
2. **No Logs**: CloudWatch logs mask all sensitive fields
3. **Encryption**:
   - In-transit: HTTPS (TLS 1.2+)
   - At-rest: KMS for DynamoDB, S3 (if used)
4. **Access Control**: IAM policies (least privilege)
5. **Network**: Lambda in VPC (optional, for extra isolation)
6. **Tokenization**: Stripe handles PCI scope

### Bedrock Guardrails (Optional):
- **Content Filters**: Block harmful/toxic output
- **PII Redaction**: Prevent accidental leaks of SSN, etc.
- **Cost**: $0.15 per 1,000 text units (worth it for production)

### IAM Policies:
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "kms:Decrypt"
      ],
      "Resource": [
        "arn:aws:bedrock:us-east-1::foundation-model/meta.llama3-2-1b-instruct-v1:0",
        "arn:aws:dynamodb:us-east-1:ACCOUNT:table/payment-bot-sessions",
        "arn:aws:logs:us-east-1:ACCOUNT:log-group:/aws/lambda/*",
        "arn:aws:kms:us-east-1:ACCOUNT:key/*"
      ]
    }
  ]
}
```

## Scalability

### Current Setup (On-Demand):
- Lambda: Auto-scales to 1,000 concurrent invocations
- Bedrock: Burst up to 5,000 tokens/sec
- DynamoDB: On-Demand scales automatically
- Cost: Pay-per-use (no idle costs)

### High Volume (>10k requests/hour):
- Switch Lambda to **Provisioned Concurrency** (reduce cold starts)
- Bedrock **Provisioned Throughput**: $13-$21/hour for guaranteed capacity
- DynamoDB **Provisioned Mode**: Fixed read/write units (cheaper at scale)
- Add **ElastiCache** (Redis) for session caching (reduce DynamoDB reads)

### Batch Processing (Non-Real-Time):
- Use Bedrock **Batch Inference**: 50% discount
- Example: Process 10k payments overnight → $2.50 instead of $5

## Monitoring & Alerting

### Key Metrics:
1. **Lambda**:
   - Invocations (per minute)
   - Errors (>1% → alert)
   - Duration (p99 <2s)
2. **Bedrock**:
   - Token usage (input + output)
   - Throttles (should be 0)
   - Latency (p95 <1s)
3. **DynamoDB**:
   - Read/write capacity
   - Throttles
4. **API Gateway**:
   - 4xx errors (client issues)
   - 5xx errors (server issues)

### Alerts (SNS → Email/Slack):
- Lambda error rate >5%
- Bedrock throttling detected
- DynamoDB write failures
- Stripe API errors

## Cost Optimization

### Tips:
1. **Prompt Caching**: Bedrock caches repeated system prompts (90% discount on cached tokens)
2. **Batch Mode**: For non-urgent flows (e.g., daily reconciliation)
3. **Right-Size Lambda**: Start with 512MB, monitor and adjust
4. **Reserved Capacity**: Commit to 1-year Bedrock for 30% off
5. **Session Cleanup**: TTL on DynamoDB to avoid storage bloat

## Future Enhancements

1. **Multi-Model**: Switch between Llama 1B/3B/7B based on complexity
2. **Prompt Tuning**: Fine-tune Llama on payment-specific dialogues
3. **Voice Integration**: Amazon Transcribe + Polly for voice payments
4. **Fraud Detection**: Integrate AWS Fraud Detector or custom ML
5. **Multi-Language**: Bedrock supports 8+ languages (expand system prompt)
6. **A/B Testing**: Compare Llama vs Mistral performance

---

**Total Development Time**: 1-2 weeks for MVP  
**Estimated Monthly Cost (1,000 customers)**: $0.50 (Bedrock) + ~$1 (AWS services) = **~$1.50/month**
