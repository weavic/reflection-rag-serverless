import logging
import os
import json
import azure.functions as func
from langchain_community.retrievers.azure_ai_search import AzureAISearchRetriever
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema.runnable import RunnablePassthrough, Runnable
from langchain_core.messages import HumanMessage
from langchain_core.utils import secret_from_env

# Environment variables
AZURE_AI_SEARCH_SERVICE_NAME = os.environ["AZURE_AI_SEARCH_SERVICE_NAME"]
AZURE_OPENAI_ENDPOINT = os.environ["AZURE_OPENAI_ENDPOINT"]
AZURE_OPENAI_API_KEY = os.environ["AZURE_OPENAI_API_KEY"]
AZURE_SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
AZURE_SEARCH_API_KEY = os.environ["AZURE_SEARCH_API_KEY"]
AZURE_SEARCH_INDEX = os.environ["AZURE_SEARCH_INDEX"]
AZURE_OPENAI_DEPLOYMENT = os.environ["AZURE_OPENAI_DEPLOYMENT"]


def main(req: func.HttpRequest) -> func.HttpResponse:
    try:
        body = req.get_json()
        query = body.get("query", "")
        if not query:
            return func.HttpResponse("Query not provided", status_code=400)

        # Retrieve documents from Azure AI Search
        retriever = AzureAISearchRetriever(
            service_name=AZURE_AI_SEARCH_SERVICE_NAME,
            index_name=AZURE_SEARCH_INDEX,
            api_key=AZURE_SEARCH_API_KEY,
            top_k=3,  # Retrieve top 3 documents
        )

        llm = AzureChatOpenAI(
            api_key=secret_from_env("AZURE_OPENAI_API_KEY")(),
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_version="2024-10-21",
            model=AZURE_OPENAI_DEPLOYMENT,
            temperature=0.7,
            max_tokens=400,
        )

        SYSTEM_TEMPLATE = (
            "You are an assistant that helps Hiroki reflect on his daily notes.\n"
            "Use the retrieved context to answer the user's question in Japanese."
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_TEMPLATE),
                MessagesPlaceholder("context"),
                ("human", "{input}"),
            ]
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
        response = chain.invoke(query)

        # Extract sources from retrieved documents
        docs = retriever.invoke(query)
        sources = [
            {
                "content": doc.page_content,
                "filename": doc.metadata.get(
                    "metadata_storage_name", "Unknown filename"
                ),
                "url": doc.metadata.get("metadata_storage_path", "Unknown url"),
                "date": doc.metadata.get(
                    "metadata_storage_last_modified", "Unknown date"
                ),
            }
            for doc in docs
        ]
        answer = response.content if hasattr(response, "content") else response
        logging.info(f"Generated answer: {answer}")
        logging.info(f"Retrieved context: {docs}, sources: {sources}")

        return func.HttpResponse(
            json.dumps({"summary": answer, "sources": sources}, ensure_ascii=False),
            status_code=200,
        )
    except Exception as e:
        logging.exception("Function error")
        return func.HttpResponse(str(e), status_code=500)
