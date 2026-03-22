from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field


class RouterOptions(BaseModel):
    depth: Literal["quick", "deep"] = "quick"
    date_range: str = "3months"


class AnalyzeRequest(BaseModel):
    raw_query: str = Field(description="사용자 자연어 입력")
    product_url: str | None = Field(default=None, description="제품 링크")
    api_key: str | None = Field(
        default=None,
        description="요청 단위 OpenAI API Key",
        exclude=True,
        repr=False,
    )
    options: RouterOptions = Field(default_factory=RouterOptions)


class RoutingStrategy(BaseModel):
    product_name: str
    product_category: str
    brand: str
    sources: list[str]
    review_count_per_source: int
    depth: Literal["quick", "deep"]
    language: Literal["ko", "en", "both"]
    date_range: str


class CollectionTask(BaseModel):
    source: str
    query: str
    target_count: int


class OrchestratorOutput(BaseModel):
    tasks: list[CollectionTask]
    estimated_reviews: int


class CollectedReview(BaseModel):
    source: str
    title: str
    snippet: str
    url: str | None = None


class CollectionBatch(BaseModel):
    source: str
    reviews: list[CollectedReview]


class ReviewListResult(BaseModel):
    reviews: list[str]


class PreprocessResult(BaseModel):
    cleaned_reviews: list[str]
    normalized_reviews: list[str]
    filtered_reviews: list[str]


class SentimentResult(BaseModel):
    score: float
    label: Literal["긍정", "부정", "중립"]
    positive_ratio: float
    negative_ratio: float
    neutral_ratio: float
    evidence: list[str]


class PurchaseReasonResult(BaseModel):
    top_reasons: list[str]
    reason_frequency: dict[str, int]
    key_selling_points: list[str]


class ComplaintResult(BaseModel):
    top_complaints: list[str]
    complaint_frequency: dict[str, int]
    severity: Literal["low", "medium", "high"]
    critical_issues: list[str]


class AggregatedReport(BaseModel):
    product_name: str
    overall_score: float
    verdict: Literal["긍정", "중립", "네거티브"]
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    recommendation: Literal["구매 추천", "조건부 추천", "비추천"]
    find_competitor: bool


class CompetitorCandidateList(BaseModel):
    queries: list[str]
    candidates: list[str]


class CompetitorScore(BaseModel):
    product_name: str
    price: int
    price_score: float
    value_for_money: float
    emotional_value: float
    quality_score: float
    overall_score: float
    pros: list[str]
    cons: list[str]
    verdict: Literal["강력 추천", "추천", "조건부 추천", "비추천"]


class ComparisonReport(BaseModel):
    original_product: CompetitorScore
    competitors: list[CompetitorScore]
    best_pick: str
    best_pick_reason: str


class PipelineResult(BaseModel):
    routing_strategy: RoutingStrategy
    collection_tasks: list[CollectionTask]
    raw_review_count: int
    preprocessed_review_count: int
    sentiment: SentimentResult
    purchase_reasons: PurchaseReasonResult
    complaints: ComplaintResult
    aggregated_report: AggregatedReport
    competitor_candidates: list[str] = Field(default_factory=list)
    competitor_report: ComparisonReport | None = None
    warnings: list[str] = Field(default_factory=list)


@dataclass
class ProductAnalysisArtifacts:
    routing_strategy: RoutingStrategy
    orchestrator_output: OrchestratorOutput
    collected_reviews: list[CollectedReview]
    preprocess_result: PreprocessResult
    sentiment: SentimentResult
    purchase_reasons: PurchaseReasonResult
    complaints: ComplaintResult
    aggregated_report: AggregatedReport
