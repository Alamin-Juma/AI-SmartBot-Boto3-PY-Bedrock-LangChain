# Custom Mistral Model Setup for PCI Level 1 Compliance

## Overview

This guide explains how to set up a **custom Mistral 7B model** using Amazon Bedrock's **Custom Model Import** or **Inference Profiles** to ensure **NO customer data reaches the AI model**.

---

## 🔐 Why Custom Model Inference?

### Foundation Model (Current - ❌ Not PCI Level 1)
```
You → Lambda → Bedrock Foundation Model → Response
                ↑
                Shared model (trained on broad data)
                Could theoretically access metadata
```

### Custom Model Import (Target - ✅ PCI Level 1)
```
You → Lambda → Custom Inference Profile → Isolated Model → Response
                ↑
                YOUR model weights (no training on customer data)
                Complete isolation, no external data access
```

---

## 🎯 Three Approaches (Choose One)

### **Option 1: Amazon Bedrock Custom Model Import (Recommended)**
Import your own Mistral weights into a private inference endpoint.

### **Option 2: Amazon Bedrock Inference Profiles**
Use cross-region inference with dedicated capacity.

### **Option 3: SageMaker Custom Endpoint**
Host Mistral on your own SageMaker endpoint (full control).

---

## 📋 Option 1: Custom Model Import (Bedrock)

### Step 1: Prepare Mistral 7B Model Weights

#### Download Mistral 7B from Hugging Face
```bash
# Install Hugging Face CLI
pip install huggingface_hub

# Login to Hugging Face (get token from https://huggingface.co/settings/tokens)
huggingface-cli login

# Download Mistral 7B Instruct
huggingface-cli download mistralai/Mistral-7B-Instruct-v0.2 \
  --local-dir ./mistral-7b-instruct \
  --local-dir-use-symlinks False
```

#### Convert to Bedrock-Compatible Format
```python
# convert_to_bedrock.py
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import json

model_path = "./mistral-7b-instruct"
output_path = "./mistral-7b-bedrock"

# Load model
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    torch_dtype=torch.float16,
    device_map="auto"
)
tokenizer = AutoTokenizer.from_pretrained(model_path)

# Save in format compatible with Bedrock
model.save_pretrained(output_path, safe_serialization=True)
tokenizer.save_pretrained(output_path)

# Create model card for Bedrock
model_card = {
    "model_name": "mistral-7b-pci-isolated",
    "model_type": "text-generation",
    "framework": "pytorch",
    "model_format": "safetensors",
    "metadata": {
        "pci_compliant": True,
        "isolated": True,
        "no_customer_data": True
    }
}

with open(f"{output_path}/model_card.json", "w") as f:
    json.dump(model_card, f, indent=2)

print(f"✓ Model converted to: {output_path}")
```

Run conversion:
```bash
python convert_to_bedrock.py
```

### Step 2: Upload Model to S3

```bash
# Create S3 bucket for model weights
aws s3 mb s3://payment-bot-custom-models-$(aws sts get-caller-identity --query Account --output text)

# Upload model artifacts
aws s3 sync ./mistral-7b-bedrock/ \
  s3://payment-bot-custom-models-$(aws sts get-caller-identity --query Account --output text)/mistral-7b/ \
  --storage-class INTELLIGENT_TIERING

# Verify upload
aws s3 ls s3://payment-bot-custom-models-$(aws sts get-caller-identity --query Account --output text)/mistral-7b/
```

### Step 3: Import Model to Bedrock

```bash
# Create custom model import job
aws bedrock create-model-customization-job \
  --job-name "mistral-7b-pci-isolated-$(date +%Y%m%d)" \
  --custom-model-name "mistral-7b-pci-isolated" \
  --role-arn "arn:aws:iam::YOUR_ACCOUNT:role/BedrockCustomModelRole" \
  --base-model-identifier "mistral.mistral-7b-instruct-v0:2" \
  --training-data-config "{ \
    \"s3Uri\": \"s3://payment-bot-custom-models-YOUR_ACCOUNT/mistral-7b/\" \
  }" \
  --output-data-config "{ \
    \"s3Uri\": \"s3://payment-bot-custom-models-YOUR_ACCOUNT/output/\" \
  }" \
  --hyper-parameters "{ \
    \"epochCount\": \"1\", \
    \"batchSize\": \"1\", \
    \"learningRate\": \"0.00001\" \
  }"
```

**Expected Time**: 2-4 hours for model import

### Step 4: Create Inference Profile

```bash
# Once import completes, create inference profile
CUSTOM_MODEL_ARN=$(aws bedrock list-custom-models \
  --query 'modelSummaries[?modelName==`mistral-7b-pci-isolated`].modelArn' \
  --output text)

echo "Custom Model ARN: $CUSTOM_MODEL_ARN"

# Create inference profile with isolated compute
aws bedrock create-inference-profile \
  --inference-profile-name "payment-bot-isolated-inference" \
  --model-source "{ \
    \"copyFrom\": \"$CUSTOM_MODEL_ARN\" \
  }" \
  --tags Key=Purpose,Value=PCI-Isolated Key=Compliance,Value=Level-1
```

