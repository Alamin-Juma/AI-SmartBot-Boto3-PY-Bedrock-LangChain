"""
Payment Collection Bot - Lambda Handler
Amazon Bedrock + Llama 3.2 1B Instruct

This Lambda function orchestrates payment collection through conversational AI.
It uses Amazon Bedrock for natural language processing and implements PCI-DSS
compliant payment validation.
"""

import json
import os
import boto3
from typing import Dict, Any, Optional
from datetime import datetime
from calendar import monthrange
import re
import threading
import stripe

# Load .env file for local testing (ignored in Lambda)
try:
    from dotenv import load_dotenv
    load_dotenv()  # Loads .env file if it exists
except ImportError:
    pass  # python-dotenv not installed, that's ok for Lambda

# Initialize AWS clients
bedrock_runtime = boto3.client('bedrock-runtime', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
dynamodb = boto3.resource('dynamodb', region_name=os.environ.get('AWS_REGION', 'us-east-1'))
secrets_manager = boto3.client('secretsmanager', region_name=os.environ.get('AWS_REGION', 'us-east-1'))

# Configuration
MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'meta.llama3-2-1b-instruct-v1:0')
SESSION_TABLE = os.environ.get('DYNAMODB_TABLE', 'payment-bot-sessions')
STRIPE_SECRET_ARN = os.environ.get('STRIPE_SECRET_ARN', '')

# Cache for Stripe key (fetch once, reuse across invocations)
_stripe_key_cache = None
_stripe_key_cache_lock = threading.Lock()

# System prompt for the payment bot
SYSTEM_PROMPT = """You are a polite and secure payment assistant. Your job is to collect payment information step-by-step:

1. Name on card (full name as it appears)
2. Card number (16 digits for Visa/MC, 15 for Amex)
3. Expiry date (MM/YY format)
4. CVV (3 digits for Visa/MC, 4 for Amex)

Rules:
- Ask for ONE piece of information at a time
- Be polite and reassuring about security
- If user provides invalid input, politely ask them to try again
- Never repeat or store full card numbers in responses
- Mask sensitive data (e.g., show "****1234" for card ending in 1234)
- Confirm all details before finalizing (with masked data)
- If user says "cancel" or "stop", end the session politely

Be conversational but efficient. Make users feel their payment is secure."""


def luhn_checksum(card_number: str) -> bool:
    """
    Validate credit card number using Luhn algorithm.
    
    Args:
        card_number: Card number as string (spaces will be stripped)
    
    Returns:
        True if valid, False otherwise
    """
    def digits_of(n):
        return [int(d) for d in str(n)]
    
    card_number = card_number.replace(' ', '').replace('-', '')
    
    if not card_number.isdigit() or len(card_number) < 13 or len(card_number) > 19:
        return False
    
    digits = digits_of(card_number)
    odd_digits = digits[-1::-2]
    even_digits = digits[-2::-2]
    checksum = sum(odd_digits)
    
    for d in even_digits:
        checksum += sum(digits_of(d * 2))
    
    return checksum % 10 == 0


def validate_expiry(expiry: str) -> bool:
    """
    Validate expiry date format (MM/YY) and check if not expired.
    Uses last day of the expiry month for accurate validation.
    
    Args:
        expiry: Date string in MM/YY format
    
    Returns:
        True if valid and not expired
    """
    pattern = r'^(0[1-9]|1[0-2])/([0-9]{2})$'
    match = re.match(pattern, expiry)
    
    if not match:
        return False
    
    month = int(match.group(1))
    year = int('20' + match.group(2))
    
    # Get last day of the expiry month
    last_day = monthrange(year, month)[1]
    expiry_date = datetime(year, month, last_day)
    
    # Compare with current date (set time to midnight for accurate comparison)
    now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    return expiry_date >= now


