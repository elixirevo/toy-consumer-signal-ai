from __future__ import annotations

import json

from src.models.pipeline import CollectionTask, OrchestratorOutput, RoutingStrategy
from src.utils.agent import llm_json_response_async


ORCHESTRATOR_PROMPT = """
너는 AI 소비 심리 분석기의 Orchestrator LLM이다.
라우팅 전략을 기반으로 실제 리뷰 수집 태스크를 JSON으로 생성한다.

반드시 지켜야 할 규칙:
- 출력은 JSON 객체 하나만 반환한다.
- tasks는 CollectionTask 배열이다.
- 각 task는 source, query, target_count를 포함한다.
- query는 실제 웹 검색에 바로 사용할 수 있게 구체적으로 만든다.
- product_name, brand, category를 반영해 리뷰/후기/단점/비교 관점 질의를 섞는다.
- user_context와 review_focus가 있으면 query에 자연스럽게 반영한다.
- query는 제품 자체 리뷰뿐 아니라 사용자의 상황과 관련된 실사용 맥락을 찾을 수 있어야 한다.
- estimated_reviews는 전체 기대 리뷰 수다.
""".strip()


def _build_orchestrator_prompt(strategy: RoutingStrategy) -> str:
    strategy_json = json.dumps(strategy.model_dump(), ensure_ascii=False, indent=2)
    return f"""
{ORCHESTRATOR_PROMPT}

라우팅 전략:
{strategy_json}

반환 스키마:
{{
  "tasks": [
    {{
      "source": "naver_shopping",
      "query": "갤럭시 S25 울트라 후기",
      "target_count": 30
    }}
  ],
  "estimated_reviews": 60
}}
""".strip()


def _fallback_tasks(strategy: RoutingStrategy) -> OrchestratorOutput:
    suffix_map = {
        "naver_shopping": "리뷰 후기",
        "coupang": "사용 후기 단점",
        "reddit": "review complaints",
        "amazon": "review pros cons",
        "danawa": "리뷰 장단점",
        "oliveyoung": "후기 만족도",
    }
    focus_terms = (
        strategy.review_focus
        or strategy.user_context.priorities
        or strategy.user_context.constraints
    )[: max(1, len(strategy.sources))]

    tasks = []
    for index, source in enumerate(strategy.sources):
        parts = [strategy.product_name]
        if focus_terms:
            parts.append(focus_terms[index % len(focus_terms)])
        parts.append(suffix_map.get(source, "리뷰"))

        tasks.append(
            CollectionTask(
                source=source,
                query=" ".join(part for part in parts if part).strip(),
                target_count=strategy.review_count_per_source,
            )
        )

    return OrchestratorOutput(
        tasks=tasks,
        estimated_reviews=len(tasks) * strategy.review_count_per_source,
    )


async def create_collection_tasks(strategy: RoutingStrategy) -> OrchestratorOutput:
    prompt = _build_orchestrator_prompt(strategy)
    payload = await llm_json_response_async(prompt, model="gpt-4o-mini")
    output = OrchestratorOutput.model_validate(payload)

    if not output.tasks:
        return _fallback_tasks(strategy)

    return output
