## 1. Import necessary libraries
from __future__ import annotations

import boto3
from typing import Dict

from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate
from langchain.memory import ConversationSummaryBufferMemory


MODEL_ID = "amazon.titan-text-lite-v1"
MODEL_REGION = "us-east-1"


class ChatbotManager:
    """Manage LLM, prompt template, and per-session memory."""

    def __init__(self) -> None:
        self.llm = ChatBedrock(
            model_id=MODEL_ID,
            model_kwargs={
                "temperature": 0.5,
                "maxTokenCount": 2048,
                "topP": 0.9,
            },
            region_name=MODEL_REGION,
        )

        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are AI SmartBot, an AWS Bedrock assistant that gives precise, concise, "
                    "and helpful answers. If you are unsure about something, explain what extra "
                    "information you would need.",
                ),
                (
                    "system",
                    "Conversation summary so far: {conversation_summary}\nUse it to stay on topic.",
                ),
                ("human", "{input}"),
            ]
        )

        self.memory_store: Dict[str, ConversationSummaryBufferMemory] = {}

    def _memory_for(self, session_id: str) -> ConversationSummaryBufferMemory:
        if session_id not in self.memory_store:
            self.memory_store[session_id] = ConversationSummaryBufferMemory(
                llm=self.llm,
                max_token_limit=1500,
                return_messages=False,
                ai_memory_key="output",
                human_memory_key="input",
            )
        return self.memory_store[session_id]

    def chat(self, session_id: str, user_input: str) -> str:
        memory = self._memory_for(session_id)
        summary = memory.load_memory_variables({}).get("history", "")

        response = self.prompt | self.llm
        result = response.invoke({
            "conversation_summary": summary,
            "input": user_input,
        })

        output_text = result.content if hasattr(result, "content") else str(result)
        memory.save_context({"input": user_input}, {"output": output_text})
        return output_text


def setup_bedrock_client():
    """Check connectivity to AWS Bedrock."""
    try:
        return boto3.client("bedrock-runtime", region_name=MODEL_REGION)
    except Exception as exc:  # pragma: no cover
        print(f"Error setting up Bedrock client: {exc}")
        return None


def initialize_chatbot() -> ChatbotManager | None:
    """Initialize the chatbot manager."""
    print("Initializing AI SmartBot...")
    client = setup_bedrock_client()
    if client is None:
        print("Unable to connect to AWS Bedrock.")
        return None

    try:
        chatbot = ChatbotManager()
        print("Chatbot initialized successfully.")
        return chatbot
    except Exception as exc:
        print(f"Failed to initialize chatbot: {exc}")
        return None


def chat_with_bot(chatbot: ChatbotManager, session_id: str, user_input: str) -> str:
    """Chat with the bot using the conversation summary memory."""
    if chatbot is None:
        return "Error: Chatbot is not initialized."

    try:
        return chatbot.chat(session_id, user_input)
    except Exception as exc:
        return f"Error in chat: {exc}"


# Main function for testing
def main() -> None:
    """Main function to test the chatbot via CLI."""
    chatbot = initialize_chatbot()

    if chatbot is None:
        return

    print("\nAI SmartBot is ready. Type 'quit' to exit.")
    session_id = "cli-user"

    while True:
        user_input = input("\nYou: ")

        if user_input.lower() in {"quit", "exit", "bye"}:
            print("Goodbye.")
            break

        response = chat_with_bot(chatbot, session_id, user_input)
        print(f"Bot: {response}")


if __name__ == "__main__":
    main()
