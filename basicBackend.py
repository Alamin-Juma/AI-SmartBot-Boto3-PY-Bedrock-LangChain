from langchain_aws import ChatBedrock
from langchain.memory import ConversationSummaryMemory
from langchain.chains import ConversationChain
from langchain.schema import HumanMessage


def titan_llm(input_text):
    """Function to invoke Amazon Titan model"""
    try:
        llm = ChatBedrock(
            model_id="amazon.titan-text-lite-v1",  # 👈 updated model ID
            model_kwargs={
                "temperature": 0.7,
                "maxTokenCount": 2048,
                "topP": 0.9
            },
            region_name='us-east-1'  # Change to your region if needed
        )

        message = HumanMessage(content=input_text)
        response = llm.invoke([message])
        print(response)
        return response.content

    except Exception as e:
        return f"Error: {e}"


if __name__ == "__main__":
    response = titan_llm("What is your name?")
    print("Model response:", response)


## 3. Create memory functions for the chatbot
def setup_conversation_memory(llm):
    """Set up conversation memory"""
    return ConversationSummaryMemory(llm=llm, max_token_limit=256) # 👈 updated to ConversationSummaryMemory


# 4 : create a chat client fucntion to run the chatbot 
def get_chatbot_response(input_text, memory):
    """Chat with the bot using conversation chain"""
    llm=titan_llm
    ConversationChain=ConversationChain(  #create a conversation chain
        llm=llm,                          #use bedriock llm 
        memory=memory,                    #use memory
        verbose=True                      #print out some of the internal states of the chain while running
    )
    try:
        response = ConversationChain.run(input_text)
        return response
    except Exception as e:
        return f"Error: {e}"