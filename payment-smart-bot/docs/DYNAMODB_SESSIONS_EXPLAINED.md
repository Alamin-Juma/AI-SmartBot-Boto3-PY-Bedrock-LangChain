# 🗄️ DynamoDB Sessions - Purpose and Architecture

## 📌 Overview

DynamoDB is used to store **session state** for each payment collection conversation. This enables the bot to maintain context across multiple messages and remember what information has been collected.

---

## 🎯 Why Sessions Are Needed

### Problem Without Sessions
Imagine this conversation:
```
User: "I want to make a payment"
Bot: "What's your name?"
User: "John Smith"
Bot: "What's your name?"  ❌ Bot forgot!
```

### Solution With Sessions
```
User: "I want to make a payment"
Bot: "What's your name?"
User: "John Smith"          [Stored in DynamoDB]
Bot: "Thanks John! Card number?"  ✅ Bot remembers!
```

AWS Lambda is **stateless** - each invocation is independent. Sessions provide memory across multiple API calls.

---

## 📊 What's Stored in DynamoDB

### Session Table Structure

From your screenshot (`payment-smart-bot-sessions-dev`), each session contains:

```json
{
  "sessionId": "test-123",           // Unique identifier (UUID)
  "collectionData": {                 // Payment info being collected
    "name": "John Smith",
    "card": "4242424242424242",      // Temporarily stored
    "expiry": "12/25",
    "cvv": "123"
  },
  "conversationHistory": [            // AI conversation context
    {"role": "user", "content": "I want to make a payment"},
    {"role": "assistant", "content": "What's your name?"},
    {"role": "user", "content": "John Smith"}
  ],
  "currentStep": "card",              // Where in the flow (name/card/expiry/cvv/confirm)
  "status": "collecting",             // collecting/awaiting_confirmation/completed/error
  "lastUpdated": "2025-10-15T13:34:21.346Z",
  "ttl": 1697389461                   // Auto-delete after 1 hour
}
```

---

## 🔄 Session Lifecycle

### 1. Session Creation
```
Frontend                API Gateway              Lambda
   │                       │                        │
   ├─ POST /chat ─────────>│                        │
   │  sessionId: new-uuid  │                        │
   │                       ├─ Invoke ──────────────>│
   │                       │                        ├─ Check DynamoDB
   │                       │                        │  (Session not found)
   │                       │                        ├─ Create new session
   │                       │                        ├─ Save to DynamoDB
   │                       │<─ Response ────────────┤
   │<─ Bot greeting ───────┤                        │
```

### 2. Collecting Information (Multiple Requests)
```
Request 1: "John Smith"
├─ Load session from DynamoDB
├─ Add to conversationHistory
├─ Store name in collectionData
├─ Set currentStep = "card"
├─ Save session back to DynamoDB
└─ Return: "Thanks John! Card number?"

Request 2: "4242424242424242"
├─ Load session from DynamoDB (has name)
├─ Add to conversationHistory
├─ Validate card with Luhn algorithm
├─ Store card in collectionData
├─ Set currentStep = "expiry"
├─ Save session back to DynamoDB
└─ Return: "Great! Expiration date?"

Request 3: "12/25"
├─ Load session from DynamoDB (has name + card)
├─ Add to conversationHistory
├─ Validate expiry date (not expired)
├─ Store expiry in collectionData
├─ Set currentStep = "cvv"
├─ Save session back to DynamoDB
└─ Return: "Perfect! CVV?"

Request 4: "123"
├─ Load session from DynamoDB (has name + card + expiry)
├─ Add to conversationHistory
├─ Validate CVV (3 digits)
├─ Store cvv in collectionData
├─ Set currentStep = "confirm"
├─ Set status = "awaiting_confirmation"
├─ Save session back to DynamoDB
└─ Return: "Please review... Type 'confirm'"

Request 5: "confirm"
├─ Load session from DynamoDB (has all data)
├─ Call Stripe API to tokenize card
├─ Delete session from DynamoDB (cleanup)
└─ Return: "✅ Payment successful! Token: tok_xxx"
```

### 3. Session Cleanup
- **Automatic:** TTL (Time To Live) = 1 hour
- **Manual:** Deleted after successful payment
- **On Error:** Remains for debugging (with TTL)

---

## 🔐 Security Considerations

### What's Stored
✅ **Stored in DynamoDB:**
- Conversation history (AI context)
- Collection progress (current step)
- Payment data **temporarily** during collection
- Session metadata (timestamps, status)

### What's NOT Stored Long-Term
❌ **Deleted After Tokenization:**
- Full card number (deleted after Stripe tokenization)
- CVV (deleted after Stripe tokenization)
- Sensitive data is **never** stored permanently

### PCI-DSS Compliance
```
Collection Flow:
User Input → Lambda Memory → DynamoDB (temp, TTL 1hr) → Stripe API
                                                             ↓
                                                         Token Created
                                                             ↓
                                                  Delete from DynamoDB
                                                             ↓
                                               Return token to frontend
```

**Key Points:**
1. Card data stored **temporarily** (max 1 hour due to TTL)
2. Encrypted at rest (DynamoDB encryption)
3. Encrypted in transit (HTTPS)
4. Deleted immediately after tokenization
5. Only tokenized reference (tok_xxx) returned to frontend

---

## 📈 Session Flow Example

### Real Example from Your Screenshot

