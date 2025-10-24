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

# Test prompt (payment context with masked card)
prompt = """You are a helpful payment assistant. 

User: I want to make a payment of $50.00 using my Visa card ending in 4242.