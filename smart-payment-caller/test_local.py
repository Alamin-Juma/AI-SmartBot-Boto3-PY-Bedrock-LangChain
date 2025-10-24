"""
Direct test script for Lambda function - No SAM required
This script tests the payment handler directly without deploying
"""

import sys
import json
from pathlib import Path

# Add src to path so we can import the Lambda handler
sys.path.insert(0, str(Path(__file__).parent / 'src'))

# Import the Lambda handler
from lambda_handler import lambda_handler

class MockContext:
    """Mock Lambda context for local testing"""
    def __init__(self):
        self.request_id = "local-test-001"
        self.function_name = "payment-bot-handler-local"
        self.memory_limit_in_mb = 512
        self.invoked_function_arn = "arn:aws:lambda:local:test:function:payment-bot-handler"

def test_payment_validation():
    """Test payment validation with Stripe test card"""
    
    # Load test event
    with open('events/test-event.json', 'r') as f:
        event = json.load(f)
    
    print("=" * 70)
    print("🧪 Testing Payment Bot Lambda Handler")
    print("=" * 70)
    print()
    print("📋 Test Event:")
    print(json.dumps(event, indent=2))
    print()
    print("-" * 70)
    print("🚀 Invoking Lambda Handler...")
    print("-" * 70)
    print()
    
    # Create mock context
    context = MockContext()
    
    # Invoke the handler
    try:
        response = lambda_handler(event, context)
        
        print()
        print("=" * 70)
        print("✅ Lambda Execution Complete!")
        print("=" * 70)
        print()
        print("📤 Response:")
        print(json.dumps(response, indent=2))
        print()
        
        # Validation checks
        print("-" * 70)
        print("🔍 Validation Checks:")
        print("-" * 70)
        
        checks = {
            "Status Code": response.get('statusCode') == 200,
            "Response Text": bool(response.get('response')),
            "PCI Compliant": response.get('metadata', {}).get('pci_compliant') == True,
            "CHD Masked": response.get('metadata', {}).get('chd_masked') == True,
            "Stripe Token": bool(response.get('stripeToken')),
            "Card Brand": bool(response.get('cardBrand')),
            "Last 4 Digits": bool(response.get('last4'))
        }
        
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"{status} {check}: {passed}")
        
        print()
        
        if all(checks.values()):
            print("=" * 70)
            print("🎉 ALL TESTS PASSED! Payment bot is working correctly.")
            print("=" * 70)
            return 0
        else:
            print("=" * 70)
            print("⚠️  Some tests failed. Check the output above.")
            print("=" * 70)
            return 1
            
    except Exception as e:
        print()
        print("=" * 70)
        print("❌ Lambda Execution Failed!")
        print("=" * 70)
        print()
        print(f"Error Type: {type(e).__name__}")
        print(f"Error Message: {str(e)}")
        print()
        
        # Common error messages
        if "stripe" in str(e).lower():
            print("💡 Stripe Error - Possible causes:")
            print("   1. Stripe API key not set in AWS SSM Parameter Store")
            print("   2. Invalid Stripe API key")
            print("   3. Stripe API connectivity issue")
            print()
            print("   Fix: Run this command to set your Stripe key:")
            print('   aws ssm put-parameter \\')
            print('     --name "/payment-bot/stripe-secret" \\')
            print('     --value "sk_test_YOUR_KEY" \\')
            print('     --type SecureString')
            print()
        
        elif "bedrock" in str(e).lower():
            print("💡 Bedrock Error - Possible causes:")
            print("   1. Bedrock model access not enabled")
            print("   2. Region doesn't support Bedrock")
            print("   3. IAM permissions missing")
            print()
            print("   Fix: Enable Bedrock model access:")
            print("   https://console.aws.amazon.com/bedrock/")
            print()
        
        elif "parameter" in str(e).lower() and "not found" in str(e).lower():
            print("💡 SSM Parameter Not Found")
            print("   The Stripe API key is not stored in AWS.")
            print()
            print("   Fix: Store your Stripe test key:")
            print('   aws ssm put-parameter \\')
            print('     --name "/payment-bot/stripe-secret" \\')
            print('     --value "sk_test_YOUR_KEY" \\')
            print('     --type SecureString')
            print()
        
        import traceback
        print("📋 Full Traceback:")
        traceback.print_exc()
        print()
        return 1

if __name__ == "__main__":
    print()
    print("🔧 Payment Bot - Direct Lambda Test")
    print("   (No SAM CLI or Docker required)")
    print()
    
    # Check if test event exists
    if not Path('events/test-event.json').exists():
        print("❌ Error: events/test-event.json not found")
        print("   Make sure you're running this from the smart-payment-caller directory")
        sys.exit(1)
    
    # Run the test
    exit_code = test_payment_validation()
    sys.exit(exit_code)
