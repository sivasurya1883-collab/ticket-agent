import httpx

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from .config import settings


_http_client: httpx.Client | None = None


def _get_http_client() -> httpx.Client:
    global _http_client
    if _http_client is None:
        _http_client = httpx.Client(verify=False)
    return _http_client


def get_chat_llm() -> ChatOpenAI:
    settings.validate()
    base_url = settings.openai_base_url or None
    return ChatOpenAI(
        base_url=base_url,
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        http_client=_get_http_client(),
    )


def get_embeddings() -> OpenAIEmbeddings:
    settings.validate()
    base_url = settings.openai_base_url or None
    return OpenAIEmbeddings(
        base_url=base_url,
        model=settings.openai_embeddings_model,
        api_key=settings.openai_api_key,
        http_client=_get_http_client(),
    )
