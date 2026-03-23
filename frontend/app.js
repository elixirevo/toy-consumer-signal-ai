const form = document.getElementById("analyze-form");
const sampleButton = document.getElementById("sample-button");
const submitButton = document.getElementById("submit-button");
const apiBaseUrlInput = document.getElementById("api-base-url");
const apiKeyInput = document.getElementById("api-key");
const rawQueryInput = document.getElementById("raw-query");
const productUrlInput = document.getElementById("product-url");
const depthInput = document.getElementById("depth");
const dateRangeInput = document.getElementById("date-range");
const clearHistoryButton = document.getElementById("clear-history-button");

const statusBox = document.getElementById("status-box");
const progressList = document.getElementById("progress-list");
const historyList = document.getElementById("history-list");
const emptyState = document.getElementById("empty-state");
const resultContent = document.getElementById("result-content");
const summaryGrid = document.getElementById("summary-grid");
const heroPanel = document.querySelector(".hero-panel");
const previewSummary = document.getElementById("preview-summary");
const previewScore = document.getElementById("preview-score");
const previewSentimentHeadline = document.getElementById("preview-sentiment-headline");
const previewSentimentMeta = document.getElementById("preview-sentiment-meta");
const previewReasons = document.getElementById("preview-reasons");
const previewRecommendation = document.getElementById("preview-recommendation");
const previewStepCollect = document.getElementById("preview-step-collect");
const previewStepAnalyze = document.getElementById("preview-step-analyze");
const previewStepCompare = document.getElementById("preview-step-compare");
const previewBarPositive = document.getElementById("preview-bar-positive");
const previewBarNeutral = document.getElementById("preview-bar-neutral");
const previewBarNegative = document.getElementById("preview-bar-negative");
const routingStrategyBox = document.getElementById("routing-strategy");
const sentimentBox = document.getElementById("sentiment-result");
const purchaseBox = document.getElementById("purchase-result");
const complaintBox = document.getElementById("complaint-result");
const aggregatedBox = document.getElementById("aggregated-report");
const competitorBox = document.getElementById("competitor-report");
const rawJsonBox = document.getElementById("raw-json");
const customSelectRoots = Array.from(document.querySelectorAll("[data-custom-select]"));

const API_BASE_STORAGE_KEY = "consumer-signal-ai-api-base-url";
const ANALYSIS_HISTORY_STORAGE_KEY = "consumer-signal-ai-analysis-history";
const MAX_HISTORY_ITEMS = 8;
const DEFAULT_REMOTE_API_BASE_URL = "https://toy-consumer-signal-back.vercel.app/";
const DEFAULT_PREVIEW_STATE = {
  summary: "실제 조회 전에는 샘플 내용이 표시됩니다.",
  score: "7.8",
  sentimentHeadline: "긍정 우세",
  sentimentMeta: "긍정 68% · 중립 21% · 부정 11%",
  reasons: "디자인 · 성능 · 만족감",
  recommendation: "구매 추천 시그널",
  steps: {
    collect: "샘플 120건 기준",
    analyze: "긍정 의견 우세",
    compare: "후보 비교 대기",
  },
  bars: {
    positive: 86,
    neutral: 58,
    negative: 32,
  },
};
let progressSequence = 0;

function getDefaultApiBaseUrl() {
  const { protocol, hostname } = window.location;
  const isLocalHost = hostname === "127.0.0.1" || hostname === "localhost";
  if (isLocalHost) {
    return "http://127.0.0.1:8000";
  }
  if (protocol === "http:" || protocol === "https:") {
    return DEFAULT_REMOTE_API_BASE_URL;
  }
  return "";
}

function restoreSavedApiBaseUrl() {
  const saved = window.localStorage.getItem(API_BASE_STORAGE_KEY);
  const defaultValue = getDefaultApiBaseUrl();

  if (saved) {
    if (saved === "/api") {
      apiBaseUrlInput.value = defaultValue;
      saveApiBaseUrl();
      return;
    }

    apiBaseUrlInput.value = saved;
    return;
  }

  apiBaseUrlInput.value = defaultValue;
}

function saveApiBaseUrl() {
  window.localStorage.setItem(API_BASE_STORAGE_KEY, apiBaseUrlInput.value.trim());
}

function setStatus(type, message) {
  statusBox.className = `status-box ${type}`;
  statusBox.textContent = message;
}

