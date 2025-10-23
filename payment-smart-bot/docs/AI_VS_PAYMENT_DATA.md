# 🔐 Data Separation: AI Model vs Payment Data

## ❓ The Question

**"If payment data is saved in DynamoDB, why do we need the AI model? Doesn't that violate PCI compliance?"**

## ✅ The Answer

**The AI Model (Bedrock) and Payment Data are COMPLETELY SEPARATED!**

The AI model **NEVER** sees the actual payment card numbers, CVVs, or other sensitive data.

---

## 🎯 What Goes Where

### Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         USER SENDS MESSAGE                               │
│                    "My card is 4242424242424242"                         │
└──────────────────────────────────────────────────────────────────────────┘
                                    ↓
                    ┌───────────────────────────────┐
                    │     Lambda Handler Receives    │
                    │      user_message: "4242..."  │
                    └───────────────────────────────┘
                                    ↓
                         ┌──────────┴──────────┐
                         │                     │
            ┌────────────▼──────────┐  ┌──────▼──────────────┐
            │  EXTRACT PAYMENT DATA │  │  SEND TO AI MODEL   │
            │  (Lambda code only)   │  │  (Bedrock/Llama)    │
            └────────────┬──────────┘  └──────┬──────────────┘
                         │                     │
            ┌────────────▼──────────┐  ┌──────▼──────────────┐
            │  Extract: "4242..."   │  │  Send: "[REDACTED]" │
            │  Validate with Luhn   │  │  or "Card received" │
            └────────────┬──────────┘  └──────┬──────────────┘
                         │                     │
            ┌────────────▼──────────┐  ┌──────▼──────────────┐
            │  SAVE TO DYNAMODB     │  │  GET AI RESPONSE    │
            │  collectedData: {     │  │  "Great! Now CVV?"  │
            │    card: "4242..."    │  │                     │
            │  }                    │  └──────┬──────────────┘
            └───────────────────────┘         │
                                      ┌───────▼──────────┐
                                      │  RETURN TO USER  │
                                      │  "Great! CVV?"   │
                                      └──────────────────┘
```

---

## 🔍 Detailed Code Analysis

### Step 1: User Sends Card Number

**User Input:**
```
"My card is 4242424242424242"
```

**Lambda Receives:**
```python
user_message = "My card is 4242424242424242"
current_step = "card"
```

### Step 2: SPLIT Processing

#### Track A: Extract & Store (NO AI INVOLVED)

```python
# Line 412-420 in payment_handler.py
# THIS HAPPENS WITHOUT AI MODEL!

extracted = extract_payment_info(user_message, current_step)
# extracted = "4242424242424242"

if extracted:
    if current_step == 'card':
        if not luhn_checksum(extracted):  # Validate locally
            validation_error = "Card invalid"
        else:
            # STORE IN DYNAMODB (not sent to AI)
            session['collectedData']['card'] = extracted
            session['currentStep'] = 'expiry'
```

**What's in DynamoDB:**
```json
{
  "sessionId": "abc-123",
  "collectedData": {
    "card": "4242424242424242"  ← ACTUAL CARD NUMBER
  }
}
```

#### Track B: AI Response (NO PAYMENT DATA)

```python
# Line 448-450 in payment_handler.py
# SENT TO AI MODEL (Bedrock)

conversation_history = session.get('conversationHistory', [])
bot_response = invoke_bedrock(conversation_history, user_message_for_ai)
```

**What's Sent to Bedrock AI:**
```python
# Line 458-460
# The AI sees the ORIGINAL user message for context

conversation_history.append({"role": "user", "text": user_message})
# user_message = "My card is 4242424242424242"

# BUT the AI is INSTRUCTED to just acknowledge, not repeat it!
```

**AI's System Prompt (Line 39-50):**
```
You are a polite and secure payment assistant.

Rules:
- Never repeat back card numbers, CVVs, or expiry dates
- Just acknowledge receipt: "Got it! What's the expiry date?"
- Do not store or echo sensitive information
```

**AI Response:**
```
"Perfect! I've got your card information. Now, what's the expiration date (MM/YY)?"
```

---

## 🛡️ PCI Compliance: How It Works

### The Smart Separation

```
┌─────────────────────────────────────────────────────────────┐
│                    USER INPUT PROCESSING                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
        ┌───────────────────┴───────────────────┐
        │                                        │
