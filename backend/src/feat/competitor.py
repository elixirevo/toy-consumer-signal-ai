from __future__ import annotations

import asyncio
import json

from src.models.pipeline import (
    AggregatedReport,
    ComparisonReport,
    CompetitorCandidateList,
    ProductAnalysisArtifacts,
    RoutingStrategy,
)
from src.utils.agent import llm_json_response_async, llm_search_async


def build_competitor_queries(
    strategy: RoutingStrategy,
    aggregated_report: AggregatedReport,
) -> list[str]:
    weakness_hint = ", ".join(aggregated_report.weaknesses[:2]) or "단점"
    return [
        f"{strategy.product_name} 대안 추천",
        f"{strategy.product_category} 추천 {weakness_hint}",
        f"{strategy.product_name} 경쟁 제품 비교",
    ]


async def discover_competitor_candidates(
    strategy: RoutingStrategy,
    aggregated_report: AggregatedReport,
) -> CompetitorCandidateList:
    queries = build_competitor_queries(strategy, aggregated_report)
    search_prompt = f"""
너는 경쟁 제품 탐색 워커다.
OpenAI 웹 검색을 사용해서 현재 제품의 대안 후보를 찾고 텍스트로 정리하라.

규칙:
- JSON으로 답하지 말고 사람이 읽을 수 있는 텍스트로 정리한다.
- 가격, 가성비, 가심비, 품질 관점에서 대안이 될 만한 후보를 적는다.
- 현재 제품명은 후보에서 제외한다.

현재 제품:
{json.dumps(strategy.model_dump(), ensure_ascii=False, indent=2)}

제품 평가:
{json.dumps(aggregated_report.model_dump(), ensure_ascii=False, indent=2)}

검색 질의:
{json.dumps(queries, ensure_ascii=False, indent=2)}
""".strip()

    try:
        search_text = await llm_search_async(search_prompt, model="gpt-4.1")
    except Exception:
        return CompetitorCandidateList(queries=queries, candidates=[])

    if not search_text.strip():
        return CompetitorCandidateList(queries=queries, candidates=[])

    structure_prompt = f"""
너는 경쟁 제품 후보 추출기다.
아래 웹 검색 결과 텍스트에서 현재 제품의 대안 후보를 뽑아 JSON 객체 하나로 반환하라.

규칙:
- 출력은 JSON 객체 하나만 반환한다.
- queries는 입력 queries를 그대로 넣는다.
- candidates는 제품명 문자열 배열이다.
- 너무 비슷한 중복 후보는 제거한다.
- 최대 3개 후보만 반환한다.
- 현재 제품명은 candidates에 포함하지 않는다.

현재 제품명:
{strategy.product_name}

queries:
{json.dumps(queries, ensure_ascii=False, indent=2)}

검색 결과 텍스트:
{search_text}

반환 스키마:
{{
  "queries": ["질의"],
  "candidates": ["후보 제품명"]
}}
""".strip()

    try:
        payload = await llm_json_response_async(structure_prompt, model="gpt-4o-mini")
    except Exception:
        return CompetitorCandidateList(queries=queries, candidates=[])

    candidate_list = CompetitorCandidateList.model_validate(payload)
    filtered = [
        candidate
        for candidate in candidate_list.candidates
        if candidate.strip() and candidate.strip() != strategy.product_name
    ]
    return CompetitorCandidateList(queries=queries, candidates=filtered[:3])


async def compare_competitors(
    original: ProductAnalysisArtifacts,
    candidates: list[ProductAnalysisArtifacts],
) -> ComparisonReport:
    prompt = f"""
너는 경쟁 제품 비교 분석기다.
원제품과 후보 제품들의 분석 결과를 기반으로 가격, 가성비, 가심비, 품질을 비교해서 JSON으로만 반환하라.

규칙:
- 출력은 JSON 객체 하나만 반환한다.
- original_product와 competitors는 CompetitorScore 스키마를 따른다.
- overall_score는 0~10 기준
- verdict는 "강력 추천", "추천", "조건부 추천", "비추천" 중 하나
- best_pick은 후보 제품 중 가장 경쟁력 있는 제품명이다.
- best_pick_reason은 한두 문단이 아니라 짧고 명확한 문장으로 작성한다.

원제품:
{json.dumps(original.aggregated_report.model_dump(), ensure_ascii=False, indent=2)}

후보 제품들:
{json.dumps([candidate.aggregated_report.model_dump() for candidate in candidates], ensure_ascii=False, indent=2)}

반환 스키마:
{{
  "original_product": {{
    "product_name": "{original.routing_strategy.product_name}",
    "price": 0,
    "price_score": 0,
    "value_for_money": 0,
    "emotional_value": 0,
    "quality_score": 0,
    "overall_score": 0,
    "pros": ["장점"],
    "cons": ["단점"],
    "verdict": "비추천"
  }},
  "competitors": [
    {{
      "product_name": "후보",
      "price": 0,
      "price_score": 0,
      "value_for_money": 0,
      "emotional_value": 0,
      "quality_score": 0,
      "overall_score": 0,
      "pros": ["장점"],
      "cons": ["단점"],
      "verdict": "추천"
    }}
  ],
  "best_pick": "후보",
  "best_pick_reason": "추천 이유"
}}
""".strip()
    payload = await llm_json_response_async(prompt, model="gpt-4o")
    return ComparisonReport.model_validate(payload)