function getCustomSelectParts(root) {
  return {
    hiddenInput: document.getElementById(root.dataset.customSelect),
    trigger: root.querySelector("[data-select-trigger]"),
    label: root.querySelector("[data-select-label]"),
    options: Array.from(root.querySelectorAll("[data-select-option]")),
  };
}

function syncCustomSelect(root) {
  const { hiddenInput, label, options } = getCustomSelectParts(root);
  const selectedOption =
    options.find((option) => option.dataset.value === hiddenInput.value) || options[0];

  if (!selectedOption) {
    return;
  }

  hiddenInput.value = selectedOption.dataset.value;
  label.textContent = selectedOption.textContent.trim();

  options.forEach((option) => {
    const isSelected = option === selectedOption;
    option.classList.toggle("is-selected", isSelected);
    option.setAttribute("aria-selected", String(isSelected));
  });
}

function openCustomSelect(root) {
  closeAllCustomSelects(root);
  root.classList.add("is-open");
  const { trigger } = getCustomSelectParts(root);
  trigger.setAttribute("aria-expanded", "true");
}

function closeCustomSelect(root) {
  root.classList.remove("is-open");
  const { trigger } = getCustomSelectParts(root);
  trigger.setAttribute("aria-expanded", "false");
}

function closeAllCustomSelects(exceptRoot = null) {
  customSelectRoots.forEach((root) => {
    if (root !== exceptRoot) {
      closeCustomSelect(root);
    }
  });
}

function setCustomSelectValue(selectId, value) {
  const root = customSelectRoots.find((item) => item.dataset.customSelect === selectId);
  if (!root) {
    return;
  }

  const { hiddenInput, options } = getCustomSelectParts(root);
  const matchedOption = options.find((option) => option.dataset.value === value);
  if (!matchedOption) {
    return;
  }

  hiddenInput.value = value;
  syncCustomSelect(root);
}

function focusAdjacentOption(options, currentOption, direction) {
  const currentIndex = options.indexOf(currentOption);
  if (currentIndex === -1) {
    return;
  }

  const nextIndex = currentIndex + direction;
  if (nextIndex < 0 || nextIndex >= options.length) {
    return;
  }

  options[nextIndex].focus();
}

function initializeCustomSelects() {
  customSelectRoots.forEach((root) => {
    const { trigger, options } = getCustomSelectParts(root);

    syncCustomSelect(root);

    trigger.addEventListener("click", () => {
      if (root.classList.contains("is-open")) {
        closeCustomSelect(root);
      } else {
        openCustomSelect(root);
      }
    });

    trigger.addEventListener("keydown", (event) => {
      if (event.key === "ArrowDown" || event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openCustomSelect(root);
        const selectedOption = options.find((option) => option.classList.contains("is-selected"));
        (selectedOption || options[0])?.focus();
      }
    });

    options.forEach((option) => {
      option.addEventListener("click", () => {
        setCustomSelectValue(root.dataset.customSelect, option.dataset.value);
        closeCustomSelect(root);
        trigger.focus();
      });

      option.addEventListener("keydown", (event) => {
        if (event.key === "ArrowDown") {
          event.preventDefault();
          focusAdjacentOption(options, option, 1);
        } else if (event.key === "ArrowUp") {
          event.preventDefault();
          focusAdjacentOption(options, option, -1);
        } else if (event.key === "Escape") {
          event.preventDefault();
          closeCustomSelect(root);
          trigger.focus();
        }
      });
    });
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest("[data-custom-select]")) {
      closeAllCustomSelects();
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeAllCustomSelects();
    }
  });
}

function resetProgress() {
  progressSequence = 0;
  progressList.innerHTML = `
    <li class="progress-item placeholder">
      <span class="progress-index">00</span>
      <div class="progress-body">
        <strong>실행 준비 중</strong>
        <p>서버 응답을 기다리는 중입니다.</p>
      </div>
    </li>
  `;
}

