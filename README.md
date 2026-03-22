# AI 소비 심리 분석기

## 사용

```zsh
# 패키지 설치
cd backend && uv sync

# 서버 실행
sh scripts/run_dev.sh
```

## 개요

- 기술 스택: OpenAI API, Python
- 목적: 제품명 또는 링크 입력 → 리뷰 수집 → 감정 / 구매이유 / 불만 분석 → 네거티브 시 경쟁 제품 추천

## 전체 파이프라인

```text
[유저 입력: 제품명 or URL]
          ↓
   ① ROUTER LLM
   분석 전략 결정
          ↓
   ② ORCHESTRATOR LLM
   수집 태스크 분해
          ↓
   ③ 병렬 웹 수집 Workers
   [OpenAI Web Search Tool]
          ↓
   ④ 프롬프트 체이닝 전처리
   Clean → Normalize → Filter
          ↓
   ⑤ 병렬 분석 Workers
   [감정] [구매이유] [불만]
          ↓
   ⑥ AGGREGATOR LLM
   종합 평가 판정
          ↓
      ┌───┴───┐
   [긍정/중립]  [네거티브]
      ↓           ↓
   최종 리포트   ⑦ 경쟁제품 탐색
              [수집 → 분석 → 비교]
                   ↓
              최종 비교 리포트
```

## ① 라우터 (Router LLM)

역할: 유저 입력을 받아 전체 분석 전략을 결정하는 첫 번째 진입점

### 입력 구조

```python
user_input = {
    "raw_query": "갤럭시 S25 울트라 리뷰 분석해줘",
    "product_url": "https://...",
    "options": {
        "depth": "deep",       # "quick" | "deep"
        "date_range": "3months"
    }
}
```

### 출력 구조

```python
class RoutingStrategy(BaseModel):
    product_name: str
    product_category: str
    brand: str
    sources: list[str]             # ["naver_shopping", "coupang", "reddit"]
    review_count_per_source: int   # 50
    depth: str                     # "quick" | "deep"
    language: str                  # "ko" | "en" | "both"
    date_range: str                # "3months"
```

- 모델: `gpt-4o-mini`

### 라우터 전략 규칙

- 국내 브랜드 → `naver_shopping`, `coupang` 우선
- 글로벌 브랜드 → `reddit`, `amazon` 추가
- 카테고리별 소스 자동 추가
- 예: 화장품 → `oliveyoung`, 가전 → `danawa`

## ② 오케스트레이터 (Orchestrator LLM)

역할: 라우팅 전략을 받아 구체적인 검색 쿼리 태스크 목록으로 분해

```python
class CollectionTask(BaseModel):
    source: str        # "naver_shopping"
    query: str         # "갤럭시 S25 울트라 사용 후기"
    target_count: int  # 50

class OrchestratorOutput(BaseModel):
    tasks: list[CollectionTask]
    estimated_reviews: int
```

- 모델: `gpt-4o-mini`

## ③ 병렬 웹 수집 Workers

### 수집 방식

- 병렬 웹 수집은 외부 검색 API를 따로 붙이지 않고 `OpenAI API`의 웹 검색 도구로 처리합니다.
- 각 워커는 검색 질의를 하나씩 받아 웹에서 리뷰, 후기, 비교 글, 커뮤니티 반응을 찾습니다.
- 수집 대상 소스는 라우터가 정하고, 실제 검색 실행은 OpenAI Responses API가 담당합니다.

```python
import asyncio
from src.utils.agent import llm_search_async

async def collect_all(tasks: list[CollectionTask]) -> list[str]:
    results = await asyncio.gather(
        *[collect_worker(task) for task in tasks]
    )
    return [review for batch in results for review in batch]

async def collect_worker(task: CollectionTask) -> list[str]:
    prompt = f"""
    아래 조건에 맞는 제품 리뷰와 사용자 반응을 웹에서 찾아 요약하세요.
    - source: {task.source}
    - query: {task.query}
    - target_count: {task.target_count}
    - 리뷰, 후기, 비교 글, 커뮤니티 반응 위주로 수집
    - 중복은 제거
    """
    result = await llm_search_async(prompt, model="gpt-4o-mini")
    return [result]
```

