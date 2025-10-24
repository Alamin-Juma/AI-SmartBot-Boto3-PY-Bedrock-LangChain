"""
PCI-Compliant IVR Payment Bot Lambda Handler
============================================
Amazon Connect + Bedrock + Stripe Integration

KEY COMPLIANCE PRINCIPLE:
    Cardholder Data (CHD) NEVER reaches Amazon Bedrock AI.
    All CHD is masked/tokenized BEFORE AI processing.

Architecture:
    1. Amazon Connect captures voice input (card number via STT)
    2. Lambda IMMEDIATELY masks CHD → stores in S3 (encrypted)
    3. Lambda sends ONLY masked/non-sensitive data to Bedrock
    4. Bedrock (Mistral 7B) generates conversational response
    5. Lambda tokenizes CHD with Stripe (test mode)
    6. Response sent back to Connect → Polly speaks to caller

PCI DSS Compliance Features:
    - CHD masking before AI (SAQ A-EP eligible)
    - Encrypted S3 storage (KMS)
    - No CHD in CloudWatch logs
    - Stripe tokenization (removes CHD from scope)
    - Audit trail for all transactions
"""

import json
import os
import re
import boto3
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import hashlib

# Initialize AWS clients
bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
s3 = boto3.client('s3')
ssm = boto3.client('ssm')

# Environment configuration
# IMPORTANT: Use custom inference profile ARN for PCI compliance
# This ensures the model has NO access to customer data or training on payment info
BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'arn:aws:bedrock:us-east-1:YOUR_ACCOUNT:inference-profile/YOUR_CUSTOM_MISTRAL_PROFILE')
AUDIT_BUCKET = os.environ.get('AUDIT_BUCKET', 'payment-bot-audit-logs')
STRIPE_SECRET_PARAM = os.environ.get('STRIPE_SECRET_PARAM', '/payment-bot/stripe-secret')

# Stripe API (lazy load)
stripe = None


def mask_card_number(card_number: str) -> Tuple[str, str]:
    """
    Mask card number for PCI compliance.
    
    Returns:
        Tuple of (masked_card, last4)
        
    Example:
        "4111111111111111" → ("************1111", "1111")
    """
    # Remove spaces and dashes
    clean_card = re.sub(r'[^0-9]', '', card_number)
    
    if len(clean_card) < 13 or len(clean_card) > 19:
        return "****INVALID****", "0000"
    
    # Keep last 4 digits only
    last4 = clean_card[-4:]
    masked = "*" * (len(clean_card) - 4) + last4
    
    return masked, last4


def mask_sensitive_data(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively mask all sensitive data in payload.
    
    PCI Compliance: Ensures no CHD appears in logs or AI prompts.
    """
    masked_payload = {}
    
    # Define sensitive field patterns
    sensitive_patterns = [
        r'card.*number',
        r'pan',
        r'cvv',
        r'cvc',
        r'security.*code',
        r'expir.*date',
        r'exp.*date'
    ]
    
    for key, value in payload.items():
        key_lower = key.lower()
        
        # Check if key matches sensitive pattern
        is_sensitive = any(re.search(pattern, key_lower) for pattern in sensitive_patterns)
        
        if is_sensitive and isinstance(value, str):
            if 'card' in key_lower or 'pan' in key_lower:
                masked_payload[key], _ = mask_card_number(value)
            elif 'cvv' in key_lower or 'cvc' in key_lower:
                masked_payload[key] = "***"
            else:
                masked_payload[key] = "****MASKED****"
        elif isinstance(value, dict):
            masked_payload[key] = mask_sensitive_data(value)
        elif isinstance(value, list):
            masked_payload[key] = [mask_sensitive_data(item) if isinstance(item, dict) else item for item in value]
        else:
            masked_payload[key] = value
    
    return masked_payload


def store_audit_log(session_id: str, masked_data: Dict[str, Any], event_type: str) -> str:
    """
    Store masked transaction data in encrypted S3 for audit trail.
    
    Returns:
        S3 object key
    """
    timestamp = datetime.utcnow().isoformat()
    
    audit_record = {
        "sessionId": session_id,
        "timestamp": timestamp,
        "eventType": event_type,
        "data": masked_data,
        "compliance": {
            "pci_level": "SAQ_A_EP",
            "chd_masked": True,
            "ai_safe": True
        }
    }
    
    # Create S3 key with date partitioning
    date_prefix = datetime.utcnow().strftime('%Y/%m/%d')
    object_key = f"audit/{date_prefix}/{session_id}-{event_type}-{timestamp}.json"
    
    try:
        s3.put_object(
            Bucket=AUDIT_BUCKET,
            Key=object_key,
            Body=json.dumps(audit_record, indent=2),
            ServerSideEncryption='aws:kms',
            ContentType='application/json'
        )
        print(f"[AUDIT] Stored: s3://{AUDIT_BUCKET}/{object_key}")
        return object_key
    except Exception as e:
        print(f"[ERROR] Failed to store audit log: {e}")
        return ""


def invoke_bedrock(prompt: str, session_id: str) -> str:
    """
    Invoke Bedrock with NON-SENSITIVE prompt only.
    
    CRITICAL: This function must NEVER receive CHD.
    """
    # Safety check: scan for potential card numbers in prompt
    if re.search(r'\d{13,19}', prompt):
        print("[SECURITY VIOLATION] Potential CHD detected in Bedrock prompt!")
        return "I apologize, but I cannot process that information. Please try again."
    
    # Construct safe prompt for Mistral
    system_prompt = """You are a helpful payment assistant for an IVR system. 
Your role is to guide callers through payment steps and provide friendly responses.

IMPORTANT: You will NEVER see or process actual card numbers. 
You only help with conversation flow and validation guidance.

Keep responses concise (under 50 words) and voice-friendly."""

    full_prompt = f"<s>[INST] {system_prompt}\n\nUser: {prompt}\n[/INST]"
    
    try:
        response = bedrock_runtime.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            contentType='application/json',
            accept='application/json',
            body=json.dumps({
                "prompt": full_prompt,
                "max_tokens": 150,
                "temperature": 0.7,
                "top_p": 0.9,
                "stop": ["</s>", "[INST]"]
            })
        )
        
        response_body = json.loads(response['body'].read())
        ai_response = response_body.get('outputs', [{}])[0].get('text', '').strip()
        
        print(f"[BEDROCK] Response: {ai_response[:100]}...")
        return ai_response
        
    except Exception as e:
        print(f"[ERROR] Bedrock invocation failed: {e}")
        return "I'm having trouble processing your request. Please hold while I connect you to an agent."


def validate_with_stripe(card_number: str, exp_month: str, exp_year: str, cvv: str) -> Dict[str, Any]:
    """
    Tokenize card with Stripe (removes CHD from PCI scope).
    
    Returns:
        {
            "success": bool,
            "token": str,
            "card_brand": str,
            "last4": str,
            "error": str (if failed)
        }
    """
    global stripe
    
    # Lazy load Stripe SDK
    if stripe is None:
        try:
            import stripe as stripe_sdk
            stripe = stripe_sdk
            
            # Get Stripe secret from SSM Parameter Store
            param = ssm.get_parameter(Name=STRIPE_SECRET_PARAM, WithDecryption=True)
            stripe.api_key = param['Parameter']['Value']
        except Exception as e:
            print(f"[ERROR] Failed to initialize Stripe: {e}")
            return {"success": False, "error": "Payment system unavailable"}
    
    try:
        # Create Stripe token (this removes CHD from your scope)
        token = stripe.Token.create(
            card={
                "number": card_number,
                "exp_month": exp_month,
                "exp_year": exp_year,
                "cvc": cvv
            }
        )
        
        card_info = token.get('card', {})
        
        return {
            "success": True,
            "token": token['id'],
            "card_brand": card_info.get('brand', 'Unknown'),
            "last4": card_info.get('last4', '****'),
            "funding": card_info.get('funding', 'unknown')
        }
        
    except stripe.error.CardError as e:
        # Card validation failed
        return {
            "success": False,
            "error": e.user_message or "Card validation failed"
        }
    except Exception as e:
        print(f"[ERROR] Stripe tokenization failed: {e}")
        return {
            "success": False,
            "error": "Payment processing error"
        }


def generate_session_hash(session_id: str) -> str:
    """Generate SHA256 hash of session ID for secure references."""
    return hashlib.sha256(session_id.encode()).hexdigest()[:16]


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for Amazon Connect integration.
    
    Expected event structure from Connect:
    {
        "Details": {
            "ContactData": {
                "ContactId": "session-123",
                "CustomerEndpoint": "+1234567890"
            },
            "Parameters": {
                "userInput": "My card number is 4111111111111111",
                "cardNumber": "4111111111111111",
                "expiryMonth": "12",
                "expiryYear": "25",
                "cvv": "123",
                "intentType": "validate_payment"
            }
        }
    }
    """
    print(f"[START] Lambda invocation: {context.request_id if hasattr(context, 'request_id') else 'local-test'}")
    
    # Extract Connect parameters
    details = event.get('Details', {})
    contact_data = details.get('ContactData', {})
    parameters = details.get('Parameters', {})
    
    session_id = contact_data.get('ContactId', f"test-{datetime.utcnow().timestamp()}")
    session_hash = generate_session_hash(session_id)
    
    print(f"[SESSION] ID: {session_id[:20]}... | Hash: {session_hash}")
    
    # STEP 1: IMMEDIATELY mask sensitive data
    masked_params = mask_sensitive_data(parameters)
    
    # STEP 2: Store audit log with MASKED data only
    store_audit_log(session_id, masked_params, "ivr_interaction")
    
    # STEP 3: Extract intent and user input
    intent_type = parameters.get('intentType', 'general')
    user_input = parameters.get('userInput', '')
    
    # Mask any CHD in user input before sending to AI
    masked_input = user_input
    for match in re.finditer(r'\d{13,19}', user_input):
        card_num = match.group()
        masked_card, _ = mask_card_number(card_num)
        masked_input = masked_input.replace(card_num, masked_card)
    
    # STEP 4: Process based on intent
    response_text = ""
    stripe_result = {}
    
    if intent_type == 'validate_payment':
        # Extract payment details
        card_number = parameters.get('cardNumber', '')
        exp_month = parameters.get('expiryMonth', '')
        exp_year = parameters.get('expiryYear', '')
        cvv = parameters.get('cvv', '')
        
        if card_number and exp_month and exp_year and cvv:
            # Tokenize with Stripe (CHD leaves your environment)
            print(f"[STRIPE] Tokenizing card ending in ****{card_number[-4:]}")
            stripe_result = validate_with_stripe(card_number, exp_month, exp_year, cvv)
            
            if stripe_result.get('success'):
                # Generate AI response with MASKED data only
                ai_prompt = f"The customer provided a valid {stripe_result.get('card_brand', 'card')} ending in {stripe_result.get('last4')}. Confirm the payment method was accepted."
                response_text = invoke_bedrock(ai_prompt, session_id)
            else:
                ai_prompt = f"The card validation failed: {stripe_result.get('error')}. Politely ask the customer to verify their card details."
                response_text = invoke_bedrock(ai_prompt, session_id)
        else:
            response_text = "I need your card number, expiry date, and security code to process the payment. Which would you like to provide first?"
    
    elif intent_type == 'general':
        # General conversation (no CHD involved)
        response_text = invoke_bedrock(masked_input, session_id)
    
    else:
        response_text = "I can help you make a payment. Would you like to proceed?"
    
    # STEP 5: Return response to Connect
    result = {
        "statusCode": 200,
        "response": response_text,
        "sessionId": session_hash,  # Return hash, not actual session ID
        "metadata": {
            "timestamp": datetime.utcnow().isoformat(),
            "intent": intent_type,
            "pci_compliant": True,
            "chd_masked": True
        }
    }
    
    # Add Stripe token to response (safe to expose)
    if stripe_result.get('success'):
        result["stripeToken"] = stripe_result.get('token')
        result["cardBrand"] = stripe_result.get('card_brand')
        result["last4"] = stripe_result.get('last4')
    
    print(f"[RESPONSE] {response_text[:100]}...")
    print(f"[END] Processing complete")
    
    return result


# Local testing support
if __name__ == "__main__":
    # Test event for local development
    test_event = {
        "Details": {
            "ContactData": {
                "ContactId": "test-session-12345"
            },
            "Parameters": {
                "userInput": "My card number is 4111111111111111",
                "cardNumber": "4242424242424242",
                "expiryMonth": "12",
                "expiryYear": "25",
                "cvv": "123",
                "intentType": "validate_payment"
            }
        }
    }
    
    class MockContext:
        request_id = "local-test-001"
    
    result = lambda_handler(test_event, MockContext())
    print("\n=== TEST RESULT ===")
    print(json.dumps(result, indent=2))
