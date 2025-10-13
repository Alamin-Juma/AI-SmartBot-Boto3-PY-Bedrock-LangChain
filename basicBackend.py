from langchain_aws.chat_models import ChatBedrock
from langchain.memory import ConversationSummaryMemory, ConversationSummaryBufferMemory
from langchain.chains import ConversationChain
from langchain.schema import HumanMessage


def titan_llm(input_text):
    """Function to invoke Amazon Titan model"""

#function to invoke model
def get_llm():
    return ChatBedrock(
        model_id="amazon.titan-text-lite-v1",  # 👈 updated model ID
        model_kwargs= {                          #configure the properties for Titan
            "temperature": 1,  
            "topP": 0.5,
            "maxTokenCount": 100,
        },
        region_name="us-east-1"                 #specify the AWS region 
    )

#test the model
#    return llm.invoke(input_text)
#response = get_llm("Hello, which LLM model you are")
#print(response)

##Create a memory function for this chat session
def create_memory():
    llm=get_llm()
    memory = ConversationSummaryBufferMemory(llm=llm, max_token_limit=512) #Maintains a summary of previous messages
    return memory


##Create a chat client function
def get_chat_response(input_text, memory): 
    
    llm = get_llm()
    
    conversation_with_memory = ConversationChain(            #create a conversation chain
        llm = llm,                                           #using the Bedrock LLM
        memory = memory,                                     #with the summarization memory
        verbose = True                                       #print out some of the internal states of the chain while running
    )
    
    chat_response = conversation_with_memory.invoke(input = input_text) #pass the user message and summary to the model
    
    return chat_response['response']


# Main function to run the chatbot
def main():
    """Main function to test the chatbot via CLI."""
    print("Initializing AI SmartBot...")
    
    # Create memory for the conversation
    memory = create_memory()
    
    print("\nAI SmartBot is ready. Type 'quit' to exit.")
    
    while True:
        user_input = input("\nYou: ")
        
        if user_input.lower() in ['quit', 'exit', 'bye']:
            print("Goodbye!")
            break
        
        try:
            response = get_chat_response(user_input, memory)
            print(f"\nBot: {response}")
        except Exception as e:
            print(f"\nError: {e}")


if __name__ == "__main__":
    main()