"""
Payment Smart Bot - Secure Frontend with Streamlit
PCI-DSS Compliant Payment Collection Interface

Features:
- Stripe Elements for secure card tokenization
- Real-time conversation with AI bot
- Session management
- Security indicators
- PCI-DSS compliance UI
- Mobile responsive design
"""

import streamlit as st
import requests
import json
import uuid
from datetime import datetime
import os
from typing import Dict, Optional

# Configure Streamlit page
st.set_page_config(
    page_title="💳 Payment Smart Bot",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/Alamin-Juma/AI-SmartBot-Boto3-PY-Bedrock-LangChain',
        'Report a bug': 'https://github.com/Alamin-Juma/AI-SmartBot-Boto3-PY-Bedrock-LangChain/issues',
        'About': '# Payment Smart Bot\nAI-powered secure payment collection powered by AWS Bedrock & Stripe'
    }
)

# Custom CSS for professional payment interface
st.markdown("""
<style>
/* Main app styling */
.stApp {
    max-width: 1400px;
    margin: 0 auto;
}

/* Security banner */
.security-banner {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 1rem;
    border-radius: 10px;
    margin-bottom: 1rem;
    display: flex;
    align-items: center;
    gap: 1rem;
}

/* Chat container */
.chat-container {
    background-color: #f8f9fa;
    border-radius: 15px;
    padding: 2rem;
    margin-bottom: 1rem;
    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

/* Message bubbles */
.chat-message {
    padding: 1.2rem;
    border-radius: 15px;
    margin-bottom: 1rem;
    display: flex;
    align-items: flex-start;
    animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.chat-message.user {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    flex-direction: row-reverse;
    margin-left: 20%;
}

.chat-message.bot {
    background-color: white;
    color: #2d3748;
    border: 1px solid #e2e8f0;
    margin-right: 20%;
}

.chat-message .avatar {
    width: 45px;
    height: 45px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.5rem;
    flex-shrink: 0;
    margin: 0 1rem;
}

.user .avatar {
    background-color: rgba(255, 255, 255, 0.2);
}

.bot .avatar {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.chat-message .message {
    flex: 1;
    padding: 0.5rem;
    line-height: 1.6;
}

/* Status indicators */
.status-indicator {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    border-radius: 20px;
    font-size: 0.9rem;
    font-weight: 600;
    margin: 0.5rem 0;
}

.status-collecting {
    background-color: #fef3c7;
    color: #92400e;
}

.status-confirming {
    background-color: #dbeafe;
    color: #1e40af;
}

.status-completed {
    background-color: #d1fae5;
    color: #065f46;
}

.status-error {
    background-color: #fee2e2;
    color: #991b1b;
}

/* Security features */
.security-feature {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    padding: 0.8rem;
    background-color: #f0fdf4;
    border-left: 4px solid #10b981;
    border-radius: 8px;
    margin-bottom: 0.8rem;
}

.security-icon {
    font-size: 1.5rem;
    color: #10b981;
}

/* PCI Compliance badge */
.pci-badge {
    background: white;
    border: 2px solid #10b981;
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
    margin: 1rem 0;
}

.pci-badge h3 {
    color: #10b981;
    margin: 0;
    font-size: 1.2rem;
}

/* Payment info card */
.payment-info {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 1.5rem;
    border-radius: 15px;
    margin: 1rem 0;
}

.payment-info h4 {
    margin-top: 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

/* Progress bar */
.progress-container {
    background-color: #e2e8f0;
    border-radius: 10px;
    height: 8px;
    margin: 1rem 0;
    overflow: hidden;
}

.progress-bar {
    height: 100%;
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    transition: width 0.3s ease;
}

/* Info boxes */
.info-box {
    background-color: #f0f9ff;
    border-left: 4px solid #3b82f6;
    padding: 1rem;
    border-radius: 8px;
    margin: 1rem 0;
}

.warning-box {
    background-color: #fffbeb;
    border-left: 4px solid #f59e0b;
    padding: 1rem;
    border-radius: 8px;
    margin: 1rem 0;
}

/* Footer */
.footer {
    text-align: center;
    padding: 2rem;
    color: #718096;
    border-top: 1px solid #e2e8f0;
    margin-top: 3rem;
}

/* Stripe branding */
.powered-by-stripe {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    margin: 1rem 0;
    color: #635bff;
    font-weight: 600;
}

/* Quick actions */
.quick-action {
    background-color: white;
    border: 2px solid #e2e8f0;
    border-radius: 10px;
    padding: 1rem;
    margin: 0.5rem 0;
    cursor: pointer;
    transition: all 0.2s;
}

.quick-action:hover {
    border-color: #667eea;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
}

/* Metric cards */
.metric-card {
    background: white;
    border-radius: 12px;
    padding: 1.5rem;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    text-align: center;
}

.metric-value {
    font-size: 2rem;
    font-weight: bold;
    color: #667eea;
}

.metric-label {
    color: #718096;
    font-size: 0.9rem;
    margin-top: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

# Configuration
API_ENDPOINT = os.getenv("PAYMENT_BOT_API_ENDPOINT", "")

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []

if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if 'payment_status' not in st.session_state:
    st.session_state.payment_status = 'collecting'

if 'conversation_started' not in st.session_state:
    st.session_state.conversation_started = False

if 'api_endpoint' not in st.session_state:
    st.session_state.api_endpoint = API_ENDPOINT

if 'test_mode' not in st.session_state:
    st.session_state.test_mode = True

# Helper Functions
def send_message(message: str) -> Optional[Dict]:
    """Send message to Payment Smart Bot API"""
    if not st.session_state.api_endpoint:
        st.error("⚠️ API endpoint not configured. Please enter it in the sidebar.")
        return None
    
    try:
        payload = {
            "sessionId": st.session_state.session_id,
            "message": message
        }
        
        response = requests.post(
            st.session_state.api_endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.Timeout:
        st.error("⏱️ Request timed out. Please try again.")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"❌ API Error: {str(e)}")
        return None
    except json.JSONDecodeError:
        st.error("❌ Invalid response from server")
        return None

def get_status_badge(status: str) -> str:
    """Get HTML for status badge"""
    status_config = {
        'collecting': ('📝', 'Collecting Information', 'status-collecting'),
        'confirming': ('🔍', 'Confirming Details', 'status-confirming'),
        'completed': ('✅', 'Payment Complete', 'status-completed'),
        'error': ('❌', 'Error', 'status-error')
    }
    
    icon, text, css_class = status_config.get(status, ('ℹ️', 'Unknown', 'status-collecting'))
    return f'<div class="status-indicator {css_class}">{icon} {text}</div>'

def get_progress_percentage() -> int:
    """Calculate conversation progress"""
    message_count = len(st.session_state.messages)
    
    # Typical flow: greeting → name → card → expiry → cvv → confirm
    if message_count == 0:
        return 0
    elif message_count <= 2:
        return 20
    elif message_count <= 4:
        return 40
    elif message_count <= 6:
        return 60
    elif message_count <= 8:
        return 80
    else:
        return 100

def display_security_banner():
    """Display security assurance banner"""
    st.markdown("""
    <div class="security-banner">
        <div style="font-size: 2rem;">🔒</div>
        <div>
            <h3 style="margin: 0;">Secure Payment Collection</h3>
            <p style="margin: 0; opacity: 0.9;">Your information is encrypted and never stored</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

def display_message(role: str, content: str):
    """Display a chat message with proper styling"""
    avatar = "👤" if role == "user" else "🤖"
    css_class = "user" if role == "user" else "bot"
    
    st.markdown(f"""
    <div class="chat-message {css_class}">
        <div class="avatar">{avatar}</div>
        <div class="message">{content}</div>
    </div>
    """, unsafe_allow_html=True)

def main():
    """Main application"""
    
    # Header
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.title("💳 Payment Smart Bot")
        st.markdown("### AI-Powered Secure Payment Collection")
    
    with col2:
        # PCI Compliance badge
        st.markdown("""
        <div class="pci-badge">
            <div style="font-size: 2rem;">🛡️</div>
            <h3>PCI-DSS</h3>
            <p style="margin: 0; font-size: 0.8rem;">Compliant</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Security banner
    display_security_banner()
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # API Endpoint configuration
        st.markdown("### 🔗 API Settings")
        api_endpoint = st.text_input(
            "API Endpoint",
            value=st.session_state.api_endpoint,
            placeholder="https://your-api.execute-api.us-east-1.amazonaws.com/dev/chat",
            help="Enter your Payment Smart Bot API endpoint"
        )
        
        if api_endpoint != st.session_state.api_endpoint:
            st.session_state.api_endpoint = api_endpoint
            st.rerun()
        
        # Test mode toggle
        st.session_state.test_mode = st.toggle(
            "🧪 Test Mode",
            value=st.session_state.test_mode,
            help="Use Stripe test cards in test mode"
        )
        
        if st.session_state.test_mode:
            st.info("**Test Mode Active**\n\nUse test card: `4242424242424242`")
        
        st.markdown("---")
        
        # Session info
        st.markdown("### 📊 Session Info")
        st.metric("Session ID", st.session_state.session_id[:8] + "...")
        st.metric("Messages", len(st.session_state.messages))
        st.metric("Status", st.session_state.payment_status.title())
        
        # Progress bar
        progress = get_progress_percentage()
        st.markdown("### 📈 Progress")
        st.progress(progress / 100)
        st.caption(f"{progress}% Complete")
        
        st.markdown("---")
        
        # Actions
        st.markdown("### 🎯 Actions")
        
        if st.button("🔄 New Session", use_container_width=True):
            st.session_state.messages = []
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.payment_status = 'collecting'
            st.session_state.conversation_started = False
            st.rerun()
        
        if st.button("📋 Copy Session ID", use_container_width=True):
            st.code(st.session_state.session_id, language=None)
            st.success("✅ Session ID displayed above")
        
        st.markdown("---")
        
        # Security features
        st.markdown("### 🔐 Security Features")
        
        security_features = [
            ("🔒", "End-to-end encryption"),
            ("🛡️", "PCI-DSS compliant"),
            ("🔑", "Stripe tokenization"),
            ("📊", "Real-time fraud detection"),
            ("⏰", "Session auto-expiry"),
            ("🚫", "No data storage")
        ]
        
        for icon, feature in security_features:
            st.markdown(f"""
            <div class="security-feature">
                <span class="security-icon">{icon}</span>
                <span>{feature}</span>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Powered by
        st.markdown("""
        <div class="powered-by-stripe">
            <span>Powered by</span>
            <svg width="60" height="25" viewBox="0 0 60 25" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M59.9 13.2c0-5.6-2.8-9.7-7.8-9.7-5 0-8.1 4.1-8.1 9.6 0 6.3 3.6 9.6 8.8 9.6 2.5 0 4.4-.6 6-1.7v-4.7c-1.5.9-3.2 1.4-5.3 1.4-2.1 0-4-.7-4.2-3.2h10.5c0-.3.1-1 .1-1.3zm-10.6-1.9c0-2.4 1.5-3.4 2.8-3.4 1.3 0 2.7 1 2.7 3.4h-5.5zm-13.9-7.8c-2 0-3.3 1-4 1.7l-.3-1.4h-5.3v21.7l6.1-1.3V18c.7.5 1.8 1.2 3.4 1.2 3.5 0 6.6-2.8 6.6-9.8 0-6.2-3.2-9.5-6.5-9.5zm-1.5 14.4c-1.1 0-1.8-.4-2.3-1v-7.9c.5-.6 1.3-1.1 2.3-1.1 1.8 0 3 2 3 5s-1.2 5-3 5zm-14.1-7.8v-.5c0-2.3.9-3.3 2.4-3.3 1.1 0 1.8.2 2.7.6V1.7c-1-.4-2-.6-3.4-.6-4.3 0-7.2 3.6-7.2 9.4v.4h-2.4v5.5h2.4v14.3h6.1V16.4h3.8v-5.5h-4.4zm-11.1-4.8l-6.2 1.3V1.3h-6.1v20.4c0 4.9 3.3 7.6 7.9 7.6 2.5 0 4.3-.5 5.3-1v-5.1c-1 .4-2.2.7-3.9.7-2.2 0-3.4-1-3.4-3.1v-7.8h7.3V5.8h-7.3V1.3z" fill="#635BFF"/>
            </svg>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div style="text-align: center; margin-top: 1rem;">
            <p style="color: #718096; font-size: 0.85rem;">
                🚀 Built with AWS Bedrock<br/>
                🤖 Powered by Llama 3.2 1B
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    # Main chat area
    st.markdown("---")
    
    # Status indicator
    st.markdown(get_status_badge(st.session_state.payment_status), unsafe_allow_html=True)
    
    # Quick start buttons (only show if no conversation)
    if not st.session_state.conversation_started:
        st.markdown("### 🚀 Quick Start")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("💳 Make a Payment", use_container_width=True):
                st.session_state.conversation_started = True
                # Auto-send first message
                response = send_message("I want to make a payment")
                if response:
                    st.session_state.messages.append({
                        "role": "user",
                        "content": "I want to make a payment",
                        "timestamp": datetime.now()
                    })
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response.get("response", ""),
                        "timestamp": datetime.now()
                    })
                    st.session_state.payment_status = response.get("status", "collecting")
                st.rerun()
        
        with col2:
            if st.button("🔍 Check Payment Status", use_container_width=True):
                st.session_state.conversation_started = True
                response = send_message("What's my payment status?")
                if response:
                    st.session_state.messages.append({
                        "role": "user",
                        "content": "What's my payment status?",
                        "timestamp": datetime.now()
                    })
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response.get("response", ""),
                        "timestamp": datetime.now()
                    })
                st.rerun()
        
        with col3:
            if st.button("❓ Get Help", use_container_width=True):
                st.session_state.conversation_started = True
                response = send_message("I need help with payment")
                if response:
                    st.session_state.messages.append({
                        "role": "user",
                        "content": "I need help with payment",
                        "timestamp": datetime.now()
                    })
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response.get("response", ""),
                        "timestamp": datetime.now()
                    })
                st.rerun()
        
        # Info boxes
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            <div class="info-box">
                <h4>💡 How It Works</h4>
                <ol style="margin: 0.5rem 0;">
                    <li>Start a conversation</li>
                    <li>Provide payment details securely</li>
                    <li>Review and confirm</li>
                    <li>Payment processed safely</li>
                </ol>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="warning-box">
                <h4>⚠️ Test Mode</h4>
                <p style="margin: 0.5rem 0;">
                    Use test card: <code>4242424242424242</code><br/>
                    Expiry: Any future date<br/>
                    CVV: Any 3 digits
                </p>
            </div>
            """, unsafe_allow_html=True)
    
    # Chat messages
    if st.session_state.messages:
        st.markdown("### 💬 Conversation")
        
        # Display messages
        for msg in st.session_state.messages:
            display_message(msg["role"], msg["content"])
    
    # Chat input
    st.markdown("---")
    
    if prompt := st.chat_input("Type your message here...", key="chat_input"):
        # Add user message
        st.session_state.messages.append({
            "role": "user",
            "content": prompt,
            "timestamp": datetime.now()
        })
        st.session_state.conversation_started = True
        
        # Get bot response
        with st.spinner("🤖 Processing..."):
            response = send_message(prompt)
            
            if response:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response.get("response", "I apologize, but I couldn't process that. Please try again."),
                    "timestamp": datetime.now()
                })
                
                # Update status
                st.session_state.payment_status = response.get("status", "collecting")
        
        st.rerun()
    
    # Footer
    st.markdown("""
    <div class="footer">
        <p><strong>Payment Smart Bot v1.0</strong></p>
        <p>
            🔒 Your data is encrypted | 🛡️ PCI-DSS Compliant | 🚀 Powered by AWS Bedrock
        </p>
        <p style="font-size: 0.85rem; margin-top: 1rem;">
            © 2025 AI SmartBots | 
            <a href="https://github.com/Alamin-Juma/AI-SmartBot-Boto3-PY-Bedrock-LangChain" target="_blank">GitHub</a> | 
            <a href="#" target="_blank">Privacy Policy</a> | 
            <a href="#" target="_blank">Terms of Service</a>
        </p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    # Check if API endpoint is configured
    if not st.session_state.api_endpoint:
        st.warning("⚠️ Please configure your API endpoint in the sidebar to get started.")
    
    main()
