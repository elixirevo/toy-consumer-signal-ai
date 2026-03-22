from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Callable
from typing import Any

from src.feat.aggregator import aggregate_report
from src.feat.analyzer import analyze_parallel
from src.feat.collector import collect_all
from src.feat.competitor import compare_competitors, discover_competitor_candidates
from src.feat.orchestrator import create_collection_tasks
from src.feat.preprocess import preprocess_reviews
from src.feat.search_router import search_router
from src.models.pipeline import AnalyzeRequest, PipelineResult, ProductAnalysisArtifacts
from src.utils.agent import reset_request_api_key, set_request_api_key


ProgressCallback = Callable[[dict[str, Any]], Awaitable[None] | None]


def _reviews_to_texts(collected_reviews) -> list[str]:
    return [
        f"[{review.source}] {review.title} - {review.snippet}"
        for review in collected_reviews
    ]


async def _emit_progress(
    progress_callback: ProgressCallback | None,
    *,
    step: str,
    status: str,
    message: str,
    data: dict[str, Any] | None = None,
) -> None:
    if progress_callback is None:
        return

    event = {
        "type": "progress",
        "step": step,
        "status": status,
        "message": message,
    }
    if data is not None:
        event["data"] = data

    maybe_awaitable = progress_callback(event)
    if inspect.isawaitable(maybe_awaitable):
        await maybe_awaitable


async def _run_single_product_analysis(
    payload: AnalyzeRequest,
    *,
    progress_callback: ProgressCallback | None = None,
    label: str = "원제품",
) -> ProductAnalysisArtifacts:
    await _emit_progress(
        progress_callback,
        step="router",
        status="started",
        message=f"{label} 라우팅 전략 생성 중",
    )
    routing_strategy = await search_router(payload)
    await _emit_progress(
        progress_callback,
        step="router",
        status="completed",
        message=f"{label} 라우팅 완료",
        data={
            "product_name": routing_strategy.product_name,
            "sources": routing_strategy.sources,
            "depth": routing_strategy.depth,
        },
    )

    await _emit_progress(
        progress_callback,
        step="orchestrator",
        status="started",
        message=f"{label} 수집 태스크 생성 중",
    )
    orchestrator_output = await create_collection_tasks(routing_strategy)
    await _emit_progress(
        progress_callback,
        step="orchestrator",
        status="completed",
        message=f"{label} 수집 태스크 생성 완료",
        data={"task_count": len(orchestrator_output.tasks)},
    )

    await _emit_progress(
        progress_callback,
        step="collector",
        status="started",
        message=f"{label} 웹 리뷰 수집 중",
    )
    collected_reviews = await collect_all(orchestrator_output.tasks)
    await _emit_progress(
        progress_callback,
        step="collector",
        status="completed",
        message=f"{label} 웹 리뷰 수집 완료",
        data={"raw_review_count": len(collected_reviews)},
    )

    raw_reviews = _reviews_to_texts(collected_reviews)
    await _emit_progress(
        progress_callback,
        step="preprocess",
        status="started",
        message=f"{label} 리뷰 전처리 중",
    )
    preprocess_result = await preprocess_reviews(raw_reviews)
    await _emit_progress(
        progress_callback,
        step="preprocess",
        status="completed",
        message=f"{label} 리뷰 전처리 완료",
        data={"filtered_review_count": len(preprocess_result.filtered_reviews)},
    )

    await _emit_progress(
        progress_callback,
        step="analysis",
        status="started",
        message=f"{label} 감정 / 구매이유 / 불만 분석 중",
    )
    sentiment, purchase_reasons, complaints = await analyze_parallel(
        preprocess_result.filtered_reviews
    )
    await _emit_progress(
        progress_callback,
        step="analysis",
        status="completed",
        message=f"{label} 핵심 분석 완료",
        data={
            "sentiment_label": sentiment.label,
            "complaint_severity": complaints.severity,
        },
    )

    await _emit_progress(
        progress_callback,
        step="aggregator",
        status="started",
        message=f"{label} 종합 평가 생성 중",
    )
    aggregated_report = await aggregate_report(
        routing_strategy,
        sentiment,
        purchase_reasons,
        complaints,
    )
    await _emit_progress(
        progress_callback,
        step="aggregator",
        status="completed",
        message=f"{label} 종합 평가 완료",
        data={
            "verdict": aggregated_report.verdict,
            "find_competitor": aggregated_report.find_competitor,
        },
    )

    return ProductAnalysisArtifacts(
        routing_strategy=routing_strategy,
        orchestrator_output=orchestrator_output,
        collected_reviews=collected_reviews,
        preprocess_result=preprocess_result,
        sentiment=sentiment,
        purchase_reasons=purchase_reasons,
        complaints=complaints,
        aggregated_report=aggregated_report,
    )


