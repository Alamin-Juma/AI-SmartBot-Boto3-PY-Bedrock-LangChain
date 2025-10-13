# Running AI SmartBot 🤖

This guide covers how to launch the AI SmartBot chatbot from both the command line (CLI) and the Streamlit web UI.

## Prerequisites

### Required Software
- **Python 3.13** installed and accessible via:
  ```
  C:/Users/User/AppData/Local/Microsoft/WindowsApps/python3.13.exe
  ```
- **Git Bash** or similar terminal (for Windows)

### AWS Configuration
- An **AWS IAM identity** with the following:
  - Access to Amazon Bedrock service
  - Model access enabled for `amazon.titan-text-lite-v1` in the `us-east-1` region
  - Valid AWS credentials configured (via `~/.aws/credentials`, environment variables, or IAM role)

### Python Dependencies
Required packages (should already be installed):
```bash
pip install boto3 streamlit langchain langchain-aws langchain-community transformers
```

## Project Structure

```
AI-SmartBots-Boto3-Bedrock-LLMs/
├── basicBackend.py       # Simple backend with ConversationSummaryBufferMemory
├── basicFrontend.py      # Simple Streamlit UI using basicBackend
├── chatbackend.py        # Advanced backend with ChatbotManager class
├── chatfrontend.py       # Advanced Streamlit UI using chatbackend
├── image.png            # Screenshot of the app
├── image copy.png       # Additional screenshot
└── docs/
    └── RUNNING.md       # This file
```

---

## 🚀 Quick Start

### Option 1: Basic Version (Simple Implementation)

#### Backend CLI
Run the basic backend in terminal for a command-line chat experience:

```bash
cd /c/dev/personal/AI-SmartBots-Boto3-Bedrock-LLMs
C:/Users/User/AppData/Local/Microsoft/WindowsApps/python3.13.exe basicBackend.py
```

**What to expect:**
- Initialization message
- Interactive prompt: `You:`
- Type your questions and press Enter
- Type `quit`, `exit`, or `bye` to exit

#### Frontend (Streamlit Web UI)
Launch the basic Streamlit web interface:

```bash
cd /c/dev/personal/AI-SmartBots-Boto3-Bedrock-LLMs
C:/Users/User/AppData/Local/Microsoft/WindowsApps/python3.13.exe -m streamlit run basicFrontend.py
```

**What to expect:**
- Server starts and displays: `Local URL: http://localhost:8501`
- Open the URL in your browser
- Chat interface with message history
- Real-time responses from AWS Bedrock

---

### Option 2: Advanced Version (Production-Ready)

#### Backend CLI
Run the advanced backend with better memory management:

```bash
cd /c/dev/personal/AI-SmartBots-Boto3-Bedrock-LLMs
C:/Users/User/AppData/Local/Microsoft/WindowsApps/python3.13.exe chatbackend.py
```

**Features:**
- `ChatbotManager` class for better organization
- Per-session memory management
- Conversation summary to maintain context
- More robust error handling

#### Frontend (Streamlit Web UI)
Launch the advanced Streamlit interface:

```bash
cd /c/dev/personal/AI-SmartBots-Boto3-Bedrock-LLMs
C:/Users/User/AppData/Local/Microsoft/WindowsApps/python3.13.exe -m streamlit run chatfrontend.py
```

**Features:**
- Modern chat interface with styled messages
- Sidebar with configuration details
- "Clear Chat History" button to reset conversations
- Real-time status indicators
- Session-based memory management

**Expected output:**
```
Local URL: http://localhost:8501
Network URL: http://10.4.19.162:8501

Initializing AI SmartBot...
Chatbot initialized successfully.
```

---

## 📸 Screenshots

### Web Interface
![AI SmartBot Web Interface](../image.png)

### Chat Example
![Chat Example](../image%20copy.png)

---

## ⚙️ Configuration

### Model Settings
Both backends use the following configuration:

