import os

from langchain_community.retrievers.google_vertex_ai_search import (
    GoogleVertexAISearchRetriever,
)

# from langchain_google_vertexai import ChatVertexAI
from gemini_wrapper import ChatGoogleGemini
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema.runnable import RunnablePassthrough
from langchain_core.messages import HumanMessage
import functions_framework
from flask import jsonify
from google.oauth2 import service_account
from dotenv import load_dotenv

load_dotenv()

creds = service_account.Credentials.from_service_account_file("sa-key.json")

# env
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCP_LOCATION_ID = os.getenv("GCP_LOCATION_ID")
VERTEX_SEARCH_ENGINE_ID = os.getenv("VERTEX_SEARCH_ENGINE_ID")
VERTEX_SEARCH_DATA_STORE_ID = os.getenv("VERTEX_SEARCH_DATA_STORE_ID")
# Vertex AI model name
MODEL_NAME = os.getenv("VERTEX_MODEL_NAME")
VERTEX_MODEL_LOCATION = os.getenv("VERTEX_MODEL_LOCATION")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

print(f"Project ID: {PROJECT_ID}")
print(f"Location ID: {GCP_LOCATION_ID}")
print(f"Search Engine ID: {VERTEX_SEARCH_ENGINE_ID}")
print(f"Data Store ID: {VERTEX_SEARCH_DATA_STORE_ID}")
print(f"Using model: {MODEL_NAME}")
print(f"Using model location: {VERTEX_MODEL_LOCATION}")


# Cloud Functions entry point
@functions_framework.http
def handle_query(request):
    try:
        data = request.get_json()
        query = data.get("query", "")

        if not query:
            return jsonify({"error": "Query is required"}), 400

        # Vertex AI Search retriever
        retriever = GoogleVertexAISearchRetriever(
            project_id=os.environ["GCP_PROJECT_ID"],
            location_id=os.environ["GCP_LOCATION_ID"],
            search_engine_id=os.environ["VERTEX_SEARCH_ENGINE_ID"],
            data_store_id=os.environ["VERTEX_SEARCH_DATA_STORE_ID"],
            top_k=3,
        )

        # Gemini Pro
        # Uncomment the following lines to use Vertex AI with a service account
        # 404 error may occur if the model is not available in the specified location
        # {
        #   "error": "Failed to generate response: 404 Publisher Model projects/website-283612/locations/us-central1/publishers/google/models/gemini-1.5-pro-001 was not found or your project does not have access to it. Please ensure you are using a valid model version. For more information, see: https://cloud.google.com/vertex-ai/generative-ai/docs/learn/model-versions"
        # }
        # llm = ChatVertexAI(
        #     model=MODEL_NAME,
        #     location=VERTEX_MODEL_LOCATION,
        #     project=PROJECT_ID,
        #     credentials=creds,  # Use the service account credentials
        #     temperature=0.7,
        #     max_output_tokens=400,
        #     max_retries=3,  # Retry up to 3 times
        # )
        llm = ChatGoogleGemini(api_key=GEMINI_API_KEY, model=MODEL_NAME)

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

        chain = (
            {
                "context": retriever
                | (lambda docs: [HumanMessage(content=d.page_content) for d in docs]),
                "input": RunnablePassthrough(),
            }
            | prompt
            | llm
        )

        try:
            response = chain.invoke(query)
            print(f"Response: {response}")
        except Exception as e:
            import traceback

            print(f"Error during chain invocation: {traceback.format_exc()}")
            return jsonify({"error": f"Failed to generate response: {str(e)}"}), 500

        docs = retriever.invoke(query)
        sources = [
            {
                "content": doc.page_content,
                "filename": doc.metadata.get("filename", "Unknown filename"),
                "url": doc.metadata.get("link", "Unknown url"),
                "date": doc.metadata.get("date", "Unknown date"),
            }
            for doc in docs
        ]
        answer = response.content if hasattr(response, "content") else response

        return jsonify({"summary": answer, "sources": sources})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