- 모델: `gpt-4o-mini`
- 검색 도구: OpenAI Responses API `tools=[{"type": "web_search"}]`

## ④ 프롬프트 체이닝 전처리

수집된 원시 리뷰를 3개 LLM이 순차적으로 정제합니다.

```text
raw_reviews
    ↓
[LLM1: Clean Agent]
HTML 제거, 중복 제거, 5자 이하 필터링
    ↓
[LLM2: Normalize Agent]
구어체 → 표준어, 신조어 해석, 맥락 보완
    ↓
[LLM3: Filter Agent]
광고성 리뷰 탐지 및 제거, 신뢰도 점수 부여 (0.0 ~ 1.0)
신뢰도 0.5 미만 제거
    ↓
filtered_reviews (신뢰도 높은 리뷰만)
```

- 모델: 3단계 모두 `gpt-4o-mini`
- Batch API 활용 시 비용 절감 가능

## ⑤ 병렬 분석 Workers

전처리된 리뷰를 3개 분석 워커가 동시에 처리합니다.

```python
async def analyze_parallel(reviews: list[str]):
    sentiment, reasons, complaints = await asyncio.gather(
        sentiment_worker(reviews),
        purchase_reason_worker(reviews),
        complaint_worker(reviews),
    )
    return sentiment, reasons, complaints
```

### 워커 출력 스키마

```python
class SentimentResult(BaseModel):
    score: float           # -1.0 ~ 1.0
    label: str             # "긍정" | "부정" | "중립"
    positive_ratio: float
    negative_ratio: float
    neutral_ratio: float
    evidence: list[str]

class PurchaseReasonResult(BaseModel):
    top_reasons: list[str]
    reason_frequency: dict
    key_selling_points: list[str]

class ComplaintResult(BaseModel):
    top_complaints: list[str]
    complaint_frequency: dict
    severity: str          # "low" | "medium" | "high"
    critical_issues: list[str]
```

- 모델: `gpt-4o-mini`

## ⑥ 어그리게이터 (Aggregator LLM)

3개 워커 결과를 받아 최종 제품 평가 판정을 내립니다.

```python
class AggregatedReport(BaseModel):
    product_name: str
    overall_score: float
    verdict: str                # "긍정" | "중립" | "네거티브"
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    recommendation: str         # "구매 추천" | "조건부 추천" | "비추천"
    find_competitor: bool
```

### 판정 기준

- `overall_score < 5.5` 또는 `severity == "high"` → `find_competitor = True`
- `sentiment_score < -0.2` → `find_competitor = True`

- 모델: `gpt-4o`

## ⑦ 경쟁 제품 탐색

네거티브 판정 시에만 실행합니다.

### 7-1. 경쟁 제품 목록 수집

```python
queries = [
    f"{product_name} 대안 추천 2025",
    f"{product_name} 경쟁 제품 비교",
    f"{category} 추천 {price_range}",
]
```

### 7-2. 경쟁 제품 병렬 분석

각 후보 제품에 대해 ③~⑥ 미니 파이프라인을 병렬 실행합니다.

### 7-3. 경쟁력 비교 스키마

```python
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
    verdict: str

class ComparisonReport(BaseModel):
    original_product: CompetitorScore
    competitors: list[CompetitorScore]
    best_pick: str
    best_pick_reason: str
```

- 모델: `gpt-4o`

## 최종 출력 예시

```text
[갤럭시 S25 울트라] 소비 심리 분석 리포트
────────────────────────────────
종합 점수:     4.8 / 10   🔴네거티브
감정 분포:     긍정 38% | 중립 22% | 부정 40%
구매 이유 Top3: 카메라 화질, S펜, 삼성 생태계
주요 불만 Top3: 발열 문제, 가격 부담, 무게

더 경쟁력 있는 대안 제품
────────────────────────────────
1위 아이폰 16 Pro
가격: 155만원 | 가성비 7.2 | 가심비 9.1 | 품질 9.0

2위 픽셀 9 Pro
가격: 119만원 | 가성비 8.5 | 가심비 7.0 | 품질 8.2

3위 갤럭시 S25+
가격: 135만원 | 가성비 7.8 | 가심비 7.5 | 품질 7.9
```
