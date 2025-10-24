# Architecture Diagrams (Mermaid Format)

## Call Flow Sequence Diagram

```mermaid
sequenceDiagram
    participant Caller
    participant Connect as Amazon Connect
    participant Lambda as AWS Lambda
    participant S3 as S3 Audit Logs
    participant Stripe
    participant Bedrock as Amazon Bedrock
    
    Caller->>Connect: Dials phone number
    Connect->>Caller: "Welcome! Enter card number..."
    Caller->>Connect: DTMF: 4242424242424242#
    Connect->>Caller: "Enter expiry MMYY..."
    Caller->>Connect: DTMF: 1225#
    Connect->>Caller: "Enter CVV..."
    Caller->>Connect: DTMF: 123#
    
    Connect->>Lambda: Invoke with CHD
    
    Note over Lambda: IMMEDIATE MASKING<br/>4242... → ****4242
    
    Lambda->>S3: Store masked data (encrypted)
    S3-->>Lambda: ✓ Stored
    
    Lambda->>Stripe: Tokenize card
    Stripe-->>Lambda: tok_xxxxx (token)
    
    Note over Lambda: Build safe prompt<br/>"Visa ending ****4242"
    
    Lambda->>Bedrock: Safe prompt (NO CHD)
    Bedrock-->>Lambda: "Payment validated!"
    
    Lambda->>Connect: Response + token
    Connect->>Caller: Polly speaks: "Thank you!"
    Caller->>Connect: Call ends
```

---

## Data Flow Diagram

```mermaid
flowchart TD
    A[Caller Voice] -->|TLS 1.2+| B[Amazon Connect]
    B -->|HTTPS| C[AWS Lambda]
    
    C -->|1. Mask CHD| D{CHD Masking}
    D -->|****1111| E[Masked Data]
    
    E -->|2. Store| F[S3 + KMS]
    E -->|3. Tokenize| G[Stripe API]
    E -->|4. AI Prompt| H[Bedrock Mistral]
    
    G -->|tok_xxxxx| C
    H -->|Safe Response| C
    
    C -->|Response| B
    B -->|Polly TTS| A
    
    style D fill:#ff6b6b
    style E fill:#51cf66
    style F fill:#4dabf7
    style G fill:#845ef7
    style H fill:#ffd43b
```

---

## Security Layers Diagram

```mermaid
flowchart LR
    subgraph Layer1[Network Security]
        A1[TLS 1.2+]
        A2[HTTPS Only]
        A3[VPC Isolation]
    end
    
    subgraph Layer2[Data Masking]
        B1[Immediate CHD Mask]
        B2[Tokenization]
        B3[No CHD to AI]
    end
    
    subgraph Layer3[Encryption]
        C1[S3 + KMS]
        C2[SSM Secrets]
        C3[CloudWatch Encrypted]
    end
    
    subgraph Layer4[Access Control]
        D1[IAM Least Privilege]
        D2[MFA Required]
        D3[Audit Logging]
    end
    
    Layer1 --> Layer2
    Layer2 --> Layer3
    Layer3 --> Layer4
    
    style Layer1 fill:#e3f2fd
    style Layer2 fill:#f3e5f5
    style Layer3 fill:#e8f5e9
    style Layer4 fill:#fff3e0
```

---

## PCI Compliance Boundary

```mermaid
flowchart TD
    subgraph Out[Out of Scope - PCI DSS]
        O1[Bedrock AI<br/>No CHD]
        O2[CloudWatch<br/>Masked Only]
        O3[S3 Logs<br/>Encrypted Masked]
    end
    
    subgraph In[In Scope - Lambda Only]
        I1[Lambda Handler<br/>Touches Raw CHD]
        I2[CHD Masking Function]
        I3[Stripe Tokenization]
    end
    
    subgraph Third[Third-Party - Stripe's Scope]
        T1[Stripe Tokens]
        T2[Payment Processing]
    end
    
    In --> |Masked Data| Out
    In --> |Raw CHD| Third
    Third --> |Tokens Only| In
    
    style In fill:#ff6b6b
    style Out fill:#51cf66
    style Third fill:#4dabf7
```

