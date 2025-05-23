#!/usr/bin/env python
import os
from langchain_aws.retrievers.bedrock import AmazonKnowledgeBasesRetriever
from langchain_aws.chat_models import ChatBedrock
from langchain.schema.runnable import RunnablePassthrough
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage
from langchain.schema.runnable import Runnable

# 1 ENV ──────────────────────────────────────────────
KB_ID = os.environ["KB_ID"]
REGION = os.getenv("AWS_REGION", "ap-northeast-1")

# 2 Components ──────────────────────────────────────
retriever = AmazonKnowledgeBasesRetriever(
    knowledge_base_id=KB_ID, region_name=REGION, min_score_confidence=0.5
)

llm = ChatBedrock(
    model="anthropic.claude-3-haiku-20240307-v1:0",
    region="ap-northeast-1",
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

if __name__ == "__main__":
    import argparse, textwrap

    p = argparse.ArgumentParser()
    p.add_argument("query", help="例えば『今週のクライミングのハイライトは？』")
    args = p.parse_args()

    response = chain.invoke(args.query)
    if hasattr(response, "content"):
        response = response.content
    print(textwrap.fill(response, width=88))
