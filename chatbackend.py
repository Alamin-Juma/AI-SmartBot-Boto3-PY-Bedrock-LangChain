## 1. Import necessary libraries
import boto3
from langchain_aws import ChatBedrock
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain.schema import HumanMessage
import os

## 2. Create functions to invoke models
def setup_bedrock_client():
    """Set up AWS Bedrock client"""
    try:
        # Initialize bedrock client with default AWS credentials
        bedrock_client = boto3.client(
            'bedrock-runtime',
            region_name='us-east-1'  # Change to your preferred region
        )
        return bedrock_client
    except Exception as e:
        print(f"Error setting up Bedrock client: {e}")
        return None

def titan_llm(input_text):
    """Function to invoke Amazon Titan model"""
    try:
        llm = ChatBedrock(
            model_id="amazon.titan-text-express-v1",
            model_kwargs={
                "temperature": 0.7,
                "maxTokenCount": 2048,
                "topP": 0.9
            },
            region_name='us-east-1'  # Change to your preferred region
        )
        
        # Create a proper message format
        message = HumanMessage(content=input_text)
        response = llm.invoke([message])
        return response.content
    
    except Exception as e:
        return f"Error: {e}"

# Test the function (commented out for production use)
# response = titan_llm("Hello, how are you?")
# print(response)

## 3. Create memory functions for the chatbot
def setup_conversation_memory():
    """Set up conversation memory"""
    return ConversationBufferMemory()

def create_conversation_chain():
    """Create a conversation chain with memory"""
    try:
        llm = ChatBedrock(
            model_id="amazon.titan-text-lite-v1",  # 👈 updated model ID
            model_kwargs={
                "temperature": 0.7,
                "maxTokenCount": 2048,
                "topP": 0.9
            },
            region_name='us-east-1'
        )
        
        memory = setup_conversation_memory()
        conversation = ConversationChain(
            llm=llm,
            memory=memory,
            verbose=True
        )
        return conversation
    except Exception as e:
        print(f"Error creating conversation chain: {e}")
        return None

## 4. Create a chat client function to run chatbot
def chat_with_bot(conversation_chain, user_input):
    """Chat with the bot using conversation chain"""
    try:
        if conversation_chain:
            response = conversation_chain.predict(input=user_input)
            return response
        else:
            return "Error: Conversation chain not initialized"
    except Exception as e:
        return f"Error in chat: {e}"

def initialize_chatbot():
    """Initialize the chatbot"""
    print("Initializing AI SmartBot...")
    conversation = create_conversation_chain()
    
    if conversation:
        print("✅ Chatbot initialized successfully!")
        return conversation
    else:
        print("❌ Failed to initialize chatbot")
        return None

# Main function for testing
def main():
    """Main function to test the chatbot"""
    conversation = initialize_chatbot()
    
    if conversation:
        print("\n🤖 AI SmartBot is ready! Type 'quit' to exit.")
        
        while True:
            user_input = input("\nYou: ")
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("👋 Goodbye!")
                break
            
            response = chat_with_bot(conversation, user_input)
            print(f"Bot: {response}")

if __name__ == "__main__":
    main()  
