# 🚀 Payment Smart Bot - Command Reference

Quick copy-paste commands for running the Payment Smart Bot.

## ✨ Quick Run Command

```bash
cd /c/dev/personal/AI-SmartBots-Boto3-Bedrock-LLMs/payment-smart-bot/frontend && C:/Users/User/AppData/Local/Microsoft/WindowsApps/python3.13.exe -m streamlit run payment_bot_frontend.py
```

**Open in browser:** `http://localhost:8501`

---

## 📋 Step-by-Step Commands

### 1. Navigate to Frontend
```bash
cd /c/dev/personal/AI-SmartBots-Boto3-Bedrock-LLMs/payment-smart-bot/frontend
```

### 2. Run Streamlit
```bash
C:/Users/User/AppData/Local/Microsoft/WindowsApps/python3.13.exe -m streamlit run payment_bot_frontend.py
```

### 3. Open Browser
```
http://localhost:8501
```

### 4. Configure API (in sidebar)
```
https://osmgkvun82.execute-api.us-east-1.amazonaws.com/dev/chat
```

---

## 🧪 Test Payment Flow

Use these test values in the conversation:

```
Name:         John Smith
Card Number:  4242424242424242
Expiry:       12/25
CVV:          123
Confirm:      confirm
```

---

## 🛠️ Useful Commands

### Check Backend Status
```bash
cd /c/dev/personal/AI-SmartBots-Boto3-Bedrock-LLMs/payment-smart-bot/terraform
terraform output api_endpoint
```

### Test Backend API
```bash
curl -X POST 'https://osmgkvun82.execute-api.us-east-1.amazonaws.com/dev/chat' \
  -H 'Content-Type: application/json' \
  -d '{"sessionId":"test-001","message":"Hi"}'
```

### View Lambda Logs
```bash
aws logs tail /aws/lambda/payment-smart-bot-handler-dev --follow
```

### Check Terraform State
```bash
cd /c/dev/personal/AI-SmartBots-Boto3-Bedrock-LLMs/payment-smart-bot/terraform
terraform state list
```

---

## 🔄 Restart Frontend

### Stop (Ctrl+C in terminal where Streamlit is running)

### Start
```bash
cd /c/dev/personal/AI-SmartBots-Boto3-Bedrock-LLMs/payment-smart-bot/frontend && C:/Users/User/AppData/Local/Microsoft/WindowsApps/python3.13.exe -m streamlit run payment_bot_frontend.py
```

---

## 📦 Install Dependencies (if needed)

```bash
cd /c/dev/personal/AI-SmartBots-Boto3-Bedrock-LLMs/payment-smart-bot/frontend
C:/Users/User/AppData/Local/Microsoft/WindowsApps/python3.13.exe -m pip install -r requirements.txt
```

---

## 🐛 Troubleshooting Commands

### Check Python Version
```bash
C:/Users/User/AppData/Local/Microsoft/WindowsApps/python3.13.exe --version
```

### Check Streamlit Installation
```bash
C:/Users/User/AppData/Local/Microsoft/WindowsApps/python3.13.exe -m pip list | grep streamlit
```

### View .env Configuration
```bash
cd /c/dev/personal/AI-SmartBots-Boto3-Bedrock-LLMs/payment-smart-bot/frontend
cat .env
```

### Check if Streamlit is Running
```bash
netstat -ano | grep 8501
# or
curl http://localhost:8501/_stcore/health
```

---

## 💡 Pro Tips

**Alias for Quick Launch (add to ~/.bashrc):**
```bash
alias payment-bot='cd /c/dev/personal/AI-SmartBots-Boto3-Bedrock-LLMs/payment-smart-bot/frontend && C:/Users/User/AppData/Local/Microsoft/WindowsApps/python3.13.exe -m streamlit run payment_bot_frontend.py'
```

Then just type: `payment-bot`

**Background Mode:**
```bash
cd /c/dev/personal/AI-SmartBots-Boto3-Bedrock-LLMs/payment-smart-bot/frontend
nohup C:/Users/User/AppData/Local/Microsoft/WindowsApps/python3.13.exe -m streamlit run payment_bot_frontend.py &
```

---

**Quick Reference Card - Save this for easy access!** 📌
