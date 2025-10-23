# 🎨 DynamoDB Sessions - Visual Flow Diagram

## 🔄 Complete Payment Flow with Sessions

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          PAYMENT COLLECTION FLOW                            │
│                        (DynamoDB Session Tracking)                          │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────>│ API Gateway  │────>│    Lambda    │────>│  DynamoDB    │
│  (Streamlit) │<────│              │<────│   Handler    │<────│  (Sessions)  │
└──────────────┘     └──────────────┘     └──────────────┘     └──────────────┘


Step 1: User Starts Conversation
═════════════════════════════════
Frontend                 Lambda                      DynamoDB
   │                       │                            │
   ├─ POST /chat ─────────>│                            │
   │  sessionId: abc-123   │                            │
   │  message: "payment"   │                            │
   │                       ├─ get_session(abc-123) ───>│
   │                       │<─ None (new session) ──────┤
   │                       │                            │
   │                       │  Create session:           │
   │                       │  {                         │
   │                       │    conversationHistory: [] │
   │                       │    collectionData: {}      │
   │                       │    currentStep: "none"     │
   │                       │    status: "collecting"    │
   │                       │  }                         │
   │                       │                            │
   │                       ├─ Call Bedrock (Llama) ────>│
   │                       │<─ "What's your name?" ─────┤
   │                       │                            │
   │                       ├─ save_session(abc-123) ───>│
   │                       │                            ├─ STORE:
   │                       │                            │  sessionId: abc-123
   │                       │                            │  conversationHistory: [
   │                       │                            │    {role: "user", content: "payment"}
   │                       │                            │    {role: "assistant", content: "What's your name?"}
   │                       │                            │  ]
   │                       │                            │  currentStep: "name"
   │                       │                            │  status: "collecting"
   │                       │                            │  ttl: <1 hour from now>
   │                       │<─ Saved ────────────────────┤
   │<─ "What's your name?" ┤                            │


Step 2: User Provides Name
═══════════════════════════
Frontend                 Lambda                      DynamoDB
   │                       │                            │
   ├─ POST /chat ─────────>│                            │
   │  sessionId: abc-123   │                            │
   │  message: "John"      │                            │
   │                       ├─ get_session(abc-123) ───>│
   │                       │<─ LOAD SESSION ────────────┤
   │                       │  conversationHistory: [previous msgs]
   │                       │  collectionData: {}        │
   │                       │  currentStep: "name"       │
   │                       │                            │
   │                       │  Update session:           │
   │                       │  collectionData.name = "John"
   │                       │  currentStep = "card"      │
   │                       │                            │
   │                       ├─ Call Bedrock ────────────>│
   │                       │<─ "Card number?" ──────────┤
   │                       │                            │
   │                       ├─ save_session(abc-123) ───>│
   │                       │                            ├─ UPDATE:
   │                       │                            │  conversationHistory: [+ new msgs]
   │                       │                            │  collectionData: {name: "John"}
   │                       │                            │  currentStep: "card"
   │                       │<─ Saved ────────────────────┤
   │<─ "Card number?" ─────┤                            │


Step 3: User Provides Card
═══════════════════════════
Frontend                 Lambda                      DynamoDB
   │                       │                            │
   ├─ POST /chat ─────────>│                            │
   │  sessionId: abc-123   │                            │
   │  message: "4242..."   │                            │
   │                       ├─ get_session(abc-123) ───>│
   │                       │<─ LOAD SESSION ────────────┤
   │                       │  collectionData: {name: "John"}
   │                       │  currentStep: "card"       │
   │                       │                            │
   │                       │  Validate card (Luhn)      │
   │                       │  ✓ Valid                   │
   │                       │                            │
   │                       │  Update session:           │
   │                       │  collectionData.card = "4242..."
   │                       │  currentStep = "expiry"    │
   │                       │                            │
   │                       ├─ save_session(abc-123) ───>│
   │                       │                            ├─ UPDATE:
   │                       │                            │  collectionData: {
   │                       │                            │    name: "John",
   │                       │                            │    card: "4242..."
   │                       │                            │  }
   │                       │                            │  currentStep: "expiry"
   │                       │<─ Saved ────────────────────┤
   │<─ "Expiration?" ──────┤                            │