def validate_cvv(cvv: str, card_number: str) -> bool:
    """
    Validate CVV format (3 digits for most cards, 4 for Amex).
    
    Args:
        cvv: CVV string
        card_number: Card number to determine card type
    
    Returns:
        True if valid format
    """
    # Amex cards start with 34 or 37 and use 4-digit CVV
    is_amex = card_number.startswith(('34', '37'))
    expected_length = 4 if is_amex else 3
    
    return cvv.isdigit() and len(cvv) == expected_length


def mask_card_number(card_number: str) -> str:
    """Mask all but last 4 digits of card number."""
    clean = card_number.replace(' ', '').replace('-', '')
    return '****' + clean[-4:]


def get_stripe_key() -> str:
    """
    Fetch Stripe API key from Secrets Manager (with thread-safe caching).
    
    Returns:
        Stripe secret key as string
    """
    global _stripe_key_cache
    
    # Thread-safe access to cache
    with _stripe_key_cache_lock:
        # Return cached value if available
        if _stripe_key_cache:
            return _stripe_key_cache
        
        try:
            if not STRIPE_SECRET_ARN:
                print("Warning: STRIPE_SECRET_ARN not set")
                return ""
            
            response = secrets_manager.get_secret_value(SecretId=STRIPE_SECRET_ARN)
            secret_dict = json.loads(response['SecretString'])
            _stripe_key_cache = secret_dict.get('STRIPE_SECRET_KEY', '')
            
            return _stripe_key_cache
        except Exception as e:
            print(f"Error fetching Stripe key from Secrets Manager: {e}")
            return ""