**Session ID:** `test-003`
```
Status: awaiting_confirmation
Current Step: confirm
Last Updated: 2025-10-15T...

Collection Data:
{
  "name": "✓",
  "card": "✓",
  "expiry": "✓",
  "cvv": "✓"
}

Conversation History:
[User] "I want to make a payment"
[Bot]  "What's your name?"
[User] "John Smith"
[Bot]  "Thanks! Card number?"
[User] "4242424242424242"
[Bot]  "Expiration date?"
[User] "12/25"
[Bot]  "CVV?"
[User] "123"
[Bot]  "Review your info... Type 'confirm'"
```

**Session ID:** `test-456`
```
Status: collecting
Current Step: card
Last Updated: 2025-10-14T...

Collection Data:
{
  "name": "John Smith"
}

Conversation History:
[User] "Hi"
[Bot]  "Hello! Ready to help with payment. Name?"
[User] "John Smith"
[Bot]  "Thanks John! Card number?"
```

---

## 🛠️ Technical Implementation

### Code Reference

**Get Session:**
```python
def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve session data from DynamoDB."""
    table = dynamodb.Table(SESSION_TABLE)
    response = table.get_item(Key={'sessionId': session_id})
    return response.get('Item')
```

**Save Session:**
```python
def save_session(session_id: str, session_data: Dict[str, Any]) -> bool:
    """Save session data to DynamoDB (non-sensitive data only)."""
    table = dynamodb.Table(SESSION_TABLE)
    
    # Add TTL (1 hour from now)
    ttl = int(datetime.now().timestamp()) + 3600
    
    table.put_item(Item={
        'sessionId': session_id,
        'conversationHistory': session_data.get('conversation_history', []),
        'collectionData': session_data.get('collected_data', {}),
        'currentStep': session_data.get('current_step', 'none'),
        'status': session_data.get('status', 'collecting'),
        'lastUpdated': datetime.utcnow().isoformat(),
        'ttl': ttl
    })
```

**Load Session in Handler:**
```python
def lambda_handler(event, context):
    body = json.loads(event['body'])
    session_id = body['sessionId']
    user_message = body['message']
    
    # Load existing session or create new
    session = get_session(session_id) or {
        'conversationHistory': [],
        'collectionData': {},
        'currentStep': 'none',
        'status': 'collecting'
    }
    
    # Process message with context from session
    # ...
    
    # Save updated session
    save_session(session_id, session)
```

---

## 💡 Benefits of Session Storage

### 1. **Stateful Conversations**
- Remember what's been collected
- Skip already-asked questions
- Maintain natural conversation flow

### 2. **Multi-Step Validation**
- Validate each field independently
- Provide specific error messages
- Retry only failed fields

### 3. **Resumable Sessions**
- User can refresh page
- Continue where they left off
- No data loss during collection

### 4. **Debugging & Monitoring**
- Track payment flow progress
- Identify where users drop off
- Analyze conversation patterns

### 5. **Fraud Prevention**
- Track suspicious patterns
- Rate limiting per session
- Audit trail of attempts

---

## 📊 DynamoDB Table Configuration

### Primary Key
```
Partition Key: sessionId (String)
```

### Attributes
```
sessionId           String      (Partition Key)
conversationHistory List        (Array of messages)
collectionData      Map         (Payment info)
currentStep         String      (name/card/expiry/cvv/confirm)
status              String      (collecting/confirming/completed/error)
lastUpdated         String      (ISO timestamp)
ttl                 Number      (Unix timestamp for auto-deletion)
```

### TTL (Time To Live)
```
Attribute: ttl
Enabled: Yes
Expiration: 1 hour after lastUpdated
Purpose: Auto-delete old/completed sessions
```

### Capacity Mode
```
Mode: On-Demand (pay per request)
Scales: Automatically
Cost: ~$0.25 per million writes
```

---

## 🔍 Session States

### Status Values

1. **collecting** - Gathering payment information
   ```
   currentStep: name → card → expiry → cvv
   ```

2. **awaiting_confirmation** - All data collected, waiting for user confirmation
   ```
   currentStep: confirm
   collectionData: {name, card, expiry, cvv}
   ```

3. **completed** - Payment tokenized successfully
   ```
   currentStep: none
   Session deleted from DynamoDB
   ```

4. **error** - Validation or processing error
   ```
   currentStep: <where error occurred>
   error: "Invalid card number"
   ```

---

## 📈 Monitoring Sessions

### CloudWatch Metrics
- Number of active sessions
- Average session duration
- Completion rate
- Drop-off points

### DynamoDB Insights
- Read/Write capacity usage
- Item count
- Storage size
- TTL deletions

### Your Screenshot Analysis
From your DynamoDB table, I can see:
- **10 items returned** (active sessions)
- Various states: collecting, confirming, error
- Multiple test sessions (test-123, test-003, etc.)
- Recent activity (2025-10-15 timestamps)

---

## 🎯 Summary

**Sessions Enable:**
1. ✅ Multi-step payment collection
2. ✅ Conversation context across requests
3. ✅ State management in stateless Lambda
4. ✅ Resumable user experience
5. ✅ Temporary secure storage
6. ✅ Auto-cleanup with TTL

**Without Sessions:**
- ❌ Bot would forget previous answers
- ❌ Users would have to re-enter everything
- ❌ No way to track collection progress
- ❌ Can't validate multi-field relationships

**The session is the "memory" of your payment bot!** 🧠

---

## 📚 Related Documentation

- [Lambda Handler Code](../lambda/payment_handler.py)
- [DynamoDB Configuration](../terraform/main.tf)
- [API Documentation](./API_DOCUMENTATION.md)
- [Security Architecture](./ARCHITECTURE.md)