---

## Infrastructure Architecture

```mermaid
graph TB
    subgraph AWS Cloud
        subgraph VPC[VPC Future]
            Lambda[AWS Lambda<br/>Python 3.11<br/>512MB/60s]
        end
        
        Connect[Amazon Connect<br/>IVR + DTMF]
        Bedrock[Amazon Bedrock<br/>Mistral 7B]
        S3[S3 Bucket<br/>Audit Logs]
        KMS[AWS KMS<br/>Encryption Key]
        SSM[SSM Parameter<br/>Stripe Secret]
        CW[CloudWatch<br/>Logs + Alarms]
    end
    
    subgraph External
        Stripe[Stripe API<br/>Tokenization]
        Caller[Phone Caller]
    end
    
    Caller -->|Voice| Connect
    Connect -->|Invoke| Lambda
    Lambda -->|Tokenize| Stripe
    Lambda -->|AI Prompt| Bedrock
    Lambda -->|Store| S3
    Lambda -->|Read Secret| SSM
    Lambda -->|Logs| CW
    S3 -->|Encrypt| KMS
    
    style Lambda fill:#ff6b6b
    style Connect fill:#4dabf7
    style Bedrock fill:#ffd43b
    style S3 fill:#51cf66
    style Stripe fill:#845ef7
```

---

## Deployment Pipeline

```mermaid
flowchart LR
    A[Local Dev] -->|sam build| B[Build Lambda]
    B -->|sam local invoke| C[Local Test]
    C -->|sam deploy| D[CloudFormation]
    D -->|Create| E[Lambda Function]
    D -->|Create| F[S3 Bucket]
    D -->|Create| G[KMS Key]
    D -->|Create| H[IAM Roles]
    
    E --> I[Connect Integration]
    I --> J[Phone Testing]
    J --> K[Production]
    
    style A fill:#e3f2fd
    style C fill:#fff3e0
    style D fill:#f3e5f5
    style K fill:#51cf66
```

---

## Cost Breakdown Flow

```mermaid
flowchart TD
    A[Total Cost: $3.31/month POC]
    
    A --> B[Amazon Connect<br/>$1.62<br/>30 calls × 3min]
    A --> C[Bedrock Mistral<br/>$0.68<br/>30 × 150 tokens]
    A --> D[Lambda<br/>Free Tier<br/>30 invocations]
    A --> E[S3 + KMS<br/>$1.01<br/>Storage + Key]
    
    style A fill:#ffd43b
    style B fill:#4dabf7
    style C fill:#845ef7
    style D fill:#51cf66
    style E fill:#ff6b6b
```

---

## Monitoring Dashboard

```mermaid
flowchart TD
    subgraph Metrics
        M1[Lambda Duration]
        M2[Lambda Errors]
        M3[Bedrock Tokens]
        M4[Stripe Success Rate]
        M5[Connect Call Volume]
    end
    
    subgraph Alarms
        A1[Error > 1/min]
        A2[Duration > 25s]
        A3[Throttles > 5/hr]
    end
    
    subgraph Actions
        AC1[SNS Alert]
        AC2[Auto-Scale]
        AC3[Page Oncall]
    end
    
    M2 -->|Trigger| A1
    M1 -->|Trigger| A2
    M3 -->|Trigger| A3
    
    A1 --> AC1
    A2 --> AC2
    A3 --> AC3
    
    style Metrics fill:#e3f2fd
    style Alarms fill:#fff3e0
    style Actions fill:#ff6b6b
```

---

## To view these diagrams:

1. **GitHub**: Automatically renders Mermaid
2. **VS Code**: Install "Markdown Preview Mermaid Support" extension
3. **Online**: Copy to https://mermaid.live/

These diagrams provide visual representation of the PCI-compliant architecture.