async def run_analysis_pipeline(
    payload: AnalyzeRequest,
    *,
    progress_callback: ProgressCallback | None = None,
) -> PipelineResult:
    token = set_request_api_key(payload.api_key)
    warnings: list[str] = []
    try:
        await _emit_progress(
            progress_callback,
            step="pipeline",
            status="started",
            message="분석 파이프라인 시작",
        )

        primary = await _run_single_product_analysis(
            payload,
            progress_callback=progress_callback,
            label="원제품",
        )

        competitor_candidates: list[str] = []
        competitor_report = None

        if primary.aggregated_report.find_competitor:
            await _emit_progress(
                progress_callback,
                step="competitor-discovery",
                status="started",
                message="경쟁 제품 후보 탐색 중",
            )
            try:
                candidate_list = await discover_competitor_candidates(
                    primary.routing_strategy,
                    primary.aggregated_report,
                )
                competitor_candidates = candidate_list.candidates
                await _emit_progress(
                    progress_callback,
                    step="competitor-discovery",
                    status="completed",
                    message="경쟁 제품 후보 탐색 완료",
                    data={"candidate_count": len(competitor_candidates)},
                )

                if competitor_candidates:
                    await _emit_progress(
                        progress_callback,
                        step="competitor-analysis",
                        status="started",
                        message="경쟁 제품 상세 분석 중",
                        data={"candidates": competitor_candidates},
                    )
                    candidate_payloads = [
                        AnalyzeRequest(
                            raw_query=f"{candidate} 리뷰 분석해줘",
                            options=payload.options,
                        )
                        for candidate in competitor_candidates
                    ]
                    candidate_analyses = await asyncio.gather(
                        *[
                            _run_single_product_analysis(
                                candidate_payload,
                                progress_callback=progress_callback,
                                label=f"경쟁제품 {index + 1}: {competitor_candidates[index]}",
                            )
                            for index, candidate_payload in enumerate(candidate_payloads)
                        ]
                    )
                    await _emit_progress(
                        progress_callback,
                        step="competitor-comparison",
                        status="started",
                        message="원제품과 경쟁 제품 비교 중",
                    )
                    competitor_report = await compare_competitors(primary, candidate_analyses)
                    await _emit_progress(
                        progress_callback,
                        step="competitor-comparison",
                        status="completed",
                        message="경쟁 제품 비교 완료",
                        data={"best_pick": competitor_report.best_pick},
                    )
                else:
                    warnings.append("경쟁 제품 후보를 찾지 못했습니다.")
                    await _emit_progress(
                        progress_callback,
                        step="competitor-discovery",
                        status="info",
                        message="경쟁 제품 후보를 찾지 못해 비교 단계를 건너뜁니다.",
                    )
            except Exception as exc:
                warnings.append(f"경쟁 제품 분석 단계가 실패했습니다: {exc}")
                await _emit_progress(
                    progress_callback,
                    step="competitor-analysis",
                    status="failed",
                    message=f"경쟁 제품 분석 단계 실패: {exc}",
                )
        else:
            await _emit_progress(
                progress_callback,
                step="competitor-skip",
                status="info",
                message="원제품 평가가 네거티브가 아니어서 경쟁 제품 탐색을 건너뜁니다.",
            )

        result = PipelineResult(
            routing_strategy=primary.routing_strategy,
            collection_tasks=primary.orchestrator_output.tasks,
            raw_review_count=len(primary.collected_reviews),
            preprocessed_review_count=len(primary.preprocess_result.filtered_reviews),
            sentiment=primary.sentiment,
            purchase_reasons=primary.purchase_reasons,
            complaints=primary.complaints,
            aggregated_report=primary.aggregated_report,
            competitor_candidates=competitor_candidates,
            competitor_report=competitor_report,
            warnings=warnings,
        )

        await _emit_progress(
            progress_callback,
            step="pipeline",
            status="completed",
            message="분석 파이프라인 완료",
        )

        return result
    finally:
        reset_request_api_key(token)
