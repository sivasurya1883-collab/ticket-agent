from __future__ import annotations

import re
import certifi
import httpx
from langchain_openai import ChatOpenAI

from openai import APIConnectionError

from .config import LLM_API_KEY, LLM_BASE_URL, LLM_ENABLED, LLM_MODEL, LLM_SSL_VERIFY, LLM_TIMEOUT_SECONDS


class LLMNotConfigured(RuntimeError):
    pass


class LLMConnectionError(RuntimeError):
    pass


def sanitize_plain_text(text: str) -> str:
    s = (text or "").strip()

    s = re.sub(r"```[\s\S]*?```", "", s)
    s = re.sub(r"\$\$[\s\S]*?\$\$", "", s)
    s = re.sub(r"\\\[[\s\S]*?\\\]", "", s)
    s = re.sub(r"(?m)^\s{0,3}#{1,6}\s+", "", s)
    s = re.sub(r"\*\*(.*?)\*\*", r"\1", s)
    s = re.sub(r"\*(.*?)\*", r"\1", s)
    s = re.sub(r"(?m)^\s*[-*]\s+", "", s)
    s = re.sub(r"(?m)^\s*\d+\.\s+", "", s)
    s = re.sub(r"[\t ]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def get_chat_llm(*, temperature: float = 0.0) -> ChatOpenAI:
    if not LLM_ENABLED:
        raise LLMNotConfigured("LLM is disabled")

    if not LLM_API_KEY:
        raise LLMNotConfigured("LLM_API_KEY not configured")

    verify = certifi.where() if LLM_SSL_VERIFY else False
    timeout = httpx.Timeout(timeout=LLM_TIMEOUT_SECONDS)
    http_async_client = httpx.AsyncClient(verify=verify, timeout=timeout)

    return ChatOpenAI(
        base_url=LLM_BASE_URL,
        model=LLM_MODEL,
        api_key=LLM_API_KEY,
        temperature=temperature,
        http_async_client=http_async_client,
    )


def _client() -> ChatOpenAI:
    return get_chat_llm(temperature=0.0)


async def generate_fd_explanation(prompt: str) -> str:
    llm = _client()
    try:
        resp = await llm.ainvoke(prompt)
        return sanitize_plain_text(str(resp.content))
    except APIConnectionError as e:
        raise LLMConnectionError("LLM connection error") from e
    finally:
        http_client = getattr(llm, "http_async_client", None)
        if http_client is not None:
            try:
                await http_client.aclose()
            except Exception:
                pass
