from __future__ import annotations

import asyncio

from src.models.pipeline import CollectionBatch, CollectionTask, CollectedReview
from src.utils.agent import llm_json_response_async, llm_search_async


def _build_collect_search_prompt(task: CollectionTask, max_reviews: int) -> str:
    return f"""
너는 리뷰 수집 워커다.
OpenAI 웹 검색 도구를 사용해서 제품 리뷰와 사용자 반응을 수집해라.

규칙:
- JSON으로 답하지 말고 사람이 읽을 수 있는 텍스트로 정리한다.
- 최대 {max_reviews}개의 서로 다른 리뷰/후기/비교 반응을 정리한다.
- 각 항목에는 출처명, 제목, 핵심 반응, URL이 드러나게 작성한다.
- 광고성 문구보다 실제 사용 경험, 장점, 단점, 불만을 우선 수집한다.
- 같은 내용은 중복해서 넣지 않는다.

입력:
- source: {task.source}
- query: {task.query}
- target_count: {task.target_count}
""".strip()


def _build_collect_structure_prompt(task: CollectionTask, max_reviews: int, search_text: str) -> str:
    return f"""
너는 리뷰 검색 결과를 구조화하는 정리기다.
아래 웹 검색 결과 텍스트를 JSON 객체 하나로 변환하라.

규칙:
- 출력은 JSON 객체 하나만 반환한다.
- source는 입력 source를 그대로 사용한다.
- reviews는 최대 {max_reviews}개까지만 포함한다.
- 각 review는 source, title, snippet, url 필드를 포함한다.
- snippet은 실제 사용자 반응이 드러나는 1~3문장 요약이어야 한다.
- URL을 모르면 null로 둔다.
- 텍스트에 없는 내용을 지어내지 않는다.

입력 source: {task.source}
검색 결과 텍스트:
{search_text}

반환 스키마:
{{
  "source": "{task.source}",
  "reviews": [
    {{
      "source": "{task.source}",
      "title": "리뷰 제목",
      "snippet": "리뷰 핵심 내용",
      "url": "https://example.com"
    }}
  ]
}}
""".strip()


def _fallback_review(task: CollectionTask, reason: str, raw_text: str | None = None) -> CollectionBatch:
    snippet = raw_text.strip() if raw_text else ""
    if not snippet:
        snippet = f"{task.query} 관련 웹 검색 결과를 구조화하지 못해 기본 요약으로 대체했습니다. 원인: {reason}"
    snippet = snippet[:700]

    return CollectionBatch(
        source=task.source,
        reviews=[
            CollectedReview(
                source=task.source,
                title=f"{task.query} 검색 결과 요약",
                snippet=snippet,
                url=None,
            )
        ],
    )


async def collect_worker(task: CollectionTask) -> CollectionBatch:
    max_reviews = min(task.target_count, 8)

    try:
        search_text = await llm_search_async(
            _build_collect_search_prompt(task, max_reviews=max_reviews),
            model="gpt-4.1",
        )
    except Exception as exc:
        return _fallback_review(task, f"search_failed: {exc}")

    if not search_text.strip():
        return _fallback_review(task, "empty_search_response")

    try:
        payload = await llm_json_response_async(
            _build_collect_structure_prompt(task, max_reviews=max_reviews, search_text=search_text),
            model="gpt-4o-mini",
        )
        batch = CollectionBatch.model_validate(payload)
    except Exception:
        return _fallback_review(task, "structure_failed", raw_text=search_text)

    if not batch.reviews:
        return _fallback_review(task, "no_reviews_after_structuring", raw_text=search_text)

    return batch


async def collect_all(tasks: list[CollectionTask]) -> list[CollectedReview]:
    batches = await asyncio.gather(*[collect_worker(task) for task in tasks])
    return [review for batch in batches for review in batch.reviews]