function appendProgress(event) {
  if (progressSequence === 0) {
    progressList.innerHTML = "";
  }

  progressSequence += 1;

  const metaEntries = Object.entries(event.data || {});
  const metaHtml = metaEntries.length
    ? `<div class="progress-meta">${metaEntries
        .map(
          ([key, value]) =>
            `<span class="chip neutral">${escapeHtml(key)}: ${escapeHtml(
              Array.isArray(value) ? value.join(", ") : value
            )}</span>`
        )
        .join("")}</div>`
    : "";

  const item = document.createElement("li");
  item.className = `progress-item ${event.status || "info"}`;
  item.innerHTML = `
    <span class="progress-index">${String(progressSequence).padStart(2, "0")}</span>
    <div class="progress-body">
      <strong>${escapeHtml(event.message || "진행 중")}</strong>
      <p>${escapeHtml(event.step || "pipeline")}</p>
      ${metaHtml}
    </div>
  `;

  progressList.prepend(item);
  progressList.scrollTop = 0;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function clampPercentage(value) {
  const numeric = Number(value);

  if (!Number.isFinite(numeric)) {
    return 0;
  }

  const normalized = numeric >= 0 && numeric <= 1 ? numeric * 100 : numeric;
  return Math.max(0, Math.min(100, Math.round(normalized)));
}

function formatPercent(value) {
  return `${clampPercentage(value)}%`;
}

function formatPreviewScore(value) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric.toFixed(1) : "-";
}

function getPreviewSentimentHeadline(sentiment) {
  const entries = [
    ["긍정", Number(sentiment?.positive_ratio) || 0],
    ["중립", Number(sentiment?.neutral_ratio) || 0],
    ["부정", Number(sentiment?.negative_ratio) || 0],
  ].sort((left, right) => right[1] - left[1]);
  const tieThreshold = entries[0][1] > 1 ? 8 : 0.08;

  if (Math.abs(entries[0][1] - entries[1][1]) < tieThreshold) {
    return "의견 혼재";
  }

  if (entries[0][0] === "긍정") {
    return "긍정 우세";
  }

  if (entries[0][0] === "부정") {
    return "부정 우세";
  }

  return "중립 반응 우세";
}

function getPreviewReasons(purchase) {
  const candidates = purchase?.top_reasons?.length
    ? purchase.top_reasons
    : purchase?.key_selling_points || [];

  return candidates.filter(Boolean).slice(0, 3).join(" · ") || "핵심 구매 이유 없음";
}

function getPreviewCompareStatus(data) {
  if (!data?.aggregated_report?.find_competitor) {
    return "탐색 불필요";
  }

  if (data?.competitor_report?.best_pick) {
    return `추천 대안 ${data.competitor_report.best_pick}`;
  }

  if ((data?.competitor_candidates || []).length > 0) {
    return `후보 ${data.competitor_candidates.length}개 확보`;
  }

  return "비교 조건 충족";
}

function getHeroPanelToneFromVerdict(verdict) {
  if (verdict === "네거티브" || verdict === "부정") {
    return "negative";
  }

  if (verdict === "중립") {
    return "neutral";
  }

  if (verdict === "긍정") {
    return "positive";
  }

  return "default";
}

function setHeroPanelTone(tone = "default") {
  if (!heroPanel) {
    return;
  }

  heroPanel.dataset.previewTone = tone;
}

function setPreviewBarWidth(element, width) {
  element.style.width = `${clampPercentage(width)}%`;
}

function applyPreviewState(state) {
  previewSummary.textContent = state.summary;
  previewSummary.title = state.summary;
  previewScore.textContent = state.score;
  previewSentimentHeadline.textContent = state.sentimentHeadline;
  previewSentimentHeadline.title = state.sentimentHeadline;
  previewSentimentMeta.textContent = state.sentimentMeta;
  previewReasons.textContent = state.reasons;
  previewReasons.title = state.reasons;
  previewRecommendation.textContent = state.recommendation;
  previewRecommendation.title = state.recommendation;
  previewStepCollect.textContent = state.steps.collect;
  previewStepCollect.title = state.steps.collect;
  previewStepAnalyze.textContent = state.steps.analyze;
  previewStepAnalyze.title = state.steps.analyze;
  previewStepCompare.textContent = state.steps.compare;
  previewStepCompare.title = state.steps.compare;
  setPreviewBarWidth(previewBarPositive, state.bars.positive);
  setPreviewBarWidth(previewBarNeutral, state.bars.neutral);
  setPreviewBarWidth(previewBarNegative, state.bars.negative);
}

function resetHeroPreview() {
  setHeroPanelTone("default");
  applyPreviewState(DEFAULT_PREVIEW_STATE);
}