| Parameter | Value | Description |
|-----------|-------|-------------|
| Model ID | `amazon.titan-text-lite-v1` | Amazon Titan Lite model |
| Region | `us-east-1` | AWS region |
| Temperature | `0.5` - `1.0` | Controls randomness (higher = more creative) |
| Max Tokens | `2048` | Maximum response length |
| Top P | `0.5` - `0.9` | Nucleus sampling parameter |

### Memory Configuration
- **Basic**: Uses `ConversationSummaryBufferMemory` with 512 token limit
- **Advanced**: Uses `ConversationSummaryBufferMemory` with 1500 token limit and session management

---

## 🔍 Troubleshooting

### Common Warnings (Safe to Ignore)

**1. PyTorch/TensorFlow Warning:**
```
None of PyTorch, TensorFlow >= 2.0, or Flax have been found.
```
✅ **Safe to ignore** - Not required for AWS Bedrock. Only needed for local Hugging Face models.

**2. LangChain Deprecation Warning:**
```
LangChainDeprecationWarning: Please see the migration guide...
```
✅ **Safe to ignore** - The code works fine. This is a future migration notice.

### Common Errors

**1. Access Denied:**
```
AccessDeniedException: You don't have access to the model
```
❌ **Solution:**
- Go to AWS Console → Bedrock → Model Access
- Request access for "Amazon Titan Text Lite v1" in us-east-1
- Wait for approval (usually instant)

**2. Credentials Not Found:**
```
Unable to locate credentials
```
❌ **Solution:**
- Configure AWS credentials: `aws configure`
- Or set environment variables:
  ```bash
  export AWS_ACCESS_KEY_ID=your_key
  export AWS_SECRET_ACCESS_KEY=your_secret
  export AWS_DEFAULT_REGION=us-east-1
  ```

**3. Module Import Error:**
```
ModuleNotFoundError: No module named 'langchain_aws'
```
❌ **Solution:**
```bash
pip install langchain-aws langchain-community transformers
```

**4. Streamlit Command Not Found:**
```
bash: streamlit: command not found
```
❌ **Solution:** Always use the Python module syntax:
```bash
python3.13.exe -m streamlit run <filename>
```

---

## 💡 Tips & Best Practices

### For CLI Usage
- Keep questions concise for faster responses
- The bot remembers conversation context
- Use `quit` to exit cleanly

### For Web UI Usage
- Use "Clear Chat History" button to start fresh conversations
- The sidebar shows current configuration
- Multiple browser tabs share the same session
- Refresh the page if you encounter errors

### Memory Management
- **ConversationSummaryBufferMemory** automatically summarizes old messages
- This keeps context relevant while avoiding token limits
- Long conversations are automatically condensed

### AWS Bedrock Best Practices
- Monitor your usage in AWS Console → Bedrock → Metrics
- Titan Lite is cost-effective for testing
- Consider switching to Titan Express for production workloads

---

## 🆘 Support

### Useful Commands

**Check AWS credentials:**
```bash
aws sts get-caller-identity
```

**List available Bedrock models:**
```bash
aws bedrock list-foundation-models --region us-east-1
```

**Check Python packages:**
```bash
pip list | grep -E "langchain|boto3|streamlit"
```

### Project Links
- **Repository:** [AI-SmartBot-Boto3-PY-Bedrock-LangChain](https://github.com/Alamin-Juma/AI-SmartBot-Boto3-PY-Bedrock-LangChain)
- **AWS Bedrock Documentation:** https://docs.aws.amazon.com/bedrock/
- **LangChain Documentation:** https://python.langchain.com/
- **Streamlit Documentation:** https://docs.streamlit.io/

---

## 📝 Notes

- Both implementations use the same AWS Bedrock model
- The "advanced" version (`chatbackend.py`) has better code organization and is recommended for production
- The "basic" version (`basicBackend.py`) is simpler and good for learning
- All chat sessions maintain context until cleared or restarted
- The web UI is more user-friendly than the CLI version
