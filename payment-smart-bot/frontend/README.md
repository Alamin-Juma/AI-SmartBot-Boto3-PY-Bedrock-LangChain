# 💳 Payment Smart Bot Frontend

Beautiful, secure, and PCI-DSS compliant Streamlit frontend for the Payment Smart Bot.

## ✨ Features

### 🎨 User Interface
- **Modern Design**: Gradient colors, smooth animations, professional styling
- **Responsive Layout**: Works on desktop, tablet, and mobile
- **Real-time Chat**: Conversational payment collection with AI bot
- **Progress Tracking**: Visual progress bar showing payment flow completion
- **Status Indicators**: Clear status badges (Collecting, Confirming, Completed, Error)

### 🔐 Security & Compliance
- **PCI-DSS Compliant UI**: No raw card data storage
- **Security Banner**: Clear security indicators for user confidence
- **HTTPS Only**: Secure communication
- **Session Management**: Unique session IDs with auto-expiry
- **Ready for Stripe Elements**: Infrastructure for tokenized payments

### 🚀 User Experience
- **Quick Start Buttons**: One-click conversation starters
- **Test Mode Toggle**: Easy switch between test and production
- **Session Info**: Real-time session metrics and progress
- **Copy Session ID**: Easy session tracking
- **Clear History**: Start fresh conversations anytime

## 📦 Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager
- Deployed Payment Smart Bot API (see main project README)

### Step 1: Install Dependencies

```bash
cd payment-smart-bot/frontend
pip install -r requirements.txt
```

### Step 2: Configure API Endpoint

**Option A: Environment Variable (Recommended)**

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your API endpoint
nano .env
```

Add:
```env
PAYMENT_BOT_API_ENDPOINT=https://osmgkvun82.execute-api.us-east-1.amazonaws.com/dev/chat
```

**Option B: Configure in UI**

You can also configure the API endpoint directly in the sidebar when running the app.

### Step 3: Run the Application

**For Windows (Git Bash):**
```bash
cd /c/dev/personal/AI-SmartBots-Boto3-Bedrock-LLMs/payment-smart-bot/frontend
C:/Users/User/AppData/Local/Microsoft/WindowsApps/python3.13.exe -m streamlit run payment_bot_frontend.py
```

**For Linux/Mac:**
```bash
streamlit run payment_bot_frontend.py
```

The app will open in your browser at `http://localhost:8501`

## 🎯 Usage

### Starting a Conversation

1. **Quick Start**: Click one of the quick start buttons:
   - 💳 Make a Payment
   - 🔍 Check Payment Status
   - ❓ Get Help

2. **Manual Start**: Type your message in the chat input

### Payment Flow

The bot will guide you through:
1. **Greeting**: Introduction and payment initiation
2. **Name Collection**: Secure name capture
3. **Card Number**: Conversational card collection
4. **Expiration Date**: Month and year collection
5. **CVV**: Security code collection
6. **Confirmation**: Review and final confirmation

### Test Mode

Enable test mode in the sidebar to use Stripe test cards:

```
Card Number: 4242 4242 4242 4242
Expiry: Any future date (e.g., 12/25)
CVV: Any 3 digits (e.g., 123)
```

### Session Management

- **Session ID**: Unique identifier displayed in sidebar
- **Progress**: Visual progress bar (0-100%)
- **New Session**: Click "🔄 New Session" to start fresh
- **Copy ID**: Click "📋 Copy Session ID" to copy for tracking

## 🏗️ Architecture

### Component Structure

```
payment_bot_frontend.py
├── Configuration
│   ├── Streamlit page config
│   ├── Custom CSS styling
│   └── Environment variables
│
├── Session State
│   ├── messages: Chat history
│   ├── session_id: Unique session identifier
│   ├── payment_status: Current status
│   └── api_endpoint: API Gateway URL
│
├── Helper Functions
│   ├── send_message(): API communication
│   ├── get_status_badge(): Status UI
│   ├── get_progress_percentage(): Progress calculation
│   ├── display_security_banner(): Security indicators
│   └── display_message(): Chat message rendering
│
└── Main UI
    ├── Header with PCI badge
    ├── Security banner
    ├── Sidebar (config, status, actions)
    ├── Quick start buttons
    ├── Chat messages display
    ├── Chat input
    └── Footer
```

### API Communication

The frontend communicates with the Payment Smart Bot Lambda via API Gateway:

**Request:**
```json
{
  "sessionId": "550e8400-e29b-41d4-a716-446655440000",
  "message": "I want to make a payment"
}
```

**Response:**
```json
{
  "response": "Great! I'll help you with that. What's your name?",
  "sessionId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "collecting"
}
```

