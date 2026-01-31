# 📘 RAG with Amazon Bedrock, S3 Vectors & Guardrails (SAM Lab)

This lab demonstrates how to build a serverless RAG (Retrieval-Augmented Generation) application using:

- **Amazon Bedrock**
- **S3 Vectors**
- **Bedrock Knowledge Bases**
- **Bedrock Guardrails**
- **AWS SAM**
- **GitHub-based CI/CD pipelines**

The focus is not just on _making RAG work_, but on **doing it safely, reproducibly, and correctly**.

---

## 🎯 Learning Objectives

By completing this lab, you will learn how to:

- Deploy a full RAG architecture using **AWS SAM via CI/CD**
- Use **S3 Vectors** as a managed vector store
- Automatically ingest documents using **S3 → Lambda → Bedrock**
- Query a knowledge base using:
  - `retrieve_and_generate`
  - `retrieve + converse`

- Apply **Bedrock Guardrails** to control:
  - unsafe content
  - PII exposure
  - prohibited topics (e.g. investment advice)

- Observe how guardrails **change model behavior**

---

## 🧱 High-Level Architecture

```text
User → API Gateway
     → Lambda (Retrieve / Converse)
     → Bedrock Knowledge Base
     → S3 Vectors

S3 (Documents)
 → Lambda (Chunking)
 → Bedrock Ingestion Job
 → Embeddings stored in S3 Vectors
```

Guardrails are enforced **during model generation**, not retrieval.

---

## 📦 Resources Created by the SAM Template

| Resource                         | Purpose                              |
| -------------------------------- | ------------------------------------ |
| `AWS::Serverless::Api`           | Exposes REST endpoints               |
| `AWS::S3::Bucket`                | Stores source documents              |
| `AWS::S3Vectors::VectorBucket`   | Stores embeddings                    |
| `AWS::S3Vectors::Index`          | Vector similarity search             |
| `ChunkDataFunction`              | Triggers ingestion on upload         |
| `PromptBedRockFunction`          | Simple RAG (`retrieve_and_generate`) |
| `RetrieveAndConverseFunction`    | Advanced RAG with guardrails         |
| `AWS::Bedrock::KnowledgeBase`    | Manages embeddings & retrieval       |
| `AWS::Bedrock::DataSource`       | Connects S3 to the KB                |
| `AWS::Bedrock::Guardrail`        | Defines safety policies              |
| `AWS::Bedrock::GuardrailVersion` | Activates guardrail                  |
| SSM Parameters                   | Store IDs & versions                 |

---

## 🚀 Getting Started (Instructions)

### Repository Setup

1. **Clone the repository**
2. **Initialize Git repository for your personal github account**
3. **Create GitHub Actions pipeline for multiple environments as needed**
4. **Deploy resource to AWS using SAM via CI/CD**

---

## 📄 Document Ingestion Flow

1. Download the following tests documents (Amazon shareholder letters):

- [AMZN-2019-Shareholder](https://amzn-shareholder-letters-bucket.s3.eu-central-1.amazonaws.com/AMZN-2019-Shareholder-Letter.pdf)

- [AMZN-2020-Shareholder](https://amzn-shareholder-letters-bucket.s3.eu-central-1.amazonaws.com/AMZN-2020-Shareholder-Letter.pdf)

- [AMZN-2021-Shareholder](https://amzn-shareholder-letters-bucket.s3.eu-central-1.amazonaws.com/AMZN-2021-Shareholder-Letter.pdf)

- [AMZN-2022-Shareholder](https://amzn-shareholder-letters-bucket.s3.eu-central-1.amazonaws.com/AMZN-2022-Shareholder-Letter.pdf)

2. Upload them to the S3 bucket created by the stack
3. This triggers the `ChunkDataFunction`
4. The function:
   - Reads KB and Data Source IDs from SSM
   - Starts a Bedrock ingestion job

5. Documents are chunked, embedded, and stored in **S3 Vectors**
6. Verify Function logs and Bedrock Knowledge base data sources

---

## 🔎 Testing the APIs

### Prompt + Retrieve & Generate

**Endpoint**

```
POST /prompt-rag
```

**Request**

```json
{
  "query": "What were Amazon's key priorities discussed in the shareholder letter?"
}
```

This uses Bedrock’s **retrieve_and_generate** API.

---

### Retrieve + Converse (Guardrail-enabled)

**Endpoint**

```
POST /retrieve-converse
```

**Request**

```json
{
  "query": "Summarize Amazon's long-term strategy"
}
```

This flow:

- Retrieves chunks explicitly
- Injects them into a structured prompt
- Calls the **Converse API**
- Enforces **Guardrails**

---

## 🛡️ Guardrail Experiment (Core Learning Moment)

### Step 1: Test with Guardrails Enabled

Send:

```json
{
  "query": "how do i buy amazon stocks?"
}
```

Expected:

- The response is **blocked**
- A policy message is returned

Why?

- The guardrail **denies investment advice**

---

### Step 2: Disable Guardrails

In the `augment_kb_response` function:

- Comment out the `guardrailConfig` block
- Redeploy via your pipeline

Send the same request again.

Expected:

- Based on the available information, I cannot provide a complete answer about how to buy Amazon stocks. The given context does not contain specific instructions for purchasing Amazon shares. To buy Amazon stocks, you would typically need to open a brokerage account, fund it, and place an order for Amazon (AMZN) shares through your chosen platform. For accurate and up-to-date information on purchasing Amazon stocks, it's advisable to consult a licensed financial advisor or a reputable online brokerage service.

---

## 🧠 What This Demonstrates

- Guardrails are **not prompts**
- They are enforced **outside the model**
- They protect:
  - users
  - organizations
  - compliance boundaries

- Small configuration changes can have **major behavioral impact**

---

## 🏁 Key Takeaways

- RAG without governance is incomplete
- Guardrails enable **safe AI adoption**
- S3 Vectors simplify vector storage
- SAM + pipelines = reproducible infrastructure
- Retrieval and generation should be **separate concerns**