function renderLoadingPreview(rawQuery) {
  setHeroPanelTone("default");
  applyPreviewState({
    summary: `${rawQuery} 관련 리뷰를 수집하고 있습니다.`,
    score: "...",
    sentimentHeadline: "분석 준비 중",
    sentimentMeta: "리뷰 감정 분류 대기",
    reasons: "구매 이유 추출 대기",
    recommendation: "종합 판단 계산 중",
    steps: {
      collect: "웹 리뷰 수집 시작",
      analyze: "감정·이유 분석 대기",
      compare: "비교 조건 확인 중",
    },
    bars: {
      positive: 72,
      neutral: 52,
      negative: 24,
    },
  });
}

function renderFailedPreview(rawQuery) {
  setHeroPanelTone("default");
  applyPreviewState({
    summary: `${rawQuery} 조회 결과를 불러오지 못했습니다.`,
    score: "-",
    sentimentHeadline: "결과 없음",
    sentimentMeta: "응답을 다시 확인해 주세요.",
    reasons: "프리뷰를 생성하지 못했습니다.",
    recommendation: "재시도 필요",
    steps: {
      collect: "응답 실패",
      analyze: "결과 없음",
      compare: "진행 안 됨",
    },
    bars: {
      positive: 0,
      neutral: 0,
      negative: 0,
    },
  });
}

function renderHeroPreview(data) {
  const report = data?.aggregated_report || {};
  const sentiment = data?.sentiment || {};
  const reviewSummary = [
    Number.isFinite(data?.raw_review_count) ? `원문 ${data.raw_review_count}건` : null,
    Number.isFinite(data?.preprocessed_review_count)
      ? `정제 ${data.preprocessed_review_count}건`
      : null,
  ]
    .filter(Boolean)
    .join(" / ");

  applyPreviewState({
    summary: [report.product_name, report.summary].filter(Boolean).join(" · ") || DEFAULT_PREVIEW_STATE.summary,
    score: formatPreviewScore(report.overall_score),
    sentimentHeadline: getPreviewSentimentHeadline(sentiment),
    sentimentMeta: `긍정 ${formatPercent(sentiment.positive_ratio)} · 중립 ${formatPercent(
      sentiment.neutral_ratio
    )} · 부정 ${formatPercent(sentiment.negative_ratio)}`,
    reasons: getPreviewReasons(data?.purchase_reasons),
    recommendation: report.recommendation || "추천 판단 대기",
    steps: {
      collect: reviewSummary || "수집량 정보 없음",
      analyze: [report.verdict, report.recommendation].filter(Boolean).join(" · ") || "분석 결과 없음",
      compare: getPreviewCompareStatus(data),
    },
    bars: {
      positive: sentiment.positive_ratio,
      neutral: sentiment.neutral_ratio,
      negative: sentiment.negative_ratio,
    },
  });
  setHeroPanelTone(getHeroPanelToneFromVerdict(report.verdict));
}

function renderList(items, emptyMessage = "데이터 없음") {
  if (!items || items.length === 0) {
    return `<p>${escapeHtml(emptyMessage)}</p>`;
  }

  return `<ul class="bullet-list">${items
    .map((item) => `<li>${escapeHtml(item)}</li>`)
    .join("")}</ul>`;
}

function renderKeyValues(entries) {
  return `<ul class="kv-list">${entries
    .map(
      ([key, value]) => `
        <li>
          <span class="kv-key">${escapeHtml(key)}</span>
          <strong>${escapeHtml(value)}</strong>
        </li>
      `
    )
    .join("")}</ul>`;
}

function verdictChipClass(verdict) {
  if (verdict === "네거티브" || verdict === "부정") {
    return "chip negative";
  }
  if (verdict === "중립") {
    return "chip neutral";
  }
  return "chip";
}

function renderSummary(data) {
  const report = data.aggregated_report;
  const cards = [
    ["제품", report.product_name],
    ["판정", report.verdict],
    ["종합 점수", report.overall_score],
    ["추천", report.recommendation],
  ];

  summaryGrid.innerHTML = cards
    .map(
      ([label, value]) => `
        <article class="summary-card">
          <span class="label">${escapeHtml(label)}</span>
          <div class="value">${escapeHtml(value)}</div>
        </article>
      `
    )
    .join("");
}

