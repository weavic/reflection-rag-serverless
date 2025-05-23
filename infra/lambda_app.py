# infra/lambda_app.py

import os
import json
from langchain_aws.retrievers.bedrock import AmazonKnowledgeBasesRetriever
from langchain_aws.chat_models import ChatBedrock
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.runnable import Runnable

KB_ID = os.environ["KB_ID"]
REGION = os.getenv("AWS_REGION", "ap-northeast-1")
MODEL_ID = os.getenv("MODEL_ID", "anthropic.claude-v2:1")
INFERENCE_PROFILE_ARN = os.getenv("INFERENCE_PROFILE_ARN")  # 必要な場合のみ

retriever = AmazonKnowledgeBasesRetriever(
    knowledge_base_id=KB_ID,
    region_name=REGION,
    min_score_confidence=0.5,
)

llm = ChatBedrock(
    model=MODEL_ID,
    region=REGION,
)

SYSTEM_TEMPLATE = (
    "You are an assistant that helps Hiroki reflect on his daily notes.\n"
    "Use the retrieved context to answer the user's question in Japanese."
)

prompt = ChatPromptTemplate.from_messages(
    [("system", SYSTEM_TEMPLATE), MessagesPlaceholder("context"), ("human", "{input}")]
)

chain: Runnable = (
    {
        "context": retriever
        | (lambda docs: [HumanMessage(content=d.page_content) for d in docs]),
        "input": RunnablePassthrough(),
    }
    | prompt
    | llm
)


def lambda_handler(event, context):
    """Lambdaエントリポイント: { "query": ... } を受け取り要約を返す"""

    try:
        if "body" in event and isinstance(event["body"], str):
            # API Gateway経由のときはbodyがJSON文字列になる
            body = json.loads(event["body"])
        else:
            body = event

        query = body.get("query") or ""
        if not query:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "No query provided"}),
            }

        response = chain.invoke(query)
        # AIMessageなら.content、それ以外ならstr
        summary = response.content if hasattr(response, "content") else response

        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"summary": summary}),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }
