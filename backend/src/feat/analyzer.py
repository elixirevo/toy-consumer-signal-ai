from __future__ import annotations

import asyncio

from src.models.pipeline import ComplaintResult, PurchaseReasonResult, SentimentResult
from src.utils.agent import llm_json_response_async


def _reviews_to_text(reviews: list[str]) -> str:
    return "\n".join(f"{idx + 1}. {review}" for idx, review in enumerate(reviews))


async def sentiment_worker(reviews: list[str]) -> SentimentResult:
    prompt = f"""
너는 감정 분석 워커다.
아래 리뷰를 감정 분석해서 JSON으로 반환하라.

규칙:
- 출력은 JSON 객체만 반환한다.
- label은 "긍정", "부정", "중립" 중 하나다.
- score는 -1.0 ~ 1.0 사이 숫자다.
- 비율 합계는 1.0에 가깝게 맞춘다.
- evidence에는 대표 근거 문장 3개 이하를 넣는다.

입력:
{_reviews_to_text(reviews)}

반환 스키마:
{{
  "score": 0.1,
  "label": "중립",
  "positive_ratio": 0.4,
  "negative_ratio": 0.3,
  "neutral_ratio": 0.3,
  "evidence": ["문장"]
}}
""".strip()
    payload = await llm_json_response_async(prompt, model="gpt-4o-mini")
    return SentimentResult.model_validate(payload)


async def purchase_reason_worker(reviews: list[str]) -> PurchaseReasonResult:
    prompt = f"""
너는 구매 이유 분석 워커다.
아래 리뷰에서 사람들이 이 제품을 사는 이유를 추출해서 JSON으로 반환하라.

규칙:
- 출력은 JSON 객체만 반환한다.
- top_reasons는 중요도 순으로 3~5개
- reason_frequency는 이유별 등장 횟수
- key_selling_points는 마케팅 메시지로 쓸 수 있는 강점

입력:
{_reviews_to_text(reviews)}

반환 스키마:
{{
  "top_reasons": ["이유"],
  "reason_frequency": {{"이유": 3}},
  "key_selling_points": ["포인트"]
}}
""".strip()
    payload = await llm_json_response_async(prompt, model="gpt-4o-mini")
    return PurchaseReasonResult.model_validate(payload)


async def complaint_worker(reviews: list[str]) -> ComplaintResult:
    prompt = f"""
너는 불만 분석 워커다.
아래 리뷰에서 주요 불만과 치명 이슈를 추출해서 JSON으로 반환하라.

규칙:
- 출력은 JSON 객체만 반환한다.
- severity는 "low", "medium", "high" 중 하나다.
- top_complaints는 중요도 순으로 3~5개

입력:
{_reviews_to_text(reviews)}

반환 스키마:
{{
  "top_complaints": ["불만"],
  "complaint_frequency": {{"불만": 2}},
  "severity": "medium",
  "critical_issues": ["치명 이슈"]
}}
""".strip()
    payload = await llm_json_response_async(prompt, model="gpt-4o-mini")
    return ComplaintResult.model_validate(payload)


async def analyze_parallel(
    reviews: list[str],
) -> tuple[SentimentResult, PurchaseReasonResult, ComplaintResult]:
    sentiment, reasons, complaints = await asyncio.gather(
        sentiment_worker(reviews),
        purchase_reason_worker(reviews),
        complaint_worker(reviews),
    )
    return sentiment, reasons, complaints