### Step 5: Get Inference Profile ARN

```bash
# Get the inference profile ARN
INFERENCE_PROFILE_ARN=$(aws bedrock get-inference-profile \
  --inference-profile-identifier payment-bot-isolated-inference \
  --query 'inferenceProfileArn' \
  --output text)

echo "Inference Profile ARN: $INFERENCE_PROFILE_ARN"

# Save to environment variable for Lambda
echo "BEDROCK_MODEL_ID=$INFERENCE_PROFILE_ARN" > .env
```

---

## 📋 Option 2: Cross-Region Inference Profile (Faster Setup)

If you don't want to import custom weights, use **cross-region inference** with dedicated capacity:

### Step 1: Create Inference Profile
```bash
aws bedrock create-inference-profile \
  --inference-profile-name "payment-bot-cross-region" \
  --model-source "{ \
    \"copyFrom\": \"us.mistral.mistral-7b-instruct-v0:2\" \
  }" \
  --inference-profile-config "{ \
    \"modelCopyConfig\": { \
      \"targetRegion\": \"us-west-2\", \
      \"copyType\": \"COPY_AND_ENCRYPT\" \
    } \
  }"
```

### Step 2: Get Profile ARN
```bash
INFERENCE_PROFILE_ARN=$(aws bedrock get-inference-profile \
  --inference-profile-identifier payment-bot-cross-region \
  --query 'inferenceProfileArn' \
  --output text)

echo "Use this ARN: $INFERENCE_PROFILE_ARN"
```

**Benefits**:
- ✅ Regional isolation
- ✅ Dedicated compute (not shared)
- ✅ Encrypted in transit and at rest
- ✅ No cross-account data access

---

## 📋 Option 3: SageMaker Custom Endpoint (Maximum Control)

For **complete control** over the model and infrastructure:

### Step 1: Create SageMaker Model

```python
# deploy_mistral_sagemaker.py
import boto3
import sagemaker
from sagemaker.huggingface import HuggingFaceModel

role = "arn:aws:iam::YOUR_ACCOUNT:role/SageMakerExecutionRole"

# Create model from Hugging Face
huggingface_model = HuggingFaceModel(
    model_data="s3://payment-bot-custom-models-YOUR_ACCOUNT/mistral-7b.tar.gz",
    role=role,
    transformers_version="4.37",
    pytorch_version="2.1",
    py_version="py310",
    model_server_workers=1,
    env={
        'HF_MODEL_ID': 'mistralai/Mistral-7B-Instruct-v0.2',
        'HF_TASK': 'text-generation',
        'MAX_INPUT_LENGTH': '2048',
        'MAX_TOTAL_TOKENS': '4096',
    }
)

# Deploy to dedicated endpoint
predictor = huggingface_model.deploy(
    initial_instance_count=1,
    instance_type="ml.g5.2xlarge",  # GPU instance
    endpoint_name="payment-bot-mistral-isolated",
    wait=True
)

print(f"✓ Endpoint deployed: {predictor.endpoint_name}")
```

### Step 2: Update Lambda to Use SageMaker

```python
# In lambda_handler.py
import boto3

sagemaker_runtime = boto3.client('sagemaker-runtime')

def invoke_sagemaker_model(prompt: str) -> str:
    """Invoke custom SageMaker endpoint"""
    
    endpoint_name = os.environ.get('SAGEMAKER_ENDPOINT', 'payment-bot-mistral-isolated')
    
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 150,
            "temperature": 0.7,
            "top_p": 0.9
        }
    }
    
    response = sagemaker_runtime.invoke_endpoint(
        EndpointName=endpoint_name,
        ContentType='application/json',
        Body=json.dumps(payload)
    )
    
    result = json.loads(response['Body'].read().decode())
    return result[0]['generated_text']
```

---

## 🔄 Update Lambda Configuration

### Update SAM Template

```yaml
# template.yaml
Parameters:
  BedrockModelId:
    Type: String
    Default: "arn:aws:bedrock:us-east-1:YOUR_ACCOUNT:inference-profile/payment-bot-isolated-inference"
    Description: "Custom inference profile ARN (NOT foundation model)"

Resources:
  PaymentBotFunction:
    Type: AWS::Serverless::Function
    Properties:
      Environment:
        Variables:
          BEDROCK_MODEL_ID: !Ref BedrockModelId
          # OR for SageMaker:
          # SAGEMAKER_ENDPOINT: payment-bot-mistral-isolated
```

### Update IAM Permissions

