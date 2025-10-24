"""
Offline test script - Tests CHD masking without AWS dependencies
"""

import sys
import json
import re
from pathlib import Path

def mask_card_number(card: str) -> tuple:
    """Test the card masking function"""
    clean_card = re.sub(r'[^0-9]', '', card)
    if len(clean_card) < 13 or len(clean_card) > 19:
        return "****INVALID****", "0000"
    last4 = clean_card[-4:]
    masked = "*" * (len(clean_card) - 4) + last4
    return masked, last4

def test_masking():
    """Test CHD masking functionality"""
    print("=" * 70)
    print("🧪 Testing PCI Compliance - CHD Masking")
    print("=" * 70)
    print()
    
    test_cards = {
        "Visa": "4242424242424242",
        "Visa Declined": "4000000000009995",
        "Mastercard": "5555555555554444",
        "Amex": "378282246310005",
        "Invalid": "1234567890"
    }
    
    all_passed = True
    
    for card_type, card_number in test_cards.items():
        masked, last4 = mask_card_number(card_number)
        
        # Check that full number is NOT in masked result
        passed = card_number not in masked
        status = "✅" if passed else "❌"
        
        print(f"{status} {card_type:20} {card_number:20} → {masked}")
        
        if not passed:
            all_passed = False
    
    print()
    print("-" * 70)
    print("🔍 Security Validation:")
    print("-" * 70)
    
    # Create test logs with all masked cards
    test_logs = [f"Processing payment for card {mask_card_number(card)[0]}" 
                 for card in test_cards.values()]
    combined_log = " ".join(test_logs)
    
    # Get a valid masked result for format check
    valid_masked = mask_card_number("4242424242424242")[0]
    valid_last4 = mask_card_number("4242424242424242")[1]
    
    checks = {
        "No full card numbers in logs": all(card not in combined_log for card in test_cards.values()),
        "Last 4 digits preserved": valid_last4 in valid_masked,
        "Asterisk masking used": "*" in valid_masked,
        "Card length preserved": len(valid_masked) == 16,
    }
    
    for check, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check}")
        all_passed = all_passed and passed
    
    print()
    
    if all_passed and all(checks.values()):
        print("=" * 70)
        print("🎉 PCI COMPLIANCE CHECK PASSED!")
        print("   CHD masking is working correctly.")
        print("=" * 70)
        return 0
    else:
        print("=" * 70)
        print("⚠️  COMPLIANCE ISSUE DETECTED")
        print("=" * 70)
        return 1

def show_next_steps():
    """Show what needs to be done next"""
    print()
    print("=" * 70)
    print("📋 Next Steps to Complete Testing")
    print("=" * 70)
    print()
    print("1️⃣  Store Stripe API Key in AWS:")
    print()
    print("    aws ssm put-parameter \\")
    print('      --name "/payment-bot/stripe-secret" \\')
    print('      --value "sk_test_YOUR_STRIPE_KEY" \\')
    print("      --type SecureString \\")
    print("      --region us-east-1")
    print()
    print("    Get your key from: https://dashboard.stripe.com/test/apikeys")
    print()
    print("2️⃣  Enable Bedrock Mistral 7B:")
    print()
    print("    • Go to: https://console.aws.amazon.com/bedrock/")
    print("    • Click 'Model access' → 'Manage model access'")
    print("    • Enable 'Mistral 7B Instruct'")
    print("    • Wait 2-5 minutes for approval")
    print()
    print("3️⃣  Deploy Infrastructure with SAM:")
    print()
    print("    sam build")
    print("    sam deploy --guided")
    print()
    print("    Or use the deployment script:")
    print("    bash deploy.sh")
    print()
    print("=" * 70)
    print()

if __name__ == "__main__":
    print()
    print("🔧 Payment Bot - Offline CHD Masking Test")
    print("   (No AWS credentials required)")
    print()
    
    exit_code = test_masking()
    
    if exit_code == 0:
        show_next_steps()
    
    sys.exit(exit_code)