Step 4: User Provides Expiry
═════════════════════════════
Frontend                 Lambda                      DynamoDB
   │                       │                            │
   ├─ POST /chat ─────────>│                            │
   │  sessionId: abc-123   │                            │
   │  message: "12/25"     │                            │
   │                       ├─ get_session(abc-123) ───>│
   │                       │<─ LOAD SESSION ────────────┤
   │                       │  collectionData: {         │
   │                       │    name: "John",           │
   │                       │    card: "4242..."         │
   │                       │  }                         │
   │                       │  currentStep: "expiry"     │
   │                       │                            │
   │                       │  Validate expiry           │
   │                       │  ✓ Not expired             │
   │                       │                            │
   │                       │  Update session:           │
   │                       │  collectionData.expiry = "12/25"
   │                       │  currentStep = "cvv"       │
   │                       │                            │
   │                       ├─ save_session(abc-123) ───>│
   │                       │                            ├─ UPDATE:
   │                       │                            │  collectionData: {
   │                       │                            │    name: "John",
   │                       │                            │    card: "4242...",
   │                       │                            │    expiry: "12/25"
   │                       │                            │  }
   │                       │                            │  currentStep: "cvv"
   │                       │<─ Saved ────────────────────┤
   │<─ "CVV?" ─────────────┤                            │


Step 5: User Provides CVV
══════════════════════════
Frontend                 Lambda                      DynamoDB
   │                       │                            │
   ├─ POST /chat ─────────>│                            │
   │  sessionId: abc-123   │                            │
   │  message: "123"       │                            │
   │                       ├─ get_session(abc-123) ───>│
   │                       │<─ LOAD SESSION ────────────┤
   │                       │  collectionData: {         │
   │                       │    name: "John",           │
   │                       │    card: "4242...",        │
   │                       │    expiry: "12/25"         │
   │                       │  }                         │
   │                       │  currentStep: "cvv"        │
   │                       │                            │
   │                       │  Validate CVV              │
   │                       │  ✓ 3 digits                │
   │                       │                            │
   │                       │  ALL DATA COLLECTED!       │
   │                       │  Update session:           │
   │                       │  collectionData.cvv = "123"│
   │                       │  currentStep = "confirm"   │
   │                       │  status = "awaiting_confirmation"
   │                       │                            │
   │                       ├─ save_session(abc-123) ───>│
   │                       │                            ├─ UPDATE:
   │                       │                            │  collectionData: {
   │                       │                            │    name: "John",
   │                       │                            │    card: "4242...",
   │                       │                            │    expiry: "12/25",
   │                       │                            │    cvv: "123"
   │                       │                            │  }
   │                       │                            │  currentStep: "confirm"
   │                       │                            │  status: "awaiting_confirmation"
   │                       │<─ Saved ────────────────────┤
   │<─ "Review & confirm" ─┤                            │


Step 6: User Confirms
══════════════════════
Frontend                 Lambda                      DynamoDB          Stripe
   │                       │                            │                │
   ├─ POST /chat ─────────>│                            │                │
   │  sessionId: abc-123   │                            │                │
   │  message: "confirm"   │                            │                │
   │                       ├─ get_session(abc-123) ───>│                │
   │                       │<─ LOAD SESSION ────────────┤                │
   │                       │  collectionData: {ALL DATA}│                │
   │                       │  status: "awaiting_confirmation"            │
   │                       │                            │                │
   │                       │  Call Stripe API ──────────────────────────>│
   │                       │  create_payment_method({   │                │
   │                       │    card: {                 │                │
   │                       │      number: "4242...",    │                │
   │                       │      exp_month: 12,        │                │
   │                       │      exp_year: 2025,       │                │
   │                       │      cvc: "123"            │                │
   │                       │    },                      │                │
   │                       │    billing: {name: "John"} │                │
   │                       │  })                        │                │
   │                       │<─ PaymentMethod ───────────────────────────┤
   │                       │  token: tok_abc123xyz      │                │
   │                       │  last4: 4242               │                │
   │                       │                            │                │
   │                       │  ✅ SUCCESS!               │                │
   │                       │  DELETE SESSION (cleanup)  │                │
   │                       │                            │                │
   │                       ├─ delete_session(abc-123) ─>│                │
   │                       │<─ Deleted ──────────────────┤                │
   │                       │                            │                │
   │<─ "✅ Payment token" ─┤                            │                │
   │    tok_abc123xyz      │                            │                │


