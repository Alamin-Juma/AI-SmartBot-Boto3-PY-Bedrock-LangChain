# Running AI SmartBot

This guide covers the minimum steps to launch the chatbot from both the command line and the Streamlit UI.

## Prerequisites
- Python 3.13 available via `C:/Users/User/AppData/Local/Microsoft/WindowsApps/python3.13.exe`
- An AWS IAM identity with access to Amazon Bedrock and the model `amazon.titan-text-lite-v1` in `us-east-1`
- Required Python packages installed in the current environment (`boto3`, `streamlit`, `langchain`, `langchain-aws`, `langchain-community`)

## Backend (CLI) Chat Loop
```bash
cd /c/dev/personal/AI-SmartBots-Boto3-Bedrock-LLMs
C:/Users/User/AppData/Local/Microsoft/WindowsApps/python3.13.exe chatbackend.py
```

The script will initialise the chatbot and drop you into an interactive prompt. Type `quit` (or `exit`/`bye`) to end the session.

## Streamlit Frontend
```bash
cd /c/dev/personal/AI-SmartBots-Boto3-Bedrock-LLMs
C:/Users/User/AppData/Local/Microsoft/WindowsApps/python3.13.exe -m streamlit run chatfrontend.py
```

When the server finishes booting it prints a local URL (for example `http://localhost:8501`). Open that address in your browser to chat. Use the **Clear Chat History** button in the sidebar to start a fresh session.

## Environment Notes
- The backend keeps a per-session summary using `ConversationSummaryBufferMemory`, so responses stay on topic without storing the entire transcript.
- Both the CLI and Streamlit rely on the same backend module, so AWS credentials need to be available via the usual SDK lookup (environment variables, shared config/credentials files, or instance profile).
