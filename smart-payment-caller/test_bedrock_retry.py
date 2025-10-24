"""Test Bedrock with automatic retry for cold start"""
import boto3
import json
import time

MODEL_ARN = "arn:aws:bedrock:us-east-1:875486186130:imported-model/i222wc3dtrqv"

print("🧪 Testing Bedrock Qwen Model (with cold start handling)")
print("=" * 60)
print(f"Model ARN: {MODEL_ARN}")
print("")

bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

prompt = "I want to make a payment of $50.00 using my Visa card ending in 4242."

print("📝 Prompt:", prompt)
print("")

# Try with retries for cold start
max_retries = 3
retry_delay = 20  # seconds

for attempt in range(1, max_retries + 1):
    try:
        print(f"⏳ Attempt {attempt}/{max_retries} - Calling Bedrock...")
        
        body = json.dumps({
            "prompt": prompt,
            "max_tokens": 200,
            "temperature": 0.7
        })
        
        response = bedrock.invoke_model(
            modelId=MODEL_ARN,
            body=body,
            contentType='application/json',
            accept='application/json'
        )
        
        response_body = json.loads(response['body'].read())
        
        print("✅ SUCCESS! Model responded!")
        print("=" * 60)
        print(json.dumps(response_body, indent=2))
        print("=" * 60)
        
        print("\n🎉 BEDROCK TEST PASSED!")
        print("✅ Custom Qwen model is working!")
        print("✅ No Stripe needed for this test!")
        break
        
    except bedrock.exceptions.ModelNotReadyException:
        if attempt < max_retries:
            print(f"⏳ Model warming up... waiting {retry_delay} seconds (cold start)")
            time.sleep(retry_delay)
        else:
            print("❌ Model still not ready after retries")
            print("   This might take up to 60 seconds for first invocation")
            print("   Try running again in a minute")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"\nError type: {type(e).__name__}")
        break
