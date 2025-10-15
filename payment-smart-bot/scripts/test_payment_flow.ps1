# Payment Smart Bot - Test Script (PowerShell)
# This script runs a complete payment flow test against your deployed API

$ErrorActionPreference = "Stop"

# Get API endpoint from Terraform output
Write-Host "🔍 Getting API endpoint from Terraform..." -ForegroundColor Blue
Push-Location "$PSScriptRoot\..\terraform"
$apiEndpoint = terraform output -raw api_endpoint 2>$null
Pop-Location

if ([string]::IsNullOrEmpty($apiEndpoint)) {
    Write-Host "❌ Error: Could not get API endpoint from Terraform" -ForegroundColor Red
    Write-Host "💡 Make sure you've deployed with: terraform apply" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ API Endpoint: $apiEndpoint" -ForegroundColor Green
Write-Host ""

# Generate unique session ID
$sessionId = "test-$(Get-Date -Format 'yyyyMMddHHmmss')"
Write-Host "📝 Session ID: $sessionId" -ForegroundColor Blue
Write-Host ""

# Helper function to make API calls
function Make-Request {
    param(
        [string]$Message,
        [string]$Step
    )
    
    Write-Host "➤ Step $Step : $Message" -ForegroundColor Yellow
    
    $body = @{
        sessionId = $sessionId
        message = $Message
    } | ConvertTo-Json
    
    try {
        $response = Invoke-RestMethod -Uri $apiEndpoint -Method Post `
            -ContentType "application/json" -Body $body
        
        Write-Host "Bot Response:" -ForegroundColor Green
        Write-Host $response.response
        Write-Host ""
    }
    catch {
        Write-Host "Error: $_" -ForegroundColor Red
        Write-Host $_.Exception.Response.StatusCode.value__
    }
    
    # Wait between requests
    Start-Sleep -Seconds 2
}

Write-Host "🤖 Starting Payment Flow Test..." -ForegroundColor Blue
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Blue
Write-Host ""

# Test flow
Make-Request "I need to make a payment" "1/6"
Make-Request "Jane Doe" "2/6"
Make-Request "4242424242424242" "3/6"
Make-Request "12/27" "4/6"
Make-Request "456" "5/6"
Make-Request "confirm" "6/6"

Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Blue
Write-Host "✅ Test flow completed!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 Expected behavior:" -ForegroundColor Yellow
Write-Host "  - Steps 1-5: Bot collects payment information"
Write-Host "  - Step 6: Bot shows Stripe validation error (raw cards blocked in test mode)"
Write-Host ""
Write-Host "💡 This is expected! In production:" -ForegroundColor Yellow
Write-Host "  - Use Stripe Elements on frontend to tokenize cards"
Write-Host "  - Send token to backend (not raw card number)"
Write-Host ""
Write-Host "📚 View logs:" -ForegroundColor Blue
Write-Host "  aws logs tail /aws/lambda/payment-smart-bot-handler-dev --since 5m"
Write-Host ""
Write-Host "🔍 Check DynamoDB session:" -ForegroundColor Blue
Write-Host "  aws dynamodb get-item \"
Write-Host "    --table-name payment-smart-bot-sessions-dev \"
Write-Host "    --key '{`"sessionId`": {`"S`": `"$sessionId`"}}'"
Write-Host ""
