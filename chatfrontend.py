import streamlit as st
import sys
import os
import uuid

# Add the current directory to the path to import chatbackend
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from chatbackend import initialize_chatbot, chat_with_bot

# Streamlit page configuration
st.set_page_config(
    page_title="🤖 AI SmartBot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
.stApp {
    max-width: 1200px;
    margin: 0 auto;
}

.chat-message {
    padding: 1rem;
    border-radius: 0.5rem;
    margin-bottom: 1rem;
    display: flex;
    align-items: flex-start;
}

.chat-message.user {
    background-color: #2b313e;
    flex-direction: row-reverse;
}

.chat-message.bot {
    background-color: #475063;
}

.chat-message .avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    margin: 0 1rem;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.2rem;
}

.chat-message .message {
    flex: 1;
    padding: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

def main():
    """Main Streamlit application"""
    
    # Title and description
    st.title("🤖 AI SmartBot - AWS Bedrock & LangChain")
    st.markdown("### Powered by Amazon Titan LLM via AWS Bedrock")
    
    # Sidebar
    with st.sidebar:
        st.header("🔧 Configuration")
        st.info("**Model:** Amazon Titan Text Express v1")
        st.info("**Region:** US-East-1")
        st.info("**Framework:** LangChain + AWS Bedrock")
        
        # Clear chat button
        if st.button("🗑️ Clear Chat History"):
            st.session_state.messages = []
            st.session_state.conversation = None
            st.session_state.session_id = str(uuid.uuid4())
            st.rerun()
        
        st.markdown("---")
        st.markdown("### 💡 Tips")
        st.markdown("""
        - Ask questions about any topic
        - The bot remembers conversation context
        - Try asking follow-up questions
        - Be specific for better responses
        """)
    
    # Initialize session state
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    if 'conversation' not in st.session_state:
        st.session_state.conversation = None

    if 'session_id' not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    
    # Initialize chatbot if not already done
    if st.session_state.conversation is None:
        with st.spinner("🔄 Initializing AI SmartBot..."):
            try:
                st.session_state.conversation = initialize_chatbot()
                if st.session_state.conversation:
                    st.success("✅ AI SmartBot initialized successfully!")
                else:
                    st.error("❌ Failed to initialize chatbot. Please check your AWS credentials.")
                    return
            except Exception as e:
                st.error(f"❌ Error initializing chatbot: {e}")
                return
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask me anything..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get bot response
        with st.chat_message("assistant"):
            with st.spinner("🤔 Thinking..."):
                try:
                    response = chat_with_bot(
                        st.session_state.conversation,
                        st.session_state.session_id,
                        prompt,
                    )
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    error_msg = f"❌ Error: {e}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #888;'>
        🚀 Built with Streamlit, LangChain, and AWS Bedrock | 
        💡 Powered by Amazon Titan LLM
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()