import json
import streamlit as st
import streamlit.components.v1 as components

# ============================================================
# 반응 속도 측정 페이지
# 저장 위치 예시:
# pages/1_reaction_time.py
# 또는
# pages/1_반응_속도_측정.py
# ============================================================

st.set_page_config(
    page_title="반응 속도 측정",
    page_icon="⚡",
    layout="wide",
)

st.markdown(
    """
<style>
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 3rem;
}
.main-title {
    font-size: 2.25rem;
    font-weight: 950;
    letter-spacing: -0.045em;
    line-height: 1.18;
    margin-bottom: .25rem;
}
.main-subtitle {
    color: #526070;
    font-size: 1.03rem;
    font-weight: 650;
    margin-bottom: 1.1rem;
}
.info-box {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 1rem 1.1rem;
    color: #334155;
    line-height: 1.68;
    font-weight: 620;
}
.warn-box {
    background: #fff7ed;
    border: 1px solid #fed7aa;
    border-radius: 16px;
    padding: 1rem 1.1rem;
    color: #9a3412;
    line-height: 1.6;
    font-weight: 760;
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown("<div class='main-title'>⚡ 반응 속도 측정</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='main-subtitle'>화면 색이 갑자기 바뀌는 순간 클릭하여 자신의 반응 시간을 측정합니다.</div>",
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class='info-box'>
이 페이지는 Streamlit 버튼이 아니라 <b>브라우저 내부 JavaScript</b>의 <code>performance.now()</code>로 시간을 측정합니다.
따라서 Streamlit 서버 왕복 지연이 거의 섞이지 않습니다.
측정한 평균 반응 시간은 자전거 정지거리 시뮬레이터의 <b>반응 시간</b> 값으로 사용할 수 있습니다.
</div>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("⚙️ 측정 설정")
    trial_count = st.slider("측정 횟수", 3, 10, 5, 1)
    st.divider()
    st.caption("대기 시간은 3~5초 사이에서 무작위로 정해집니다.")
    st.caption("게이지나 카운트다운 없이 갑자기 초록색으로 바뀝니다.")

settings = {
    "trialCount": int(trial_count),
    "minWait": 3.0,
    "maxWait": 5.0,
}

reaction_html = """
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>
  :root {
    --ink: #0f172a;
    --muted: #64748b;
    --line: #dbe3ee;
    --soft: #f8fafc;
    --idle: #2563eb;
    --wait: #f97316;
    --ready: #16a34a;
    --bad: #ef4444;
    --done: #334155;
  }

  * {
    box-sizing: border-box;
  }

  body {
    margin: 0;
    background: transparent;
    font-family: Pretendard, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    color: var(--ink);
  }

  .wrap {
    width: 100%;
    min-height: 780px;
    padding: 18px;
    border-radius: 24px;
    background: linear-gradient(180deg, #f8fbff 0%, #eef4ff 100%);
    border: 1px solid #e1e8f4;
  }

  .top {
    display: flex;
    justify-content: space-between;
    gap: 14px;
    align-items: flex-start;
    margin-bottom: 14px;
  }

  .title {
    font-size: 24px;
    font-weight: 950;
    letter-spacing: -0.03em;
    margin-bottom: 4px;
  }

  .desc {
    color: var(--muted);
    font-size: 14px;
    font-weight: 700;
    line-height: 1.45;
  }

  .controls {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  button {
    border: 0;
    border-radius: 999px;
    padding: 11px 16px;
    font-size: 14px;
    font-weight: 900;
    cursor: pointer;
    box-shadow: 0 8px 20px rgba(15, 23, 42, .12);
    transition: transform .08s ease, opacity .15s ease;
  }

  button:active {
    transform: translateY(1px);
  }

  .primary {
    color: white;
    background: #111827;
  }

  .secondary {
    color: var(--ink);
    background: white;
    border: 1px solid var(--line);
  }

  .layout {
    display: grid;
    grid-template-columns: 1.25fr .75fr;
    gap: 14px;
  }

  .panel {
    background: rgba(255,255,255,.88);
    border: 1px solid rgba(219, 227, 238, .95);
    border-radius: 22px;
    padding: 14px;
    box-shadow: 0 12px 30px rgba(15, 23, 42, .05);
  }

  .test-zone {
    position: relative;
    height: 440px;
    border-radius: 22px;
    overflow: hidden;
    background: var(--idle);
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    cursor: pointer;
    user-select: none;
    transition: background .08s ease, transform .12s ease;
  }

  .test-zone.wait {
    background: var(--wait);
  }

  .test-zone.ready {
    background: var(--ready);
  }

  .test-zone.bad {
    background: var(--bad);
  }

  .test-zone.done {
    background: var(--done);
  }

  .test-zone:active {
    transform: scale(.997);
  }

  .zone-content {
    color: white;
    padding: 24px;
  }

  .zone-main {
    font-size: 48px;
    font-weight: 1000;
    letter-spacing: -0.055em;
    line-height: 1.08;
    margin-bottom: 10px;
  }

  .zone-sub {
    font-size: 17px;
    font-weight: 800;
    opacity: .94;
    line-height: 1.5;
  }

  .trial-badge {
    position: absolute;
    top: 16px;
    left: 16px;
    padding: 8px 12px;
    border-radius: 999px;
    background: rgba(255,255,255,.20);
    color: white;
    font-size: 13px;
    font-weight: 900;
    backdrop-filter: blur(8px);
  }

  .secret-wait-note {
    position: absolute;
    bottom: 16px;
    left: 16px;
    right: 16px;
    padding: 9px 12px;
    border-radius: 999px;
    background: rgba(255,255,255,.18);
    color: white;
    font-size: 13px;
    font-weight: 850;
    backdrop-filter: blur(8px);
  }

  .metric-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    margin-bottom: 12px;
  }

  .metric {
    background: #ffffff;
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 12px;
  }

  .metric .k {
    color: var(--muted);
    font-size: 12px;
    font-weight: 850;
    margin-bottom: 4px;
  }

  .metric .v {
    color: var(--ink);
    font-size: 24px;
    font-weight: 1000;
    letter-spacing: -0.04em;
    line-height: 1.05;
  }

  .metric .s {
    color: #475569;
    font-size: 14px;
    font-weight: 850;
    margin-top: 4px;
  }

  .metric .n {
    color: var(--muted);
    font-size: 11px;
    font-weight: 700;
    margin-top: 3px;
  }

  .result-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .result-row {
    display: grid;
    grid-template-columns: 76px 1fr 112px;
    gap: 8px;
    align-items: center;
    font-size: 13px;
    font-weight: 850;
    color: var(--ink);
  }

  .bar-track {
    height: 14px;
    background: #e2e8f0;
    border-radius: 999px;
    overflow: hidden;
  }

  .bar {
    height: 100%;
    width: 0%;
    background: linear-gradient(90deg, #22c55e, #eab308, #ef4444);
    border-radius: 999px;
    transition: width .25s ease;
  }

  .record-time {
    text-align: right;
    line-height: 1.15;
  }

  .record-time .ms {
    color: #0f172a;
    font-weight: 950;
  }

  .record-time .sec {
    color: #64748b;
    font-size: 11px;
    font-weight: 800;
  }

  .guide {
    margin-top: 12px;
    padding: 13px 14px;
    border-radius: 16px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    color: #334155;
    line-height: 1.55;
    font-size: 13px;
    font-weight: 700;
  }

  .copy-box {
    margin-top: 12px;
    padding: 13px 14px;
    border-radius: 16px;
    background: #ecfdf5;
    border: 1px solid #a7f3d0;
    color: #065f46;
    line-height: 1.55;
    font-size: 13px;
    font-weight: 850;
  }

  .warning {
    margin-top: 12px;
    padding: 13px 14px;
    border-radius: 16px;
    background: #fff7ed;
    border: 1px solid #fed7aa;
    color: #9a3412;
    line-height: 1.55;
    font-size: 13px;
    font-weight: 800;
  }

  .small {
    color: var(--muted);
    font-size: 12px;
    font-weight: 700;
    line-height: 1.55;
  }

  @media (max-width: 900px) {
    .layout {
      grid-template-columns: 1fr;
    }
    .top {
      flex-direction: column;
    }
    .controls {
      justify-content: flex-start;
    }
    .zone-main {
      font-size: 35px;
    }
  }
</style>
</head>

<body>
<div class="wrap">
  <div class="top">
    <div>
      <div class="title">⚡ 반응 속도 측정</div>
      <div class="desc">
        초록색 화면으로 갑자기 바뀌는 순간 클릭하세요.
        주황색 화면에서 너무 빨리 누르면 무효입니다.
      </div>
    </div>
    <div class="controls">
      <button class="primary" onclick="startTest()">측정 시작</button>
      <button class="secondary" onclick="resetTest()">초기화</button>
      <button class="secondary" onclick="copyResult()">결과 복사</button>
    </div>
  </div>

  <div class="layout">
    <div class="panel">
      <div id="testZone" class="test-zone" onclick="handleZoneClick()">
        <div class="trial-badge" id="trialBadge">대기 중</div>
        <div class="zone-content">
          <div class="zone-main" id="zoneMain">측정 시작을 누르세요</div>
          <div class="zone-sub" id="zoneSub">
            초록색 화면이 나타나는 순간 클릭하면 반응 시간이 기록됩니다.
          </div>
        </div>
        <div class="secret-wait-note" id="secretWaitNote">
          대기 시간은 보이지 않습니다.
        </div>
      </div>

      <div class="guide">
        <b>측정 방법</b><br>
        1. 측정 시작을 누릅니다.<br>
        2. 주황색 화면에서는 기다립니다. 남은 시간은 표시되지 않습니다.<br>
        3. 3~5초 사이의 무작위 시점에 초록색 화면으로 바뀝니다.<br>
        4. 초록색 화면으로 바뀌는 순간 최대한 빠르게 클릭합니다.
      </div>

      <div class="warning">
        실제 주행 중 반응 시간은 피로, 스마트폰 사용, 이어폰 착용, 야간 시야, 주변 소음 등에 따라 더 길어질 수 있습니다.
      </div>
    </div>

    <div class="panel">
      <div class="metric-grid">
        <div class="metric">
          <div class="k">최근 기록</div>
          <div class="v" id="latestMs">-</div>
          <div class="s" id="latestSec">-</div>
          <div class="n">방금 측정한 반응 시간</div>
        </div>
        <div class="metric">
          <div class="k">평균</div>
          <div class="v" id="avgMs">-</div>
          <div class="s" id="avgSec">-</div>
          <div class="n">시뮬레이터 입력값</div>
        </div>
        <div class="metric">
          <div class="k">최고 기록</div>
          <div class="v" id="bestMs">-</div>
          <div class="s" id="bestSec">-</div>
          <div class="n">가장 빠른 반응</div>
        </div>
        <div class="metric">
          <div class="k">측정 횟수</div>
          <div class="v" id="trialCount">0/5</div>
          <div class="s">유효 측정</div>
          <div class="n">무효 클릭은 제외</div>
        </div>
      </div>

      <div class="result-list" id="resultList"></div>

      <div class="copy-box" id="copyBox">
        아직 측정값이 없습니다. 측정이 끝나면 평균 반응 시간이 ms와 초 단위로 표시됩니다.
      </div>

      <div class="guide">
        <b>정지거리 시뮬레이터와 연결</b><br>
        반응 시간 동안 자전거는 아직 제동하지 못하고 계속 이동합니다.
        반응 시간이 길어지면 정지거리 식의 일차항이 커집니다.
      </div>

      <div class="small" style="margin-top: 10px;">
        이 측정은 브라우저 내부의 performance.now()를 사용합니다.
        다만 모니터 주사율, 마우스·터치 입력 지연, 집중 상태에 따라 결과가 달라질 수 있습니다.
      </div>
    </div>
  </div>
</div>

<script>
const SETTINGS = __SETTINGS__;

let state = "idle";
let startTime = null;
let waitTimer = null;
let results = [];
let earlyCount = 0;
let currentDelay = 0;

const trialTarget = SETTINGS.trialCount;
const minWaitMs = SETTINGS.minWait * 1000;
const maxWaitMs = SETTINGS.maxWait * 1000;

const zone = document.getElementById("testZone");
const zoneMain = document.getElementById("zoneMain");
const zoneSub = document.getElementById("zoneSub");
const trialBadge = document.getElementById("trialBadge");
const resultList = document.getElementById("resultList");
const secretWaitNote = document.getElementById("secretWaitNote");

function msText(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "-";
  return `${Math.round(value)} ms`;
}

function secText(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "-";
  return `${(value / 1000).toFixed(3)} s`;
}

function secTextKorean(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return "-";
  return `${(value / 1000).toFixed(3)}초`;
}

function average(arr) {
  if (arr.length === 0) return null;
  return arr.reduce((a, b) => a + b, 0) / arr.length;
}

function median(arr) {
  if (arr.length === 0) return null;
  const sorted = [...arr].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 1) return sorted[mid];
  return (sorted[mid - 1] + sorted[mid]) / 2;
}

function setZone(nextState, main, sub) {
  state = nextState;
  zone.className = `test-zone ${nextState}`;
  zoneMain.textContent = main;
  zoneSub.textContent = sub;
}

function updateStats() {
  const latest = results.length > 0 ? results[results.length - 1] : null;
  const avg = average(results);
  const best = results.length > 0 ? Math.min(...results) : null;
  const worst = results.length > 0 ? Math.max(...results) : null;
  const med = median(results);

  document.getElementById("latestMs").textContent = msText(latest);
  document.getElementById("latestSec").textContent = secText(latest);
  document.getElementById("avgMs").textContent = msText(avg);
  document.getElementById("avgSec").textContent = secText(avg);
  document.getElementById("bestMs").textContent = msText(best);
  document.getElementById("bestSec").textContent = secText(best);
  document.getElementById("trialCount").textContent = `${results.length}/${trialTarget}`;

  resultList.innerHTML = "";
  for (let i = 0; i < trialTarget; i++) {
    const value = results[i];
    const row = document.createElement("div");
    row.className = "result-row";

    const label = document.createElement("div");
    label.textContent = `${i + 1}회차`;

    const track = document.createElement("div");
    track.className = "bar-track";

    const bar = document.createElement("div");
    bar.className = "bar";

    if (value !== undefined) {
      const width = Math.max(5, Math.min(100, (value / 800) * 100));
      bar.style.width = `${width}%`;
    } else {
      bar.style.width = "0%";
    }

    track.appendChild(bar);

    const text = document.createElement("div");
    text.className = "record-time";
    if (value !== undefined) {
      text.innerHTML = `<div class="ms">${msText(value)}</div><div class="sec">${secText(value)}</div>`;
    } else {
      text.innerHTML = `<div class="ms">-</div><div class="sec">-</div>`;
    }

    row.appendChild(label);
    row.appendChild(track);
    row.appendChild(text);
    resultList.appendChild(row);
  }

  const copyBox = document.getElementById("copyBox");
  if (avg === null) {
    copyBox.textContent = "아직 측정값이 없습니다. 측정이 끝나면 평균 반응 시간이 ms와 초 단위로 표시됩니다.";
  } else {
    copyBox.innerHTML = `
      평균 반응 시간: <b>${msText(avg)}</b> = <b>${secText(avg)}</b><br>
      최고 기록: <b>${msText(best)}</b> = <b>${secText(best)}</b><br>
      중앙값: <b>${msText(med)}</b> = <b>${secText(med)}</b><br>
      가장 느린 기록: <b>${msText(worst)}</b> = <b>${secText(worst)}</b><br>
      정지거리 시뮬레이터의 반응 시간에는 <b>${(avg / 1000).toFixed(3)}초</b>를 넣으면 됩니다.
    `;
  }

  if (results.length >= trialTarget) {
    setZone("done", "측정 완료", `평균 반응 시간은 ${msText(avg)} = ${secText(avg)}입니다. 다시 측정하려면 측정 시작을 누르세요.`);
    trialBadge.textContent = "완료";
    secretWaitNote.textContent = "측정 완료";
  } else {
    trialBadge.textContent = `${results.length + 1}/${trialTarget}회차`;
  }
}

function startTest() {
  clearTimeout(waitTimer);

  if (results.length >= trialTarget) {
    results = [];
    earlyCount = 0;
    updateStats();
  }

  beginTrial();
}

function beginTrial() {
  if (results.length >= trialTarget) {
    updateStats();
    return;
  }

  clearTimeout(waitTimer);

  currentDelay = minWaitMs + Math.random() * (maxWaitMs - minWaitMs);

  setZone("wait", "기다리세요...", "언제 바뀔지 알 수 없습니다. 초록색으로 바뀌는 순간 클릭하세요.");
  trialBadge.textContent = `${results.length + 1}/${trialTarget}회차`;
  secretWaitNote.textContent = "대기 시간은 숨겨져 있습니다.";

  waitTimer = setTimeout(() => {
    startTime = performance.now();
    setZone("ready", "지금 클릭!", "초록색으로 바뀌었습니다. 최대한 빠르게 클릭하세요.");
    secretWaitNote.textContent = "지금 클릭!";
  }, currentDelay);
}

function handleZoneClick() {
  if (state === "idle" || state === "done") {
    return;
  }

  if (state === "wait") {
    earlyCount += 1;
    clearTimeout(waitTimer);
    setZone("bad", "너무 빨랐습니다", "초록색으로 바뀐 뒤에 클릭해야 합니다. 잠시 후 같은 회차를 다시 시작합니다.");
    trialBadge.textContent = "무효";
    secretWaitNote.textContent = "무효 클릭";
    setTimeout(beginTrial, 1000);
    return;
  }

  if (state === "ready") {
    const reactionTime = performance.now() - startTime;
    results.push(reactionTime);
    clearTimeout(waitTimer);
    updateStats();

    if (results.length < trialTarget) {
      setZone("idle", `${Math.round(reactionTime)} ms = ${(reactionTime / 1000).toFixed(3)} s`, "기록되었습니다. 다음 회차를 곧 시작합니다.");
      secretWaitNote.textContent = "다음 회차 준비";
      setTimeout(beginTrial, 850);
    }
  }
}

function resetTest() {
  clearTimeout(waitTimer);
  results = [];
  earlyCount = 0;
  startTime = null;
  currentDelay = 0;
  setZone("idle", "측정 시작을 누르세요", "초록색 화면이 나타나는 순간 클릭하면 반응 시간이 기록됩니다.");
  trialBadge.textContent = "대기 중";
  secretWaitNote.textContent = "대기 시간은 보이지 않습니다.";
  updateStats();
}

function copyResult() {
  const avg = average(results);
  if (avg === null) {
    alert("복사할 측정 결과가 아직 없습니다.");
    return;
  }

  const best = Math.min(...results);
  const worst = Math.max(...results);
  const med = median(results);

  const lines = results.map((value, index) =>
    `- ${index + 1}회차: ${Math.round(value)} ms = ${(value / 1000).toFixed(3)} s`
  ).join("\\n");

  const text =
`반응 속도 측정 결과
- 유효 측정 횟수: ${results.length}회
- 평균 반응 시간: ${Math.round(avg)} ms = ${(avg / 1000).toFixed(3)} s
- 최고 기록: ${Math.round(best)} ms = ${(best / 1000).toFixed(3)} s
- 중앙값: ${Math.round(med)} ms = ${(med / 1000).toFixed(3)} s
- 가장 느린 기록: ${Math.round(worst)} ms = ${(worst / 1000).toFixed(3)} s
- 정지거리 시뮬레이터 입력값: ${(avg / 1000).toFixed(3)}초

회차별 기록
${lines}`;

  navigator.clipboard.writeText(text).then(() => {
    alert("측정 결과를 복사했습니다.");
  }).catch(() => {
    alert(text);
  });
}

updateStats();
</script>
</body>
</html>
"""

reaction_html = reaction_html.replace("__SETTINGS__", json.dumps(settings, ensure_ascii=False))
components.html(reaction_html, height=900, scrolling=True)

st.markdown("---")

st.markdown("## 수업에서 연결할 핵심 질문")

st.markdown(
    """
<div class='info-box'>
<b>질문 1.</b> 반응 시간이 0.5초인 사람과 1.5초인 사람이 같은 속도로 달리면, 정지거리는 얼마나 달라질까?<br>
<b>질문 2.</b> 반응 시간은 정지거리 식에서 왜 일차항으로 들어갈까?<br>
<b>질문 3.</b> 속도를 두 배로 높이면 반응거리는 두 배가 되지만, 제동거리는 왜 네 배에 가까워질까?
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
### 정지거리 시뮬레이터에 넣는 방법

예를 들어 평균 반응 시간이 `420 ms`라면,

```text
420 ms = 0.420초
```

이므로 정지거리 시뮬레이터의 반응 시간에 `0.420초`를 넣으면 됩니다.
"""
)