═══════════════════════════════════════════════════════════════════════════════


SESSION STATE IN DYNAMODB (During Collection)
══════════════════════════════════════════════

After Step 1 (Name requested):
┌─────────────────────────────────────────┐
│ sessionId: abc-123                      │
├─────────────────────────────────────────┤
│ conversationHistory: [                  │
│   {role: "user", content: "payment"}    │
│   {role: "assistant", content: "name?"} │
│ ]                                       │
│                                         │
│ collectionData: {}                      │
│                                         │
│ currentStep: "name"                     │
│ status: "collecting"                    │
│ lastUpdated: "2025-10-15T13:00:00Z"    │
│ ttl: 1697389200 (1 hour)               │
└─────────────────────────────────────────┘


After Step 3 (Card collected):
┌─────────────────────────────────────────┐
│ sessionId: abc-123                      │
├─────────────────────────────────────────┤
│ conversationHistory: [                  │
│   ... (previous messages)               │
│   {role: "user", content: "4242..."}    │
│   {role: "assistant", content: "exp?"} │
│ ]                                       │
│                                         │
│ collectionData: {                       │
│   "name": "John",                       │
│   "card": "4242424242424242"           │
│ }                                       │
│                                         │
│ currentStep: "expiry"                   │
│ status: "collecting"                    │
│ lastUpdated: "2025-10-15T13:01:30Z"    │
│ ttl: 1697389290                         │
└─────────────────────────────────────────┘


After Step 5 (All data collected, awaiting confirm):
┌─────────────────────────────────────────┐
│ sessionId: abc-123                      │
├─────────────────────────────────────────┤
│ conversationHistory: [... all msgs]     │
│                                         │
│ collectionData: {                       │
│   "name": "John",                       │
│   "card": "4242424242424242",          │
│   "expiry": "12/25",                   │
│   "cvv": "123"                         │
│ }                                       │
│                                         │
│ currentStep: "confirm"                  │
│ status: "awaiting_confirmation"         │
│ lastUpdated: "2025-10-15T13:02:45Z"    │
│ ttl: 1697389365                         │
└─────────────────────────────────────────┘


After Step 6 (Payment tokenized):
┌─────────────────────────────────────────┐
│ SESSION DELETED FROM DYNAMODB           │
│                                         │
│ Sensitive data removed                  │
│ Only Stripe token (tok_xxx) returned    │
│ to frontend                             │
└─────────────────────────────────────────┘


═══════════════════════════════════════════════════════════════════════════════


WHY SESSIONS ARE CRITICAL
═════════════════════════

Without DynamoDB Sessions:
❌ Lambda is stateless - forgets everything after each request
❌ Bot would ask same questions repeatedly
❌ No way to validate all fields are collected
❌ Can't maintain conversation context
❌ User would have to send all data in one message

With DynamoDB Sessions:
✅ Remember conversation history across requests
✅ Track which fields are collected
✅ Maintain natural multi-turn conversation
✅ Validate each field independently
✅ Provide context to Bedrock AI
✅ Resume if user takes a break


═══════════════════════════════════════════════════════════════════════════════


SECURITY & TTL
══════════════

Time To Live (TTL):
┌────────────────────────────────────────────────────────────┐
│  t=0min     Session Created                                │
│             └─ TTL set to current_time + 3600 seconds      │
│                                                             │
│  t=30min    Still collecting data                          │
│             └─ Session exists in DynamoDB                  │
│                                                             │
│  t=45min    Payment confirmed, tokenized                   │
│             └─ Session manually deleted by Lambda          │
│                                                             │
│  t=60min    [If not deleted] TTL expires                   │
│             └─ DynamoDB auto-deletes session               │
└────────────────────────────────────────────────────────────┘

Security Benefits:
✅ Temporary storage (max 1 hour)
✅ Encrypted at rest
✅ Encrypted in transit
✅ Auto-cleanup prevents data accumulation
✅ Manual cleanup after tokenization
✅ No long-term storage of card data