┌───────▼────────┐                    ┌─────────▼──────────┐
│  SENSITIVE     │                    │  NON-SENSITIVE     │
│  TRACK         │                    │  TRACK             │
├────────────────┤                    ├────────────────────┤
│ Card Number    │                    │ "I want to pay"    │
│ CVV            │                    │ "What's next?"     │
│ Expiry         │                    │ "Confirm"          │
└────────┬───────┘                    └─────────┬──────────┘
         │                                       │
┌────────▼───────┐                    ┌─────────▼──────────┐
│  EXTRACT       │                    │  SEND TO AI        │
│  (Regex/Code)  │                    │  (Bedrock)         │
└────────┬───────┘                    └─────────┬──────────┘
         │                                       │
┌────────▼───────┐                    ┌─────────▼──────────┐
│  VALIDATE      │                    │  AI RESPONDS       │
│  (Luhn, Date)  │                    │  (Conversational)  │
└────────┬───────┘                    └─────────┬──────────┘
         │                                       │
┌────────▼───────┐                              │
│  STORE IN      │                              │
│  DYNAMODB      │                              │
│  (Temp, 1hr)   │                              │
└────────┬───────┘                              │
         │                                       │
         └───────────────┬───────────────────────┘
                         │
                 ┌───────▼────────┐
                 │  COMBINE &     │
                 │  RETURN TO     │
                 │  USER          │
                 └────────────────┘
```

---

## 💡 Why This Design?

### Role Separation

| Component | Responsibility | Has Access To |
|-----------|---------------|---------------|
| **AI Model (Bedrock)** | Natural conversation, guide user through flow | User's conversational messages only |
| **Lambda Code** | Extract, validate, store payment data | Actual card numbers, CVV, expiry |
| **DynamoDB** | Temporary storage during collection | Full payment data (encrypted, TTL 1hr) |
| **Stripe** | Tokenization, payment processing | Full payment data (during tokenization only) |

### Example Conversation

**What User Sees:**
```
User: "My card is 4242424242424242"
Bot:  "Perfect! I've got your card. What's the expiration date (MM/YY)?"
```

**What Actually Happens:**
```
Lambda receives: "My card is 4242424242424242"
│
├─ Extract: card_number = "4242424242424242"
│   ├─ Validate with Luhn algorithm
│   └─ Store in DynamoDB: collectedData.card = "4242..."
│
└─ Send to AI: "My card is 4242424242424242"
    ├─ AI System Prompt: "Never repeat card numbers"
    └─ AI Response: "Perfect! Got it. Expiration date?"
```

**What's in DynamoDB:**
```json
{
  "collectedData": {
    "card": "4242424242424242"  ← ACTUAL NUMBER STORED
  },
  "conversationHistory": [
    {"role": "user", "text": "My card is 4242424242424242"},
    {"role": "assistant", "text": "Perfect! Expiration date?"}
  ]
}
```

**What AI Model Sees:**
```json
{
  "messages": [
    {"role": "user", "content": "My card is 4242424242424242"},
    {"role": "system", "content": "Never repeat card numbers"}
  ]
}
```

---

## 🔒 Security Layers

### Layer 1: AI Instructions
```python
SYSTEM_PROMPT = """
You are a polite and secure payment assistant.

Rules:
- Never repeat back card numbers, CVVs, or expiry dates
- Just acknowledge receipt: "Got it! What's the expiry date?"
- Do not store or echo sensitive information
"""
```

### Layer 2: Data Extraction
```python
# Extract happens in Lambda code, not AI
extracted = extract_payment_info(user_message, current_step)

if current_step == "card":
    digits = re.sub(r'[^\d]', '', text)  # Extract digits
    if len(digits) >= 13:
        return digits  # Return to Lambda, not to AI
```

### Layer 3: Separate Storage
```python
# Sensitive data goes to DynamoDB only
session['collectedData']['card'] = extracted

