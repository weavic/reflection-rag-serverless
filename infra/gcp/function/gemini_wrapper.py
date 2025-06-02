## About This Wrapper
#
# - This is a custom wrapper to use Gemini API with LangChain's BaseChatModel.
# - `429 Too Many Requests` occurs persistently when using Gemini API via AI Studio key.
# - Fallback to OpenAI's gpt-4-turbo is recommended until proper support is available.
#
## How to switch to OpenAI
#
# ```python
# Fallback to OpenAI if Gemini keeps returning 429
# from langchain.chat_models import ChatOpenAI
# llm = ChatOpenAI(model="gpt-4-turbo", temperature=0.7)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatResult
from pydantic import Field, PrivateAttr
from backoffretry import requests_retry_session


class ChatGoogleGemini(BaseChatModel):
    api_key: str = Field(...)
    model: str = Field(default="gemini-pro")
    _api_url: str = PrivateAttr()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._api_url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs) -> ChatResult:
        prompt = "\n".join([m.content for m in messages if isinstance(m, HumanMessage)])
        body = {"contents": [{"parts": [{"text": prompt}]}]}

        response = requests_retry_session().post(
            self._api_url,
            headers={"Content-Type": "application/json"},
            json=body,
        )
        response.raise_for_status()
        result = response.json()

        content = result["candidates"][0]["content"]["parts"][0]["text"]
        return ChatResult(generations=[AIMessage(content=content)])

    @property
    def _llm_type(self) -> str:
        return "chat-google-gemini"
