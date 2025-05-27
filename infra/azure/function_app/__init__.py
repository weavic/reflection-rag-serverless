import logging
import os
import json
import azure.functions as func
from openai import AzureOpenAI
from azure.search.documents import SearchClient
from azure.core.credentials import AzureKeyCredential

# Environment variables
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
        search_client = SearchClient(
            endpoint=AZURE_SEARCH_ENDPOINT,
            index_name=AZURE_SEARCH_INDEX,
            credential=AzureKeyCredential(AZURE_SEARCH_API_KEY),
        )
        results = search_client.search(query, top=3)
        context = "\n".join([doc["content"] for doc in results if "content" in doc])

        # Call Azure OpenAI
        client = AzureOpenAI(
            api_key=os.environ["AZURE_OPENAI_API_KEY"],
            api_version="2024-10-21",
            azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        )

        response = client.chat.completions.create(
            model=AZURE_OPENAI_DEPLOYMENT,
            messages=[
                {
                    "role": "system",
                    "content": "ユーザーの記録を振り返って要約してください。",
                },
                {"role": "user", "content": f"情報: {context}\n質問: {query}"},
            ],
            temperature=0.7,
            max_tokens=400,
        )

        answer = response.choices[0].message["content"]
        return func.HttpResponse(json.dumps({"summary": answer}), status_code=200)
    except Exception as e:
        logging.exception("Function error")
        return func.HttpResponse(str(e), status_code=500)
