import asyncio
import json
import os
import re
from contextvars import ContextVar
from typing import Any

from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

request_api_key: ContextVar[str | None] = ContextVar("request_api_key", default=None)


def set_request_api_key(api_key: str | None):
    return request_api_key.set(api_key)


def reset_request_api_key(token) -> None:
    request_api_key.reset(token)


def _resolve_api_key(explicit_api_key: str | None = None) -> str:
    api_key = explicit_api_key or request_api_key.get() or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OpenAI API 키가 없습니다. 서버 환경변수 OPENAI_API_KEY를 설정하거나 요청에 api_key를 포함하세요."
        )
    return api_key


def _sync_client(explicit_api_key: str | None = None) -> OpenAI:
    return OpenAI(api_key=_resolve_api_key(explicit_api_key))


def _async_client(explicit_api_key: str | None = None) -> AsyncOpenAI:
    return AsyncOpenAI(api_key=_resolve_api_key(explicit_api_key))


def llm_response_sync(prompt: str, model: str = "gpt-4o-mini", api_key: str | None = None) -> str:
    response = _sync_client(api_key).responses.create(
        model=model,
        input=prompt
    )
    return response.output_text


async def llm_response_async(
    prompt: str,
    model: str = "gpt-4o-mini",
    api_key: str | None = None,
) -> str:
    response = await _async_client(api_key).responses.create(
        model=model,
        input=prompt
    )
    return response.output_text

async def llm_search_async(
    prompt: str,
    model: str = "gpt-4o-mini",
    api_key: str | None = None,
) -> str:
    response = await _async_client(api_key).responses.create(
        model=model,
        input=prompt,
        tools=[{"type": "web_search"}],
    )
    return response.output_text

async def run_llm_search_parallel(prompt_details):
    tasks = [
        llm_search_async(item['user_prompt'], item['model'])
        for item in prompt_details
    ]
    responses = await asyncio.gather(*tasks)
    return responses


def extract_json_payload(raw_text: str) -> Any:
    raw_text = raw_text.strip()

    if not raw_text:
        raise ValueError("JSON payload를 추출하지 못했습니다: empty response")

    if raw_text.startswith("```"):
        raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        raw_text = re.sub(r"\s*```$", "", raw_text)

    for candidate in (raw_text,):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    for pattern in (r"\{.*\}", r"\[.*\]"):
        match = re.search(pattern, raw_text, re.DOTALL)
        if not match:
            continue
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            continue

    raise ValueError(f"JSON payload를 추출하지 못했습니다: {raw_text}")


def llm_json_response_sync(
    prompt: str,
    model: str = "gpt-4o-mini",
    api_key: str | None = None,
) -> Any:
    return extract_json_payload(llm_response_sync(prompt, model=model, api_key=api_key))


async def llm_json_response_async(
    prompt: str,
    model: str = "gpt-4o-mini",
    api_key: str | None = None,
) -> Any:
    raw_response = await llm_response_async(prompt, model=model, api_key=api_key)
    return extract_json_payload(raw_response)


async def llm_search_json_async(
    prompt: str,
    model: str = "gpt-4o-mini",
    api_key: str | None = None,
) -> Any:
    raw_response = await llm_search_async(prompt, model=model, api_key=api_key)
    return extract_json_payload(raw_response)
