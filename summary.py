#!/usr/bin/env python
import logging
import os
from langchain_aws.retrievers.bedrock import AmazonKnowledgeBasesRetriever
from langchain_aws.chat_models import ChatBedrock
from langchain.schema.runnable import RunnablePassthrough
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage
from langchain_core.retrievers import BaseRetriever
from langchain_core.language_models import BaseLanguageModel
from langchain.schema.runnable import Runnable
from langchain_community.retrievers.azure_ai_search import AzureAISearchRetriever
from langchain_openai import AzureChatOpenAI
from langchain_core.utils import secret_from_env

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# 1 ENV ──────────────────────────────────────────────
# for AWS Lambda, set the environment variables in the Lambda console or via SAM/CloudFormation
KB_ID = os.environ["KB_ID"]
REGION = os.getenv("AWS_REGION", "ap-northeast-1")

# for Azure Function, set the environment variables in the Azure portal or via local.settings.json
AZURE_AI_SEARCH_SERVICE_NAME = os.environ["AZURE_AI_SEARCH_SERVICE_NAME"]
AZURE_OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
AZURE_OPENAI_API_KEY = os.environ["AZURE_OPENAI_API_KEY"]
AZURE_SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
AZURE_SEARCH_API_KEY = os.environ["AZURE_SEARCH_API_KEY"]
AZURE_SEARCH_INDEX = os.environ["AZURE_SEARCH_INDEX"]
AZURE_OPENAI_DEPLOYMENT = os.environ["AZURE_OPENAI_DEPLOYMENT"]

# 2. constants ──────────────────────────────────────────────
SYSTEM_TEMPLATE = (
    "You are an assistant that helps Hiroki reflect on his daily notes.\n"
    "Use the retrieved context to answer the user's question in Japanese."
)

prompt = ChatPromptTemplate.from_messages(
    [("system", SYSTEM_TEMPLATE), MessagesPlaceholder("context"), ("human", "{input}")]
)

if __name__ == "__main__":
    import argparse, textwrap

    p = argparse.ArgumentParser()
    p.add_argument("query", help="例えば『今週のクライミングのハイライトは？』")
    p.add_argument(
        "--azure", action="store_true", help="Azure AI Searchを使用する場合は指定"
    )
    args = p.parse_args()

    # CLI優先で切り替え
    use_azure = args.azure or os.getenv("USE_AZURE", "false").lower() == "true"

    retriever: BaseRetriever
    llm: BaseLanguageModel

    # retriever/llm再定義（最初に全部env読むとエラーになるため）
    if use_azure:
        retriever = AzureAISearchRetriever(
            service_name=AZURE_AI_SEARCH_SERVICE_NAME,
            index_name=AZURE_SEARCH_INDEX,
            api_key=AZURE_SEARCH_API_KEY,
            top_k=3,
        )
        llm = AzureChatOpenAI(
            api_key=secret_from_env("AZURE_OPENAI_API_KEY")(),
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_version="2024-10-21",
            model=AZURE_OPENAI_DEPLOYMENT,
            temperature=0.7,
            max_tokens=400,
        )
    else:
        retriever = AmazonKnowledgeBasesRetriever(
            knowledge_base_id=KB_ID, region_name=REGION, min_score_confidence=0.5
        )
        llm = ChatBedrock(
            model="anthropic.claude-3-haiku-20240307-v1:0",
            region="ap-northeast-1",
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

    response = chain.invoke(args.query)
    answer = response.content if hasattr(response, "content") else response

    # ドキュメント型ごとに安全に取り出し
    docs = retriever.invoke(args.query)
    sources = []
    for doc in docs:
        if hasattr(doc, "metadata"):
            meta = doc.metadata
        elif hasattr(doc, "__dict__"):
            meta = getattr(doc, "metadata", {})
        else:
            meta = {}
        sources.append(
            {
                "content": getattr(doc, "page_content", str(doc)),
                "filename": meta.get("metadata_storage_name", "Unknown filename"),
                "url": meta.get("metadata_storage_path", "Unknown url"),
                "date": meta.get("metadata_storage_last_modified", "Unknown date"),
            }
        )

    logging.info(f"Generated answer: {answer}")
    logging.info(f"Retrieved context: {docs}, sources: {sources}")