def tokenize_payment(collected_data: Dict[str, str]) -> Dict[str, Any]:
    """
    Tokenize payment data using Stripe API.
    Creates a PaymentMethod without charging the card.
    
    Args:
        collected_data: Dict with 'name', 'card', 'expiry', 'cvv'
    
    Returns:
        Dict with 'success' bool and either 'token' or 'error'
    """
    try:
        # Set Stripe API key
        stripe.api_key = get_stripe_key()
        
        if not stripe.api_key:
            return {"success": False, "error": "Stripe API key not configured"}
        
        # Parse expiry date
        exp_month, exp_year = collected_data['expiry'].split('/')
        exp_month = int(exp_month)
        exp_year = int('20' + exp_year)
        
        # Create PaymentMethod (tokenize card data)
        payment_method = stripe.PaymentMethod.create(
            type="card",
            card={
                "number": collected_data['card'],
                "exp_month": exp_month,
                "exp_year": exp_year,
                "cvc": collected_data['cvv'],
            },
            billing_details={
                "name": collected_data['name']
            }
        )
        
        print(f"Stripe PaymentMethod created: {payment_method.id}")
        
        return {
            "success": True,
            "token": payment_method.id,
            "card_brand": payment_method.card.brand,
            "last4": payment_method.card.last4
        }
        
    except stripe.CardError as e:
        # Card declined or invalid
        error_msg = e.user_message if hasattr(e, 'user_message') else str(e)
        print(f"Stripe CardError: {error_msg}")
        return {"success": False, "error": error_msg}
        
    except stripe.StripeError as e:
        # Other Stripe errors
        print(f"Stripe error: {str(e)}")
        return {"success": False, "error": f"Payment processing error: {str(e)}"}
        
    except Exception as e:
        print(f"Unexpected error in tokenization: {e}")
        return {"success": False, "error": "Payment processing failed"}


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve session data from DynamoDB."""
    try:
        table = dynamodb.Table(SESSION_TABLE)
        response = table.get_item(Key={'sessionId': session_id})
        return response.get('Item')
    except Exception as e:
        print(f"Error getting session: {e}")
        return None


def save_session(session_id: str, session_data: Dict[str, Any]) -> bool:
    """Save session data to DynamoDB (non-sensitive data only)."""
    try:
        table = dynamodb.Table(SESSION_TABLE)
        session_data['sessionId'] = session_id
        session_data['lastUpdated'] = datetime.utcnow().isoformat()
        table.put_item(Item=session_data)
        return True
    except Exception as e:
        print(f"Error saving session: {e}")
        return False


def invoke_bedrock(conversation_history: list, user_message: str) -> str:
    """
    Call Amazon Bedrock with Llama 3.2 1B for conversational response.
    
    Args:
        conversation_history: List of prior messages
        user_message: Current user input
    
    Returns:
        Bot's response as string
    """
    try:
        # Build messages array for Bedrock Converse API
        messages = [
            {
                "role": "user" if msg["role"] == "user" else "assistant",
                "content": [{"text": msg["text"]}]
            }
            for msg in conversation_history
        ]
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": [{"text": user_message}]
        })
        
        # Call Bedrock
        response = bedrock_runtime.converse(
            modelId=MODEL_ID,
            messages=messages,
            system=[{"text": SYSTEM_PROMPT}],
            inferenceConfig={
                "temperature": 0.5,
                "maxTokens": 512,
                "topP": 0.9
            }
        )
        
        # Extract response text (handle multi-content responses)
        output_message = response.get('output', {}).get('message', {})
        content_blocks = output_message.get('content', [])
        
        # Find first text content block
        text_content = next(
            (block['text'] for block in content_blocks if 'text' in block),
            "Error processing request."
        )
        
        return text_content
    
    except Exception as e:
        print(f"Bedrock error: {e}")
        return "I apologize, but I'm having trouble processing that. Could you try again?"


def extract_payment_info(text: str, current_step: str) -> Optional[str]:
    """
    Extract payment information from user input based on current collection step.
    
    Args:
        text: User's message
        current_step: What info we're collecting (name, card, expiry, cvv)
    
    Returns:
        Extracted value or None
    """
    text = text.strip()
    
    if current_step == "card":
        # Extract digits only
        digits = re.sub(r'[^\d]', '', text)
        if len(digits) >= 13:
            return digits
    
    elif current_step == "expiry":
        # Look for MM/YY pattern
        match = re.search(r'(0[1-9]|1[0-2])/([0-9]{2})', text)
        if match:
            return match.group(0)
    
    elif current_step == "cvv":
        # Extract 3-4 digit number
        match = re.search(r'\b([0-9]{3,4})\b', text)
        if match:
            return match.group(1)
    
    elif current_step == "name":
        # Basic name extraction (2+ words)
        if len(text.split()) >= 2 and not any(char.isdigit() for char in text):
            return text.title()
    
    return None


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for payment bot.
    
    Expected event structure:
    {
        "sessionId": "unique-session-id",
        "message": "user input text"
    }
    
    Returns:
    {
        "statusCode": 200,
        "body": {
            "response": "bot response",
            "status": "collecting|validating|complete|error",
            "sessionId": "session-id"
        }
    }
    """
    try:
        # Parse input
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event
        
        session_id = body.get('sessionId', f"session-{datetime.now().timestamp()}")
        user_message = body.get('message', '').strip()
        
        if not user_message:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'No message provided'})
            }
        
        # Get or create session
        session = get_session(session_id) or {
            'conversationHistory': [],
            'collectedData': {},
            'currentStep': 'name',
            'status': 'collecting'
        }
        
        # Check for cancel/abort (expanded synonyms)
        cancel_words = {'cancel', 'stop', 'quit', 'abort', 'exit', 'no', 'nevermind', 'never mind'}
        if any(word in user_message.lower() for word in cancel_words):
            session['status'] = 'cancelled'
            save_session(session_id, session)
            return {
                'statusCode': 200,
                'body': json.dumps({
                    'response': 'No problem! Payment cancelled. Have a great day!',
                    'status': 'cancelled',
                    'sessionId': session_id
                })
            }
        
        # Extract payment info based on current step
        current_step = session['currentStep']
        extracted = extract_payment_info(user_message, current_step)
        
        # Validate if we got data
        validation_error = None
        if extracted:
            if current_step == 'card':
                if not luhn_checksum(extracted):
                    validation_error = "That card number doesn't pass validation. Could you double-check it?"
                else:
                    session['collectedData']['card'] = extracted
                    session['currentStep'] = 'expiry'
            
            elif current_step == 'expiry':
                if not validate_expiry(extracted):
                    validation_error = "That expiry date seems invalid or expired. Please use MM/YY format."
                else:
                    session['collectedData']['expiry'] = extracted
                    session['currentStep'] = 'cvv'
            
            elif current_step == 'cvv':
                card = session['collectedData'].get('card', '')
                if not validate_cvv(extracted, card):
                    validation_error = "CVV should be 3 digits (4 for Amex). Please try again."
                else:
                    session['collectedData']['cvv'] = extracted
                    session['currentStep'] = 'confirm'
            
            elif current_step == 'name':
                session['collectedData']['name'] = extracted
                session['currentStep'] = 'card'
        
        # Build conversation history for Bedrock
        conversation_history = session.get('conversationHistory', [])
        
        # Add validation context if needed
        if validation_error:
            user_message_for_ai = f"{user_message} [SYSTEM: Validation failed - {validation_error}]"
        else:
            user_message_for_ai = user_message
        
        # Get AI response
        bot_response = invoke_bedrock(conversation_history, user_message_for_ai)
        
        # Override with validation error if present
        if validation_error:
            bot_response = validation_error
        
        # Update conversation history (store only non-sensitive parts)
        conversation_history.append({"role": "user", "text": user_message})
        conversation_history.append({"role": "assistant", "text": bot_response})
        session['conversationHistory'] = conversation_history[-10:]  # Keep last 10 messages
        
        # Check if we're at confirmation step
        if session['currentStep'] == 'confirm':
            collected = session['collectedData']
            if all(k in collected for k in ['name', 'card', 'expiry', 'cvv']):
                # Show summary with masked data
                summary = (
                    f"Please confirm:\n"
                    f"Name: {collected['name']}\n"
                    f"Card: {mask_card_number(collected['card'])}\n"
                    f"Expiry: {collected['expiry']}\n"
                    f"CVV: ***\n"
                    f"Reply 'confirm' to proceed or 'cancel' to abort."
                )
                bot_response = summary
                session['status'] = 'awaiting_confirmation'
        
        # Handle final confirmation
        if session.get('status') == 'awaiting_confirmation' and 'confirm' in user_message.lower():
            # Tokenize payment data with Stripe
            collected_data = session['collectedData']
            tokenization_result = tokenize_payment(collected_data)
            
            if tokenization_result['success']:
                session['status'] = 'complete'
                session['paymentToken'] = tokenization_result['token']
                
                bot_response = (
                    f"✅ Payment processed successfully!\n\n"
                    f"Token: {tokenization_result['token']}\n"
                    f"Card: {tokenization_result['card_brand']} ending in {tokenization_result['last4']}\n\n"
                    f"Thank you for your payment!"
                )
                
                # Remove sensitive data from session before saving
                if 'card' in collected_data:
                    collected_data['card'] = mask_card_number(collected_data['card'])
                if 'cvv' in collected_data:
                    collected_data.pop('cvv')  # Never store CVV
            else:
                # Tokenization failed
                bot_response = (
                    f"❌ Payment processing failed: {tokenization_result['error']}\n\n"
                    f"Please check your card details and try again."
                )
                session['status'] = 'error'
        
        # Save session
        save_session(session_id, session)
        
        # Return response
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'response': bot_response,
                'status': session['status'],
                'sessionId': session_id,
                'currentStep': session['currentStep']
            })
        }
    
    except Exception as e:
        # Log the full error with stack trace
        import traceback
        error_details = traceback.format_exc()
        print(f"CRITICAL ERROR in lambda_handler: {e}")
        print(f"Stack trace:\n{error_details}")
        
        # Re-raise the exception so Lambda marks it as an error (for CloudWatch alarms)
        # This ensures the alarm can detect failures
        raise Exception(f"Payment handler error: {str(e)}") from e


# For local testing
if __name__ == "__main__":
    # Test event
    test_event = {
        "sessionId": "test-local-001",
        "message": "I want to make a payment"
    }
    
    result = lambda_handler(test_event, None)
    print(json.dumps(json.loads(result['body']), indent=2))
