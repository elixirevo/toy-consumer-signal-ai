# Consumer Signal AI

AI 소비 심리 분석기에 제시한 5가지 패턴을 조합하면 아래와 같은 구조가 됩니다.

## 사용 스택

- OpenAI API
- FaseAPI
- HTML, JS, CSS

## 전체 파이프라인 설계

```text
[사용자 입력: 제품명]
        ↓
  ① 라우터 LLM
  (분석 전략 결정)
        ↓
  ② 오케스트레이터 LLM
  (수집 태스크 분해)
        ↓
  ③ 병렬 수집 Workers
  [네이버] [쿠팡] [Reddit] [커뮤니티]
        ↓
  ④ 프롬프트 체이닝
  Clean → Extract → Structure
        ↓
  ⑤ 병렬 분석 Workers
  [감정] [구매이유] [불만] [키워드]
        ↓
  ⑥ 어그리게이터 LLM
  (종합 리포트 생성)
        ↓
  ⑦ 평가 LLM
  (품질 검증 & 재시도)
```

## ① 라우터: 분석 전략 결정

사용자 입력을 받아 어떤 소스를 얼마나 수집할지 결정하는 가벼운 LLM입니다.

```python
# gpt-4o-mini 로 충분 (가볍고 빠름)
ROUTER_PROMPT = """
제품명과 카테고리를 분석해서 최적의 리뷰 수집 전략을 JSON으로 반환하세요.
- 국내 제품 → 네이버/쿠팡 우선
- 글로벌 제품 → Reddit/글로벌 사이트 포함
- B2B 제품 → 전문 커뮤니티 포함
"""

class RoutingStrategy(BaseModel):
    sources: list[str]        # ["naver", "coupang", "reddit"]
    review_count: int         # 각 소스 당 수집 수
    analysis_depth: str       # "quick" | "deep"
    language: str             # "ko" | "en" | "both"
```

## ② 오케스트레이터: 태스크 분해

라우터 결과를 받아 구체적인 수집 태스크를 동적으로 생성합니다.

```python
# 오케스트레이터가 동적으로 worker 수를 결정
# (병렬화와의 차이: 태스크 수가 런타임에 결정됨)
class CollectionTask(BaseModel):
    source: str           # "naver_shopping"
    query: str            # "아이폰 16 리뷰"
    target_count: int     # 50
    priority: int         # 1(높음) ~ 3(낮음)

# LangGraph Send API로 동적 워커 분기
def orchestrate(state):
    tasks = orchestrator_llm.invoke(state["strategy"])
    return [Send("collect_worker", task) for task in tasks]
```

## ③ 병렬 수집 Workers

오케스트레이터가 만든 태스크를 동시에 실행합니다.

```text
[네이버 Worker]   [쿠팡 Worker]   [Reddit Worker]   [DC/뽐뿌 Worker]
      ↓                 ↓               ↓                   ↓
  50개 리뷰          50개 리뷰       30개 리뷰            20개 리뷰
                         └──────────────┴──────────────────┘
                                    Aggregator
                                  (150개 raw 리뷰)
```

## ④ 프롬프트 체이닝: 전처리 파이프라인

수집된 리뷰를 LLM1 → LLM2 → LLM3 순서로 정제합니다.

```text
LLM1 (Clean Agent)
"HTML/이모지 제거, 중복 제거, 언어 감지"
        ↓ 정제된 텍스트
LLM2 (Normalize Agent)
"구어체 → 표준어, 신조어 해석, 맥락 보완"
        ↓ 정규화된 텍스트
LLM3 (Filter Agent)
"광고성 리뷰 필터링, 신뢰도 점수 부여"
        ↓ 신뢰도 높은 리뷰만
```

각 단계 출력이 다음 단계 입력이 되며, 각 LLM은 한 가지 역할만 담당합니다.

## ⑤ 병렬 분석 Workers: 핵심 분석

전처리된 리뷰를 4개 분석 워커가 동시에 처리합니다.

```python
# 4개 워커 동시 실행
async def run_parallel_analysis(reviews):
    results = await asyncio.gather(
        sentiment_worker(reviews),       # 감정 분석
        purchase_reason_worker(reviews), # 구매 이유 추출
        complaint_worker(reviews),       # 불만 사항 추출
        keyword_worker(reviews)          # 핵심 키워드 추출
    )
    return results

# 각 워커는 전용 시스템 프롬프트 + Structured Output
class SentimentResult(BaseModel):
    score: float          # -1.0 ~ 1.0
    label: str            # 긍정/부정/중립
    evidence: list[str]   # 근거 리뷰 문장

class PurchaseReasonResult(BaseModel):
    reasons: list[str]
    frequency: dict[str, int]
```

## ⑥ 어그리게이터: 종합 리포트

4개 워커 결과를 하나의 인사이트 리포트로 종합합니다.

```python
AGGREGATOR_PROMPT = """
감정분석, 구매이유, 불만, 키워드 분석 결과를 종합해서
소비자 심리 인사이트 리포트를 작성하세요.

- 핵심 구매 동기 Top 3
- 주요 불만 클러스터 Top 3
- 감정 분포 요약
- 마케팅 시사점
"""
```

## ⑦ 평가 & 최적화 루프

마지막으로 평가 LLM이 결과 품질을 검증하고, 기준 미달 시 재처리합니다.

```text
어그리게이터 결과
        ↓
  평가 LLM 체크
  - 근거 있는 분석인가?
  - 리뷰 수가 충분한가?
  - 논리적 모순 없는가?
        ↓
  [PASS] → 최종 출력
  [FAIL] → 부족한 워커만 재실행 (partial retry)
```

```python
class EvaluationResult(BaseModel):
    passed: bool
    score: float           # 0.0 ~ 1.0
    weak_areas: list[str]  # ["complaint_analysis", ...]
    retry_nodes: list[str] # 재실행할 노드 이름
```

## LangGraph 전체 State 구조

```python
class AnalyzerState(TypedDict):
    # 입력
    product_name: str

    # 라우터
    routing_strategy: RoutingStrategy

    # 오케스트레이터
    collection_tasks: list[CollectionTask]

    # 수집
    raw_reviews: list[str]

    # 전처리 체이닝
    cleaned_reviews: list[str]
    normalized_reviews: list[str]
    filtered_reviews: list[str]

    # 병렬 분석
    sentiment_result: SentimentResult
    purchase_result: PurchaseReasonResult
    complaint_result: ComplaintResult
    keyword_result: KeywordResult

    # 최종
    final_report: dict
    eval_result: EvaluationResult
    retry_count: int       # 무한루프 방지
```

## 패턴별 역할 요약

| 패턴 | 적용 위치 | 사용 모델 |
| --- | --- | --- |
| 라우팅 | 분석 전략 결정 | gpt-4o-mini |
| 오케스트레이터-워커 | 수집 태스크 분해 | gpt-4o-mini |
| 병렬 처리 | 소스 수집, 4대 분석 | gpt-4o-mini x N |
| 프롬프트 체이닝 | 전처리 3단계 | gpt-4o-mini |
| 평가 & 최적화 | 결과 품질 검증 | gpt-4o (고성능) |

어그리게이터와 평가 LLM만 `gpt-4o`를 쓰고 나머지는 `gpt-4o-mini`로 처리하면 품질과 비용을 동시에 잡을 수 있습니다.
