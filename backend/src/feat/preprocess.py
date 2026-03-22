from __future__ import annotations

import json

from src.models.pipeline import PreprocessResult, ReviewListResult
from src.utils.agent import llm_json_response_async


def _reviews_to_text(reviews: list[str]) -> str:
    return "\n".join(f"{idx + 1}. {review}" for idx, review in enumerate(reviews))


async def clean_reviews(raw_reviews: list[str]) -> list[str]:
    prompt = f"""
너는 리뷰 정제 1단계 Clean Agent다.
아래 리뷰 목록에서 HTML, 노이즈, 중복 문장을 제거하고 핵심 문장만 남겨라.

규칙:
- 출력은 JSON 객체만 반환한다.
- reviews 필드는 정제된 문자열 배열이다.
- 완전히 중복인 항목은 제거한다.
- 의미 없는 짧은 텍스트는 제거한다.

입력:
{_reviews_to_text(raw_reviews)}

반환 스키마:
{{"reviews": ["정제된 리뷰"]}}
""".strip()
    payload = await llm_json_response_async(prompt, model="gpt-4o-mini")
    return ReviewListResult.model_validate(payload).reviews


async def normalize_reviews(cleaned_reviews: list[str]) -> list[str]:
    prompt = f"""
너는 리뷰 정제 2단계 Normalize Agent다.
아래 리뷰 목록을 분석하기 좋게 정규화하라.

규칙:
- 출력은 JSON 객체만 반환한다.
- reviews 필드는 정규화된 문자열 배열이다.
- 구어체를 표준어에 가깝게 정리한다.
- 신조어와 축약 표현은 의미가 유지되도록 풀어쓴다.
- 원래 평가 방향은 바꾸지 않는다.

입력:
{_reviews_to_text(cleaned_reviews)}

반환 스키마:
{{"reviews": ["정규화된 리뷰"]}}
""".strip()
    payload = await llm_json_response_async(prompt, model="gpt-4o-mini")
    return ReviewListResult.model_validate(payload).reviews


async def filter_reviews(normalized_reviews: list[str]) -> list[str]:
    prompt = f"""
너는 리뷰 정제 3단계 Filter Agent다.
아래 리뷰 목록에서 광고성, 근거 부족, 지나치게 모호한 리뷰를 제외하라.

규칙:
- 출력은 JSON 객체만 반환한다.
- reviews 필드는 최종 분석에 사용할 문자열 배열이다.
- 분석 가능한 리뷰만 남긴다.
- 장점 또는 단점이 분명히 드러나는 리뷰를 우선 유지한다.

입력:
{_reviews_to_text(normalized_reviews)}

반환 스키마:
{{"reviews": ["분석 가능한 리뷰"]}}
""".strip()
    payload = await llm_json_response_async(prompt, model="gpt-4o-mini")
    return ReviewListResult.model_validate(payload).reviews


async def preprocess_reviews(raw_reviews: list[str]) -> PreprocessResult:
    cleaned_reviews = await clean_reviews(raw_reviews)
    normalized_reviews = await normalize_reviews(cleaned_reviews)
    filtered_reviews = await filter_reviews(normalized_reviews)
    return PreprocessResult(
        cleaned_reviews=cleaned_reviews,
        normalized_reviews=normalized_reviews,
        filtered_reviews=filtered_reviews,
    )