function renderRoutingStrategy(strategy, tasks, reviewCounts) {
  const sourceChips = (strategy.sources || [])
    .map((source) => `<span class="chip neutral">${escapeHtml(source)}</span>`)
    .join("");
  const reviewFocusChips = (strategy.review_focus || [])
    .map((focus) => `<span class="chip">${escapeHtml(focus)}</span>`)
    .join("");
  const userContext = strategy.user_context || {};

  routingStrategyBox.innerHTML = `
    ${renderKeyValues([
      ["제품명", strategy.product_name],
      ["카테고리", strategy.product_category],
      ["브랜드", strategy.brand],
      ["사용자 상황", userContext.summary || "일반 사용자 기준"],
      ["리뷰 수집량", `${strategy.review_count_per_source} / source`],
      ["분석 깊이", strategy.depth],
      ["언어", strategy.language],
      ["기간", strategy.date_range],
      ["수집 리뷰 수", String(reviewCounts.raw_review_count)],
      ["전처리 후 리뷰 수", String(reviewCounts.preprocessed_review_count)],
      ["생성 태스크 수", String(tasks.length)],
    ])}
    <div class="metric-row">${sourceChips || "<span class='chip neutral'>source 없음</span>"}</div>
    <div class="metric-row">${
      reviewFocusChips || "<span class='chip neutral'>개인화 포인트 없음</span>"
    }</div>
  `;
}

function renderSentiment(sentiment) {
  sentimentBox.innerHTML = `
    <div class="metric-row">
      <span class="${verdictChipClass(sentiment.label)}">${escapeHtml(sentiment.label)}</span>
      <span class="chip neutral">score ${escapeHtml(sentiment.score)}</span>
    </div>
    ${renderKeyValues([
      ["긍정 비율", sentiment.positive_ratio],
      ["부정 비율", sentiment.negative_ratio],
      ["중립 비율", sentiment.neutral_ratio],
    ])}
    <h4>근거 문장</h4>
    ${renderList(sentiment.evidence, "근거 문장 없음")}
  `;
}

function renderPurchaseReasons(purchase) {
  const frequencyEntries = Object.entries(purchase.reason_frequency || {}).map(
    ([key, value]) => `${key}: ${value}`
  );

  purchaseBox.innerHTML = `
    <h4>Top Reasons</h4>
    ${renderList(purchase.top_reasons, "구매 이유 없음")}
    <h4>빈도</h4>
    ${renderList(frequencyEntries, "빈도 데이터 없음")}
    <h4>셀링 포인트</h4>
    ${renderList(purchase.key_selling_points, "셀링 포인트 없음")}
  `;
}

function renderComplaints(complaints) {
  const frequencyEntries = Object.entries(complaints.complaint_frequency || {}).map(
    ([key, value]) => `${key}: ${value}`
  );

  complaintBox.innerHTML = `
    <div class="metric-row">
      <span class="${complaints.severity === "high" ? "chip negative" : "chip neutral"}">
        severity ${escapeHtml(complaints.severity)}
      </span>
    </div>
    <h4>Top Complaints</h4>
    ${renderList(complaints.top_complaints, "불만 없음")}
    <h4>빈도</h4>
    ${renderList(frequencyEntries, "빈도 데이터 없음")}
    <h4>Critical Issues</h4>
    ${renderList(complaints.critical_issues, "치명 이슈 없음")}
  `;
}

function renderAggregatedReport(report, warnings) {
  const warningHtml =
    warnings && warnings.length > 0
      ? `<h4>Warnings</h4>${renderList(warnings)}`
      : "";

  aggregatedBox.innerHTML = `
    <div class="metric-row">
      <span class="${verdictChipClass(report.verdict)}">${escapeHtml(report.verdict)}</span>
      <span class="chip neutral">${escapeHtml(report.recommendation)}</span>
      <span class="${report.find_competitor ? "chip negative" : "chip"}">
        ${report.find_competitor ? "경쟁 제품 탐색 실행" : "대체 제품 탐색 불필요"}
      </span>
    </div>
    <p>${escapeHtml(report.summary)}</p>
    <h4>강점</h4>
    ${renderList(report.strengths, "강점 없음")}
    <h4>약점</h4>
    ${renderList(report.weaknesses, "약점 없음")}
    ${warningHtml}
  `;
}

