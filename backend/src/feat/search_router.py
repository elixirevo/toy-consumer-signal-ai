from __future__ import annotations

import asyncio
import json
from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.models.pipeline import AnalyzeRequest, RouterOptions, RoutingStrategy
from src.utils.agent import llm_json_response_async

RouterInput = AnalyzeRequest

ROUTER_SYSTEM_PROMPT = """
너는 AI 소비 심리 분석기의 Router LLM이다.
사용자 입력을 보고 리뷰 수집 전략을 JSON 객체 하나로만 반환해야 한다.

반드시 지켜야 할 규칙:
- 출력은 JSON 객체만 반환한다.
- 설명, 코드블록, 마크다운을 포함하지 않는다.
- sources는 검색 우선순위가 높은 순서대로 반환한다.
- review_count_per_source는 정수다.
- depth는 "quick" 또는 "deep"만 허용한다.
- language는 "ko", "en", "both" 중 하나만 허용한다.

라우팅 전략 규칙:
- 국내 브랜드 또는 한국 이커머스 중심 제품이면 naver_shopping, coupang 우선
- 글로벌 브랜드 또는 해외 제품이면 reddit, amazon 추가
- 화장품 카테고리면 oliveyoung 추가 가능
- 가전 카테고리면 danawa 추가 가능
- 링크가 있으면 링크 정보도 참고하되 제품명 기준 전략을 반환
- quick면 소스 수와 리뷰 수를 보수적으로
- deep면 소스 수와 리뷰 수를 넓게
""".strip()


def _build_router_prompt(user_input: AnalyzeRequest) -> str:
    input_payload = json.dumps(user_input.model_dump(), ensure_ascii=False, indent=2)

    return f"""
{ROUTER_SYSTEM_PROMPT}

입력 데이터:
{input_payload}

반환 스키마:
{{
  "product_name": "string",
  "product_category": "string",
  "brand": "string",
  "sources": ["naver_shopping", "coupang"],
  "review_count_per_source": 30,
  "depth": "quick",
  "language": "ko",
  "date_range": "3months"
}}
""".strip()


async def route_search_strategy(user_input: AnalyzeRequest) -> RoutingStrategy:
    prompt = _build_router_prompt(user_input)
    payload = await llm_json_response_async(prompt, model="gpt-4o-mini")
    return RoutingStrategy.model_validate(payload)


async def search_router(user_input: AnalyzeRequest | dict | str) -> RoutingStrategy:
    if isinstance(user_input, str):
        validated_input = AnalyzeRequest(raw_query=user_input)
    elif isinstance(user_input, dict):
        validated_input = AnalyzeRequest.model_validate(user_input)
    else:
        validated_input = user_input

    return await route_search_strategy(validated_input)


if __name__ == "__main__":
    sample_input = AnalyzeRequest(
        raw_query="갤럭시 S25 울트라 리뷰 분석해줘",
        options=RouterOptions(depth="deep", date_range="3months"),
    )
    print(asyncio.run(search_router(sample_input)).model_dump_json(indent=2))
