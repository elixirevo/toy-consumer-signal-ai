from __future__ import annotations

import json

from src.models.pipeline import (
    AggregatedReport,
    ComplaintResult,
    PurchaseReasonResult,
    RoutingStrategy,
    SentimentResult,
)
from src.utils.agent import llm_json_response_async


AGGREGATOR_PROMPT = """
너는 AI 소비 심리 분석기의 Aggregator LLM이다.
감정분석, 구매이유, 불만 분석 결과를 종합해서 최종 제품 평가를 JSON으로 반환한다.

판정 규칙:
- overall_score는 0.0 ~ 10.0
- verdict는 "긍정", "중립", "네거티브" 중 하나
- recommendation은 "구매 추천", "조건부 추천", "비추천" 중 하나
- recommendation과 verdict는 반드시 user_context 기준으로 판단한다.
- 특별한 user_context가 없을 때만 일반 사용자 기준으로 판단한다.
- 사용자의 priorities / constraints / usage_context에 맞는지 여부를 강점과 약점에 반영한다.
- overall_score < 5.5 이거나 불만 severity가 high면 find_competitor는 true
- sentiment score < -0.2면 find_competitor는 true
- 사용자 상황에 핵심적인 constraint를 충족하지 못하면 find_competitor는 true
- summary는 "이 사용자에게 왜 추천/비추천인지"가 드러나게 작성한다.

출력은 JSON 객체 하나만 반환한다.
""".strip()


async def aggregate_report(
    routing_strategy: RoutingStrategy,
    sentiment_result: SentimentResult,
    purchase_result: PurchaseReasonResult,
    complaint_result: ComplaintResult,
) -> AggregatedReport:
    prompt = f"""
{AGGREGATOR_PROMPT}

제품 정보:
{json.dumps(routing_strategy.model_dump(), ensure_ascii=False, indent=2)}

감정 분석:
{json.dumps(sentiment_result.model_dump(), ensure_ascii=False, indent=2)}

구매 이유 분석:
{json.dumps(purchase_result.model_dump(), ensure_ascii=False, indent=2)}

불만 분석:
{json.dumps(complaint_result.model_dump(), ensure_ascii=False, indent=2)}

반환 스키마:
{{
  "product_name": "{routing_strategy.product_name}",
  "overall_score": 6.4,
  "verdict": "중립",
  "summary": "한 줄 요약",
  "strengths": ["강점"],
  "weaknesses": ["약점"],
  "recommendation": "조건부 추천",
  "find_competitor": false
}}
""".strip()

    payload = await llm_json_response_async(prompt, model="gpt-4o")
    return AggregatedReport.model_validate(payload)