function renderCompetitors(data) {
  if (!data.competitor_report) {
    const candidates = data.competitor_candidates || [];
    competitorBox.innerHTML = `
      <p>경쟁 제품 비교 결과가 없습니다.</p>
      ${
        candidates.length
          ? `<h4>발견된 후보</h4>${renderList(candidates)}`
          : "<p>경쟁 제품 후보 없음</p>"
      }
    `;
    return;
  }

  const report = data.competitor_report;
  const competitors = (report.competitors || [])
    .map(
      (item) => `
        <li>
          <strong>${escapeHtml(item.product_name)}</strong><br />
          verdict: ${escapeHtml(item.verdict)} / overall: ${escapeHtml(item.overall_score)}<br />
          가격 ${escapeHtml(item.price)} / 가성비 ${escapeHtml(item.value_for_money)} /
          가심비 ${escapeHtml(item.emotional_value)} / 품질 ${escapeHtml(item.quality_score)}
        </li>
      `
    )
    .join("");

  competitorBox.innerHTML = `
    <div class="metric-row">
      <span class="chip">${escapeHtml(report.best_pick)}</span>
      <span class="chip neutral">${escapeHtml(report.best_pick_reason)}</span>
    </div>
    <h4>원제품</h4>
    ${renderKeyValues([
      ["제품명", report.original_product.product_name],
      ["판정", report.original_product.verdict],
      ["종합 점수", report.original_product.overall_score],
      ["가격", report.original_product.price],
    ])}
    <h4>후보 비교</h4>
    <ul class="bullet-list">${competitors || "<li>후보 없음</li>"}</ul>
  `;
}

function renderResponse(data) {
  emptyState.classList.add("hidden");
  resultContent.classList.remove("hidden");

  renderHeroPreview(data);
  renderSummary(data);
  renderRoutingStrategy(data.routing_strategy, data.collection_tasks || [], {
    raw_review_count: data.raw_review_count,
    preprocessed_review_count: data.preprocessed_review_count,
  });
  renderSentiment(data.sentiment);
  renderPurchaseReasons(data.purchase_reasons);
  renderComplaints(data.complaints);
  renderAggregatedReport(data.aggregated_report, data.warnings);
  renderCompetitors(data);
  rawJsonBox.textContent = JSON.stringify(data, null, 2);
}

function clearRenderedResult() {
  resultContent.classList.add("hidden");
  emptyState.classList.remove("hidden");
  resetHeroPreview();
  summaryGrid.innerHTML = "";
  routingStrategyBox.innerHTML = "";
  sentimentBox.innerHTML = "";
  purchaseBox.innerHTML = "";
  complaintBox.innerHTML = "";
  aggregatedBox.innerHTML = "";
  competitorBox.innerHTML = "";
  rawJsonBox.textContent = "";
}