## 🎨 Customization

### Styling

Edit the CSS in `payment_bot_frontend.py` to customize:
- Color scheme (currently purple gradient)
- Font sizes and families
- Animation timings
- Component layouts

Example: Change primary color:
```css
/* From purple gradient */
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

/* To blue gradient */
background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
```

### Branding

Replace these elements:
- Page title: `st.set_page_config(page_title="Your Brand")`
- Logo: Add your logo in sidebar
- Footer: Update footer text and links
- Stripe branding: Customize or remove powered-by section

## 🔧 Configuration Options

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `PAYMENT_BOT_API_ENDPOINT` | API Gateway URL | `https://abc123.execute-api.us-east-1.amazonaws.com/dev/chat` |
| `STRIPE_PUBLISHABLE_KEY` | Stripe public key (future) | `pk_test_...` |

### Streamlit Configuration

Create `.streamlit/config.toml`:

```toml
[theme]
primaryColor = "#667eea"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f8f9fa"
textColor = "#2d3748"
font = "sans serif"

[server]
port = 8501
enableCORS = true
enableXsrfProtection = true

[browser]
gatherUsageStats = false
```

## 🔐 Security Best Practices

### Implemented Security Features

✅ **No Raw Card Storage**: All card data sent directly to backend
✅ **HTTPS Only**: Secure communication
✅ **Session Isolation**: Unique session IDs
✅ **Input Validation**: Client-side validation before API calls
✅ **XSS Prevention**: Streamlit's built-in protections
✅ **CSRF Protection**: Enabled in Streamlit config

### Future Enhancements

- [ ] Stripe Elements integration for PCI-compliant card input
- [ ] Rate limiting on frontend
- [ ] Biometric authentication
- [ ] 3D Secure (3DS) support
- [ ] Multi-factor authentication

## 🚀 Deployment

### Local Development

```bash
streamlit run payment_bot_frontend.py --server.port 8501
```

### Production Deployment

**Option 1: Streamlit Cloud**

1. Push code to GitHub
2. Connect to [Streamlit Cloud](https://streamlit.io/cloud)
3. Add secrets in dashboard (API endpoint)
4. Deploy

**Option 2: Docker**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY payment_bot_frontend.py .
COPY .env .

EXPOSE 8501

CMD ["streamlit", "run", "payment_bot_frontend.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

Build and run:
```bash
docker build -t payment-bot-frontend .
docker run -p 8501:8501 payment-bot-frontend
```

**Option 3: AWS (EC2 or ECS)**

See main project documentation for AWS deployment guides.

## 📊 Monitoring

### Session Metrics

Track in sidebar:
- Session ID
- Message count
- Current status
- Progress percentage

### API Health

Monitor:
- Response times
- Error rates
- Success rates
- API availability

### User Analytics

Optional integrations:
- Google Analytics
- Mixpanel
- Amplitude
- Custom metrics

## 🐛 Troubleshooting

### Common Issues

**Issue: "API endpoint not configured"**
```
Solution: Add API endpoint in sidebar or .env file
```

**Issue: "Request timed out"**
```
Solution: 
1. Check API Gateway is running
2. Verify Lambda is not cold starting
3. Increase timeout in send_message() function
```

**Issue: "Invalid response from server"**
```
Solution:
1. Verify API endpoint URL is correct
2. Check API Gateway CORS configuration
3. Review Lambda function logs in CloudWatch
```

**Issue: Styling not displaying**
```
Solution:
1. Clear browser cache
2. Check st.markdown unsafe_allow_html=True
3. Verify CSS syntax in custom styles
```

### Debug Mode

Enable Streamlit debug mode:

```bash
streamlit run payment_bot_frontend.py --logger.level=debug
```

Or in `.streamlit/config.toml`:

```toml
[logger]
level = "debug"
```

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is part of AI-SmartBots-Boto3-Bedrock-LLMs.

## 🔗 Related Documentation

- [Main Project README](../../README.md)
- [Deployment Guide](../docs/DEPLOYMENT_GUIDE.md)
- [API Documentation](../docs/API_DOCUMENTATION.md)
- [Troubleshooting](../docs/TROUBLESHOOTING.md)

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/Alamin-Juma/AI-SmartBot-Boto3-PY-Bedrock-LangChain/issues)
- **Documentation**: [Project Docs](../docs/)
- **Discussions**: [GitHub Discussions](https://github.com/Alamin-Juma/AI-SmartBot-Boto3-PY-Bedrock-LangChain/discussions)

---

**Built with ❤️ using Streamlit, AWS Bedrock, and Stripe**
