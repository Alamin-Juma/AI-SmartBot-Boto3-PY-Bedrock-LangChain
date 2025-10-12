from langchain_aws import ChatBedrock
from langchain.memory import ConversationBufferMemory
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
