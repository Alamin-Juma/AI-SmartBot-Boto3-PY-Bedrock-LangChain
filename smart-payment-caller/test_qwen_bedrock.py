"""Quick test of Bedrock Qwen model invocation"""
import boto3
import json

# Your model ARN
MODEL_ARN = "arn:aws:bedrock:us-east-1:875486186130:imported-model/i222wc3dtrqv"

print("🧪 Testing Bedrock Qwen Model Invocation")
print("=" * 60)
print(f"Model ARN: {MODEL_ARN}")
print("")

# Create Bedrock client
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

# Test prompt (payment context with masked card - NO FULL CARD NUMBER!)
prompt = "I want to make a payment of $50.00 using my Visa card ending in 4242."

print("📝 Sending prompt:")
print(f"   '{prompt}'")
print("")

# Invoke model
try:
    print("⏳ Calling Bedrock model...")
    
    # For Qwen models, use simple text format
    body = json.dumps({
        "prompt": prompt,
        "max_tokens": 200,
        "temperature": 0.7,
        "top_p": 0.9
    })
    
    response = bedrock.invoke_model(
        modelId=MODEL_ARN,
        body=body,
        contentType='application/json',
        accept='application/json'
    )
    
    # Parse response
    response_body = json.loads(response['body'].read())
    
    print("✅ Response received!")
    print("=" * 60)
    print(response_body)
    print("=" * 60)
    
    # Extract text if available
    if 'outputs' in response_body:
        print("\n📄 Model Response:")
        for output in response_body['outputs']:
            if 'text' in output:
                print(output['text'])
    elif 'generation' in response_body:
        print("\n📄 Model Response:")
        print(response_body['generation'])
    elif 'response' in response_body:
        print("\n📄 Model Response:")
        print(response_body['response'])
    
    print("\n🎉 Bedrock invocation successful!")
    print("✅ Your custom Qwen model is working!")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nTroubleshooting:")
    print("1. Check model ARN is correct")
    print("2. Verify IAM permissions for bedrock:InvokeModel")
    print("3. Ensure model is in 'Active' state")
    print("\nModel ARN used:")
    print(f"   {MODEL_ARN}")