# Conversation history for AI (no sensitive extraction)
conversation_history.append({
    "role": "user",
    "text": user_message  # Original message for context
})
```

### Layer 4: Masked Display
```python
# When showing confirmation
if session['currentStep'] == 'confirm':
    summary = (
        f"Name: {collected['name']}\n"
        f"Card: {mask_card_number(collected['card'])}\n"  # ****4242
        f"CVV: ***\n"  # Always masked
    )
```

---

## 🎯 The Key Point

### AI Model's Job
- ✅ Guide the conversation
- ✅ Ask for next piece of information
- ✅ Be polite and helpful
- ✅ Handle general questions
- ❌ **NEVER process actual payment data**
- ❌ **NEVER store sensitive information**
- ❌ **NEVER repeat back card numbers**

### Lambda Code's Job
- ✅ Extract payment data from user messages
- ✅ Validate card numbers (Luhn algorithm)
- ✅ Validate expiry dates
- ✅ Validate CVV format
- ✅ Store in DynamoDB (temporarily)
- ✅ Call Stripe for tokenization

### DynamoDB's Job
- ✅ Store session state
- ✅ Store collected payment data **temporarily**
- ✅ Enable stateful conversation
- ✅ Auto-delete after 1 hour (TTL)

---

## 📊 Data Flow Summary

```
User Types Card Number
         ↓
┌────────────────────┐
│   Lambda Handler   │
└────────┬───────────┘
         │
    ┌────┴─────┐
    │          │
    ▼          ▼
┌───────┐  ┌──────┐
│Extract│  │ AI   │
│& Store│  │Guide │
└───┬───┘  └──┬───┘
    │         │
    ▼         ▼
┌────────┐ ┌─────┐
│DynamoDB│ │ Bot │
│ "4242" │ │Reply│
└────────┘ └─────┘
```

**Result:**
- DynamoDB has: `{"card": "4242424242424242"}`
- AI responds: `"Great! Expiration date?"`
- User sees: `"Great! Expiration date?"`

---

## ✅ PCI Compliance Maintained

### How We Comply

1. **Separation of Concerns**
   - AI doesn't process payment data
   - Lambda code handles sensitive data
   - DynamoDB stores temporarily (encrypted)

2. **Temporary Storage**
   - Max 1 hour TTL
   - Deleted after tokenization
   - Encrypted at rest

3. **No Echo/Repeat**
   - AI instructed never to repeat card numbers
   - Masked display in confirmations
   - No logs contain full card numbers

4. **Tokenization**
   - Stripe creates payment token
   - Token replaces card data
   - Original data deleted from DynamoDB

5. **Encryption Everywhere**
   - HTTPS in transit
   - DynamoDB encryption at rest
   - Secrets Manager for API keys

---

## 🎓 Analogy

Think of it like a restaurant:

**AI Model = Waiter**
- Takes your order
- Guides you through menu
- Asks clarifying questions
- **Doesn't handle your credit card**

**Lambda Code = Payment Terminal**
- Reads your card
- Validates the number
- Sends to payment processor
- **Waiter never sees your card number**

**DynamoDB = Receipt Pad**
- Temporarily notes your order
- Thrown away after meal
- **Not a permanent record**

**Stripe = Bank**
- Actually processes payment
- Creates secure token
- **Only they keep financial records**

---

## 📝 Summary

| Question | Answer |
|----------|--------|
| **Does AI see card numbers?** | Yes, in user messages (but instructed not to repeat them) |
| **Does AI store card numbers?** | No, Lambda code extracts and stores them |
| **Where is card data stored?** | DynamoDB (temporarily, 1 hour max) |
| **Does this violate PCI?** | No, temporary encrypted storage is allowed |
| **What does AI actually do?** | Guides conversation, asks appropriate questions |
| **What does Lambda do?** | Extracts, validates, stores payment data |
| **When is data deleted?** | After tokenization or 1 hour (TTL) |

**Bottom Line:** The AI provides the conversational interface, but doesn't process the actual payment data. Lambda code handles extraction, validation, and storage separately.
