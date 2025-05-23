# Recall API - Personal Reflection RAG Serverless API

> **Summary:**  
> AWS Bedrock × LangChain を活用した「個人の知識リフレクションAPI」PoC。  
> S3 + KnowledgeBase + Bedrock + Lambda + API Gateway の最小サーバーレス構成。

---

## アーキテクチャ概要

- **API Gateway**（/recall, POST）  
  ↓  
- **Lambda**（Python, LangChain, Bedrock連携, RAG推論）  
  ↓  
- **Bedrock Knowledge Base**（個人の記録/日記/ノート）  
  ↓  
- **Bedrock LLM**（Claude 3/3.5/Haiku等）

### アーキテクチャ図

:::mermaid
flowchart TD
    User["User (curl/HTTP Client)"]
        -->|POST /recall| APIGW["API Gateway"]
    APIGW --> Lambda["AWS Lambda<br> (lambda_app.py)"]
    Lambda --> BedrockKB["Bedrock Knowledge Base"]
    Lambda --> BedrockLLM["Bedrock LLM<br> (Claude/他)"]
    BedrockKB --> S3["S3 (日記/素材データ)"]

    BedrockLLM -.->|"Summary<br>（要約応答）"| Lambda
    BedrockKB -.->|"Doc retrieval<br>（検索）"| Lambda

    classDef ext fill:#e3fcef,stroke:#4d8076,stroke-width:2px;
    classDef aws fill:#fdf6e3,stroke:#d19a66,stroke-width:2px;
    class APIGW,Lambda,BedrockKB,BedrockLLM,S3 aws;
:::

## セットアップ & デプロイ手順

### 1. 必要パッケージ

    ```bash
    pip install -r requirements.txt
    # sam cli（未インストールなら）
    brew install aws/tap/aws-sam-cli
    ```

### 2. AWSリソース準備（初回のみ）

- BedrockでKnowledgeBase作成し、KnowledgeBaseIdを控える
- モデルID (ModelId) を確認（例: anthropic.claude-3-haiku-20240307-v1:0）

### 3. デプロイ

    ```bash
    sam build
    sam deploy --guided \
    --stack-name recall-api-stack \
    --parameter-overrides \
        KnowledgeBaseId=<YourKBID> \
        ModelId=<YourModelID>
    ```

### 4. エンドポイント情報取得

- AWSコンソール API Gateway → Stages → Prod → Invoke URLを確認

### 5. API利用

#### API仕様

    ```bash
    POST https://<api-id>.execute-api.ap-northeast-1.amazonaws.com/Prod/recall
    Content-Type: application/json
    {
    "query": "ここ１週間のクライミングのハイライトは？"
    }
    ```

##### Request例

    ```bash
    curl -X POST "https://<api-id>.execute-api.ap-northeast-1.amazonaws.com/Prod/recall" \
    -H "Content-Type: application/json" \
    -d '{"query": "ここ１週間のクライミングのハイライトは？"}'
    ```

##### Response例

    ```bash
    {
    "summary": "ここ1週間のクライミングのハイライトは以下の通りです: ..."
    }
    ```