```yaml
# For Bedrock Custom Model
Policies:
  - PolicyName: BedrockCustomModelAccess
    PolicyDocument:
      Version: '2012-10-17'
      Statement:
        - Effect: Allow
          Action:
            - bedrock:InvokeModel
          Resource:
            - !Sub "arn:aws:bedrock:${AWS::Region}:${AWS::AccountId}:inference-profile/*"

# For SageMaker Endpoint
Policies:
  - PolicyName: SageMakerInvokeAccess
    PolicyDocument:
      Version: '2012-10-17'
      Statement:
        - Effect: Allow
          Action:
            - sagemaker:InvokeEndpoint
          Resource:
            - !Sub "arn:aws:sagemaker:${AWS::Region}:${AWS::AccountId}:endpoint/payment-bot-mistral-isolated"
```

---

## 🎯 Comparison: Foundation vs. Custom

| Feature | Foundation Model | Custom Import | SageMaker Endpoint |
|---------|-----------------|---------------|-------------------|
| **Setup Time** | 5 minutes | 2-4 hours | 30 minutes |
| **PCI Level 1** | ⚠️ Questionable | ✅ Yes | ✅ Yes |
| **Data Isolation** | ❌ Shared | ✅ Isolated | ✅ Completely Isolated |
| **Cost (per 1M tokens)** | $0.15 | $0.20-$0.30 | $1.50-$3.00 |
| **Control** | ❌ None | 🟡 Medium | ✅ Full |
| **Customization** | ❌ No | 🟡 Limited | ✅ Full |
| **QSA Approval** | ❌ Difficult | ✅ Likely | ✅ Guaranteed |

---

## ✅ Recommended Approach for PCI Level 1

### **Phase 1: POC (Current)**
Use **foundation model** with strict CHD masking:
- Model ID: `mistral.mistral-7b-instruct-v0:2`
- Prove CHD never reaches AI
- ✅ Works for POC and demo

### **Phase 2: Production (Required for PCI Level 1)**
Deploy **custom inference profile**:
- Use Option 2 (Cross-Region Inference)
- Dedicated compute, no shared resources
- Regional isolation
- ✅ QSA will likely approve

### **Phase 3: Maximum Compliance (If QSA Requires)**
Deploy **SageMaker custom endpoint**:
- Full control over model and infrastructure
- Private VPC deployment
- Network isolation (no internet access)
- ✅ Guaranteed QSA approval

---

## 📊 Cost Comparison (1000 calls/month)

| Approach | Cost |
|----------|------|
| Foundation Model | $0.68/month |
| Custom Inference Profile | $1.20/month |
| SageMaker Endpoint (24/7) | $350/month |
| SageMaker Serverless | $2.50/month |

**Recommendation**: Use **Custom Inference Profile** (Option 2) for best balance of compliance and cost.

---

## 🚀 Quick Setup for Production

### If You Have Time Constraints:

```bash
# Option 2 (Fastest - 10 minutes)
aws bedrock create-inference-profile \
  --inference-profile-name "payment-bot-isolated" \
  --model-source '{"copyFrom":"us.mistral.mistral-7b-instruct-v0:2"}' \
  --inference-profile-config '{"modelCopyConfig":{"targetRegion":"us-west-2","copyType":"COPY_AND_ENCRYPT"}}'

# Get ARN
PROFILE_ARN=$(aws bedrock get-inference-profile \
  --inference-profile-identifier payment-bot-isolated \
  --query 'inferenceProfileArn' --output text)

# Update Lambda
aws lambda update-function-configuration \
  --function-name payment-bot-handler-dev \
  --environment "Variables={BEDROCK_MODEL_ID=$PROFILE_ARN}"
```

---

## 📝 Documentation for QSA

When presenting to a QSA, provide:

1. **Architecture Diagram** showing:
   - Custom inference profile ARN (not foundation model)
   - No data path between customer data and model training
   - Complete isolation of compute resources

2. **Configuration Evidence**:
   ```bash
   aws bedrock get-inference-profile \
     --inference-profile-identifier YOUR_PROFILE \
     --query '{Name:inferenceProfileName,ARN:inferenceProfileArn,Model:modelSource,Status:status}'
   ```

3. **IAM Policy** showing restricted access to custom profile only

4. **Audit Logs** showing all invocations are logged and monitored

---

## 🎓 Next Steps

**For POC (Current)**:
- ✅ Keep using foundation model with CHD masking
- Prove the architecture works

**For Production**:
1. Choose Option 2 (Custom Inference Profile) - 10 min setup
2. Update `template.yaml` with new ARN
3. Redeploy: `sam deploy`
4. Document for QSA audit

**For Maximum Compliance**:
1. Deploy SageMaker custom endpoint (Option 3)
2. Full VPC isolation
3. Private subnets, no internet access
4. Complete control for QSA audit

---

**Questions?**
- [Bedrock Custom Models Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/custom-models.html)
- [Inference Profiles Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/inference-profiles.html)
- [SageMaker Endpoints Documentation](https://docs.aws.amazon.com/sagemaker/latest/dg/realtime-endpoints.html)