function getSavedHistory() {
  try {
    const raw = window.localStorage.getItem(ANALYSIS_HISTORY_STORAGE_KEY);
    if (!raw) {
      return [];
    }

    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function saveHistory(entries) {
  window.localStorage.setItem(ANALYSIS_HISTORY_STORAGE_KEY, JSON.stringify(entries));
}

function formatTimestamp(timestamp) {
  try {
    return new Date(timestamp).toLocaleString("ko-KR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return timestamp;
  }
}

function renderHistory() {
  const items = getSavedHistory();

  if (!items.length) {
    historyList.innerHTML = `<div class="history-empty">저장된 분석 기록이 없습니다.</div>`;
    return;
  }

  historyList.innerHTML = items
    .map(
      (item) => `
        <button class="history-button" type="button" data-history-id="${escapeHtml(item.id)}">
          <strong class="history-title">${escapeHtml(item.productName || item.request.raw_query)}</strong>
          <div class="history-meta">
            <span class="${verdictChipClass(item.verdict)}">${escapeHtml(item.verdict || "기록")}</span>
            <span class="chip neutral">${escapeHtml(formatTimestamp(item.createdAt))}</span>
          </div>
          <p class="history-query">${escapeHtml(item.request.raw_query)}</p>
        </button>
      `
    )
    .join("");
}

function persistAnalysisHistory(requestPayload, result) {
  const items = getSavedHistory();
  const productName = result?.aggregated_report?.product_name || requestPayload.raw_query;
  const verdict = result?.aggregated_report?.verdict || "기록";
  const deduped = items.filter(
    (item) =>
      !(
        item.request?.raw_query === requestPayload.raw_query &&
        (item.productName || "") === productName
      )
  );

  const nextItem = {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    createdAt: new Date().toISOString(),
    productName,
    verdict,
    request: {
      raw_query: requestPayload.raw_query,
      product_url: requestPayload.product_url,
      options: requestPayload.options,
    },
    result,
  };

  saveHistory([nextItem, ...deduped].slice(0, MAX_HISTORY_ITEMS));
  renderHistory();
}

function loadHistoryEntry(entryId) {
  const items = getSavedHistory();
  const entry = items.find((item) => item.id === entryId);
  if (!entry) {
    return;
  }

  rawQueryInput.value = entry.request?.raw_query || "";
  productUrlInput.value = entry.request?.product_url || "";
  setCustomSelectValue("depth", entry.request?.options?.depth || "quick");
  setCustomSelectValue("date-range", entry.request?.options?.date_range || "3months");

  resetProgress();
  renderResponse(entry.result);
  setStatus("success", "브라우저에 저장된 이전 분석 결과를 불러왔습니다.");
}

function clearHistory() {
  window.localStorage.removeItem(ANALYSIS_HISTORY_STORAGE_KEY);
  renderHistory();
  setStatus("idle", "저장된 분석 기록을 지웠습니다.");
}

function fillSample() {
  rawQueryInput.value =
    "허리가 약한 1인 가구인데 다이슨 V12 Detect Slim이 가볍고 청소하기 편한지 리뷰 분석해줘";
  productUrlInput.value = "";
  apiKeyInput.value = "";
  setCustomSelectValue("depth", "deep");
  setCustomSelectValue("date-range", "3months");
}

async function handleSubmit(event) {
  event.preventDefault();

  const apiBaseUrl = (apiBaseUrlInput.value.trim() || getDefaultApiBaseUrl()).replace(/\/+$/, "");
  const payload = {
    raw_query: rawQueryInput.value.trim(),
    product_url: productUrlInput.value.trim() || null,
    api_key: apiKeyInput.value.trim() || null,
    options: {
      depth: depthInput.value,
      date_range: dateRangeInput.value,
    },
  };

  if (!payload.raw_query) {
    setStatus("error", "분석 요청 문구를 입력해야 합니다.");
    return;
  }

  saveApiBaseUrl();
  submitButton.disabled = true;
  resetProgress();
  clearRenderedResult();
  renderLoadingPreview(payload.raw_query);
  setStatus("loading", "분석 파이프라인 실행 중입니다. 검색과 LLM 단계가 순차/병렬로 진행됩니다.");

  try {
    const response = await fetch(`${apiBaseUrl}/analyze/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(errorText || `HTTP ${response.status}`);
    }

    if (!response.body) {
      throw new Error("스트리밍 응답 본문이 없습니다.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let finalResult = null;

    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) {
          continue;
        }

        const streamEvent = JSON.parse(trimmed);

        if (streamEvent.type === "progress") {
          appendProgress(streamEvent);
          setStatus("loading", streamEvent.message || "분석 진행 중입니다.");
        } else if (streamEvent.type === "result") {
          finalResult = streamEvent.data;
        } else if (streamEvent.type === "error") {
          throw new Error(streamEvent.message || "알 수 없는 오류");
        }
      }
    }

    if (buffer.trim()) {
      const streamEvent = JSON.parse(buffer.trim());
      if (streamEvent.type === "result") {
        finalResult = streamEvent.data;
      } else if (streamEvent.type === "progress") {
        appendProgress(streamEvent);
      } else if (streamEvent.type === "error") {
        throw new Error(streamEvent.message || "알 수 없는 오류");
      }
    }

    if (!finalResult) {
      throw new Error("최종 결과 이벤트를 받지 못했습니다.");
    }

    renderResponse(finalResult);
    persistAnalysisHistory(payload, finalResult);
    setStatus("success", "분석이 완료되었습니다.");
  } catch (error) {
    renderFailedPreview(payload.raw_query);
    setStatus("error", `요청 실패: ${error.message}`);
  } finally {
    submitButton.disabled = false;
  }
}

restoreSavedApiBaseUrl();
initializeCustomSelects();
renderHistory();
resetProgress();
clearRenderedResult();
form.addEventListener("submit", handleSubmit);
sampleButton.addEventListener("click", fillSample);
clearHistoryButton.addEventListener("click", clearHistory);
historyList.addEventListener("click", (event) => {
  const button = event.target.closest("[data-history-id]");
  if (!button) {
    return;
  }
  loadHistoryEntry(button.getAttribute("data-history-id"));
});
