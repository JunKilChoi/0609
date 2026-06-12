import math
import json
import html
import streamlit as st
import streamlit.components.v1 as components

# ============================================================
# 픽시 자전거 정지거리와 이차함수
# GitHub / Streamlit Cloud 실행 파일: app.py
# requirements.txt: streamlit
# ============================================================

st.set_page_config(
    page_title="픽시 자전거 정지거리와 이차함수",
    page_icon="🚲",
    layout="wide",
    initial_sidebar_state="expanded",
)

G = 9.8
APPROACH_DISTANCE = 8.0  # 위험 발견 전 짧은 등속 주행 구간. 정지거리 함수 S(x)에는 포함하지 않음.

ROAD_OPTIONS = {
    "마른 아스팔트": {"mu": 0.70, "desc": "비교적 잘 멈추는 노면"},
    "젖은 아스팔트": {"mu": 0.45, "desc": "비가 온 뒤처럼 제동거리가 늘어나는 노면"},
    "모래·낙엽길": {"mu": 0.25, "desc": "바퀴가 쉽게 미끄러질 수 있는 노면"},
    "빙판길": {"mu": 0.10, "desc": "제동이 매우 어려운 노면"},
}

CURVE_COLORS = [
    "#2563eb", "#ef4444", "#059669", "#7c3aed", "#f59e0b",
    "#0f766e", "#be123c", "#0891b2", "#9333ea", "#ea580c",
    "#16a34a", "#475569", "#db2777", "#0369a1", "#a16207"
]


# ------------------------------------------------------------
# 계산 함수
# ------------------------------------------------------------
def fmt_m(x: float) -> str:
    if x is None or not math.isfinite(x):
        return "-"
    if abs(x) >= 100:
        return f"{x:.0f} m"
    return f"{x:.1f} m"


def fmt_time(x: float) -> str:
    if x is None or not math.isfinite(x):
        return "-"
    return f"{x:.2f} s"


def calc_coefficients(reaction_time: float, mu: float) -> dict:
    """S(x)=Ax^2+Bx+0. x 단위는 km/h, S 단위는 m."""
    a_eff = mu * G
    A = 1 / (25.92 * a_eff) if a_eff > 0 else math.inf
    B = reaction_time / 3.6
    vertex_x = -B / (2 * A) if A > 0 and math.isfinite(A) else math.nan
    vertex_y = -(B * B) / (4 * A) if A > 0 and math.isfinite(A) else math.nan
    return {
        "a_eff": a_eff,
        "A": A,
        "B": B,
        "vertex_x": vertex_x,
        "vertex_y": vertex_y,
    }


def calc_result(speed_kmh: float, reaction_time: float, mu: float) -> dict:
    v = speed_kmh / 3.6
    coeff = calc_coefficients(reaction_time, mu)
    a_eff = coeff["a_eff"]

    reaction_distance = v * reaction_time
    braking_distance = (v * v) / (2 * a_eff) if a_eff > 0 else math.inf
    total_stopping_distance = reaction_distance + braking_distance
    braking_time = v / a_eff if a_eff > 0 else math.inf

    return {
        **coeff,
        "speed_kmh": speed_kmh,
        "speed_ms": v,
        "reaction_time": reaction_time,
        "reaction_distance": reaction_distance,
        "braking_distance": braking_distance,
        "total_stopping_distance": total_stopping_distance,
        "braking_time": braking_time,
        "approach_time": APPROACH_DISTANCE / v if v > 0 else 0.0,
        "physical_total_time": (APPROACH_DISTANCE / v if v > 0 else 0.0) + reaction_time + braking_time if math.isfinite(braking_time) else 0.0,
    }


def risk_label(total_distance: float) -> tuple[str, str]:
    if total_distance < 8:
        return "낮음", "현재 조건에서는 비교적 짧은 거리에서 멈춥니다."
    if total_distance < 18:
        return "주의", "보행자나 장애물이 가까이 있으면 위험할 수 있습니다."
    if total_distance < 35:
        return "위험", "정지거리가 상당히 길어졌습니다. 속도를 낮추는 것이 가장 효과적입니다."
    return "매우 위험", "속도와 노면 조건 때문에 정지거리가 급격히 길어졌습니다."


def make_curve(name: str, mass: float, speed_kmh: float, reaction_time: float, mu: float, color: str, group: str) -> dict:
    c = calc_coefficients(reaction_time, mu)
    return {
        "name": name,
        "mass": float(mass),
        "markerSpeed": float(speed_kmh),
        "reactionTime": float(reaction_time),
        "mu": float(mu),
        "A": float(c["A"]),
        "B": float(c["B"]),
        "aEff": float(c["a_eff"]),
        "color": color,
        "group": group,
    }


def dedupe_curves(curves: list[dict]) -> list[dict]:
    seen = set()
    out = []
    for c in curves:
        key = (round(c["mass"], 2), round(c["markerSpeed"], 2), round(c["reactionTime"], 4), round(c["mu"], 4), c["group"])
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


# ------------------------------------------------------------
# 인터랙티브 이차함수 그래프
# ------------------------------------------------------------
def build_interactive_graph_html(graph_data: dict) -> str:
    data_json = json.dumps(graph_data, ensure_ascii=False)
    template = r"""
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>
  :root {
    --ink: #0f172a;
    --muted: #64748b;
    --line: #e2e8f0;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: transparent;
    font-family: Pretendard, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    color: var(--ink);
  }
  .wrap {
    width: 100%;
    border: 1px solid #e1e8f4;
    border-radius: 22px;
    background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
    padding: 14px;
  }
  .top {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    align-items: flex-start;
    margin-bottom: 10px;
  }
  .title {
    font-size: 20px;
    font-weight: 950;
    letter-spacing: -0.03em;
  }
  .sub {
    color: var(--muted);
    font-size: 13px;
    font-weight: 720;
    margin-top: 3px;
    line-height: 1.45;
  }
  .buttons {
    display: flex;
    flex-wrap: wrap;
    gap: 7px;
    justify-content: flex-end;
  }
  button {
    border: 1px solid #dbe3ee;
    background: white;
    color: #0f172a;
    border-radius: 999px;
    padding: 8px 12px;
    font-weight: 900;
    cursor: pointer;
    box-shadow: 0 5px 14px rgba(15,23,42,.06);
  }
  button.primary {
    background: #111827;
    color: white;
    border-color: #111827;
  }
  button:active { transform: translateY(1px); }
  .canvas-box {
    width: 100%;
    height: 640px;
    border: 1px solid #e2e8f0;
    border-radius: 18px;
    overflow: hidden;
    background: #ffffff;
    position: relative;
  }
  canvas {
    width: 100%;
    height: 100%;
    display: block;
    cursor: grab;
    touch-action: none;
  }
  canvas:active { cursor: grabbing; }
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 14px;
    margin-top: 12px;
    font-size: 12px;
    color: #334155;
    font-weight: 820;
    line-height: 1.35;
  }
  .item { display: inline-flex; align-items: center; gap: 5px; }
  .swatch { width: 18px; height: 6px; border-radius: 999px; display: inline-block; }
  .note {
    margin-top: 10px;
    padding: 11px 13px;
    border-radius: 14px;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    color: #475569;
    font-size: 12px;
    font-weight: 750;
    line-height: 1.55;
  }
</style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <div>
      <div class="title">📈 이차함수 그래프: 드래그로 이동, 휠로 확대·축소</div>
      <div class="sub">실제 속도 영역 x ≥ 0은 실선, 수학적 확장 영역 x &lt; 0은 점선입니다. 여러 조건의 그래프를 중첩해 비교할 수 있습니다.</div>
    </div>
    <div class="buttons">
      <button class="primary" onclick="resetView()">전체 맞춤</button>
      <button onclick="zoomAtCenter(0.75)">확대</button>
      <button onclick="zoomAtCenter(1.33)">축소</button>
      <button onclick="focusPositive()">실제 속도 영역</button>
    </div>
  </div>
  <div class="canvas-box">
    <canvas id="graph"></canvas>
  </div>
  <div id="legend" class="legend"></div>
  <div class="note">
    조작법: 그래프 안을 누른 채 움직이면 화면이 이동합니다. 마우스 휠 또는 터치패드 스크롤로 확대·축소할 수 있습니다. 점선은 실제 주행 속도가 아니라, 완전제곱식과 평행이동을 이해하기 위한 수학적 확장입니다.
  </div>
</div>

<script>
const DATA = __DATA__;
const canvas = document.getElementById("graph");
const ctx = canvas.getContext("2d");

const margins = {left: 78, right: 28, top: 38, bottom: 72};

// Streamlit은 슬라이더 값을 바꿀 때 앱을 다시 그리므로,
// 그래프를 드래그/확대해 놓은 시야가 초기화될 수 있다.
// 브라우저 localStorage에 view를 저장해 비교군 설정을 바꿔도 시야를 유지한다.
const VIEW_STORAGE_KEY = "fixie_quadratic_graph_view_v1";
let view = {xMin: -40, xMax: 80, yMin: -20, yMax: 80};
let dragging = false;
let last = null;

function validView(v) {
  return v &&
    Number.isFinite(v.xMin) && Number.isFinite(v.xMax) &&
    Number.isFinite(v.yMin) && Number.isFinite(v.yMax) &&
    v.xMax > v.xMin && v.yMax > v.yMin &&
    Math.abs(v.xMax - v.xMin) >= 3 &&
    Math.abs(v.yMax - v.yMin) >= 1;
}

function saveView() {
  try {
    if (validView(view)) {
      localStorage.setItem(VIEW_STORAGE_KEY, JSON.stringify(view));
    }
  } catch (e) {
    // localStorage 사용이 막힌 환경이면 저장만 건너뛴다.
  }
}

function loadView() {
  try {
    const raw = localStorage.getItem(VIEW_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return validView(parsed) ? parsed : null;
  } catch (e) {
    return null;
  }
}

function clearSavedView() {
  try {
    localStorage.removeItem(VIEW_STORAGE_KEY);
  } catch (e) {}
}

function rect() { return canvas.getBoundingClientRect(); }
function plotWidth() { return rect().width - margins.left - margins.right; }
function plotHeight() { return rect().height - margins.top - margins.bottom; }
function sx(x) { return margins.left + (x - view.xMin) / (view.xMax - view.xMin) * plotWidth(); }
function sy(y) { return margins.top + plotHeight() - (y - view.yMin) / (view.yMax - view.yMin) * plotHeight(); }
function invX(px) { return view.xMin + (px - margins.left) / plotWidth() * (view.xMax - view.xMin); }
function invY(py) { return view.yMin + (margins.top + plotHeight() - py) / plotHeight() * (view.yMax - view.yMin); }
function f(curve, x) { return curve.A * x * x + curve.B * x; }

function niceStep(raw) {
  if (!isFinite(raw) || raw <= 0) return 1;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const norm = raw / mag;
  if (norm < 1.5) return 1 * mag;
  if (norm < 3.5) return 2 * mag;
  if (norm < 7.5) return 5 * mag;
  return 10 * mag;
}

function setBestView(xMin=-50, xMax=80) {
  const ys = [0];
  const n = 360;
  for (const curve of DATA.curves) {
    for (let i=0; i<=n; i++) {
      const x = xMin + (xMax - xMin) * i / n;
      ys.push(f(curve, x));
    }
    if (curve.markerSpeed >= xMin && curve.markerSpeed <= xMax) {
      ys.push(f(curve, curve.markerSpeed));
    }
  }
  let yMin = Math.min(...ys);
  let yMax = Math.max(...ys);
  const span = Math.max(8, yMax - yMin);
  view = {
    xMin,
    xMax,
    yMin: yMin - span * 0.18,
    yMax: yMax + span * 0.18
  };
}

function resetView() {
  clearSavedView();
  const maxMarker = Math.max(...DATA.curves.map(c => c.markerSpeed), DATA.selectedSpeed);
  setBestView(-50, Math.max(70, maxMarker + 25));
  saveView();
  draw();
}

function focusPositive() {
  const maxMarker = Math.max(...DATA.curves.map(c => c.markerSpeed), DATA.selectedSpeed);
  setBestView(0, Math.max(60, maxMarker + 20));
  saveView();
  draw();
}

function applyZoom(factor, anchorX, anchorY, mode="both") {
  const x0 = invX(anchorX);
  const y0 = invY(anchorY);

  let newXMin = view.xMin;
  let newXMax = view.xMax;
  let newYMin = view.yMin;
  let newYMax = view.yMax;

  if (mode === "both" || mode === "x") {
    newXMin = x0 + (view.xMin - x0) * factor;
    newXMax = x0 + (view.xMax - x0) * factor;
  }
  if (mode === "both" || mode === "y") {
    newYMin = y0 + (view.yMin - y0) * factor;
    newYMax = y0 + (view.yMax - y0) * factor;
  }

  if (Math.abs(newXMax - newXMin) < 3 || Math.abs(newYMax - newYMin) < 1) return;
  if (Math.abs(newXMax - newXMin) > 1000 || Math.abs(newYMax - newYMin) > 2000) return;

  view = {xMin:newXMin, xMax:newXMax, yMin:newYMin, yMax:newYMax};
  saveView();
  draw();
}

function zoomAtCenter(factor) {
  const r = rect();
  applyZoom(factor, r.width/2, r.height/2, "both");
}

function resizeCanvas() {
  const r = rect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.round(r.width * dpr);
  canvas.height = Math.round(r.height * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  draw();
}

function formatAxisNumber(value, step) {
  if (!isFinite(value)) return "";
  const absStep = Math.abs(step);
  if (absStep >= 10) return String(Math.round(value));
  if (absStep >= 1) return value.toFixed(Math.abs(value) < 1e-9 ? 0 : 1).replace(/\.0$/, "");
  if (absStep >= 0.1) return value.toFixed(1);
  return value.toFixed(2);
}

function drawGrid() {
  const r = rect();
  const w = r.width, h = r.height;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, w, h);

  const xStep = niceStep((view.xMax - view.xMin) / 9);
  const yStep = niceStep((view.yMax - view.yMin) / 8);

  const xTicks = [];
  const yTicks = [];

  // 1) 그래프 내부 격자선은 클리핑해서 그린다.
  ctx.save();
  ctx.beginPath();
  ctx.rect(margins.left, margins.top, plotWidth(), plotHeight());
  ctx.clip();

  ctx.strokeStyle = "#e7edf6";
  ctx.lineWidth = 1;

  let x = Math.floor(view.xMin / xStep) * xStep;
  while (x <= view.xMax + 1e-9) {
    const px = sx(x);
    xTicks.push({value: x, px});
    ctx.beginPath();
    ctx.moveTo(px, margins.top);
    ctx.lineTo(px, margins.top + plotHeight());
    ctx.stroke();
    x += xStep;
  }

  let y = Math.floor(view.yMin / yStep) * yStep;
  while (y <= view.yMax + 1e-9) {
    const py = sy(y);
    yTicks.push({value: y, py});
    ctx.beginPath();
    ctx.moveTo(margins.left, py);
    ctx.lineTo(margins.left + plotWidth(), py);
    ctx.stroke();
    y += yStep;
  }

  // 축선
  ctx.strokeStyle = "#1f2937";
  ctx.lineWidth = 2;
  if (view.xMin <= 0 && view.xMax >= 0) {
    const px = sx(0);
    ctx.beginPath();
    ctx.moveTo(px, margins.top);
    ctx.lineTo(px, margins.top + plotHeight());
    ctx.stroke();
  }
  if (view.yMin <= 0 && view.yMax >= 0) {
    const py = sy(0);
    ctx.beginPath();
    ctx.moveTo(margins.left, py);
    ctx.lineTo(margins.left + plotWidth(), py);
    ctx.stroke();
  }
  ctx.restore();

  // 2) x축·y축 수치 라벨은 클리핑 밖에서 그린다.
  ctx.fillStyle = "#475569";
  ctx.font = "800 12px Pretendard, Arial";
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  for (const tick of xTicks) {
    if (tick.px < margins.left - 1 || tick.px > margins.left + plotWidth() + 1) continue;
    ctx.fillText(formatAxisNumber(tick.value, xStep), tick.px, margins.top + plotHeight() + 10);
  }

  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  for (const tick of yTicks) {
    if (tick.py < margins.top - 1 || tick.py > margins.top + plotHeight() + 1) continue;
    ctx.fillText(formatAxisNumber(tick.value, yStep), margins.left - 10, tick.py);
  }

  // 축 제목
  ctx.fillStyle = "#0f172a";
  ctx.font = "850 15px Pretendard, Arial";
  ctx.textAlign = "center";
  ctx.textBaseline = "bottom";
  ctx.fillText("초기 속도 x (km/h)", margins.left + plotWidth()/2, h - 10);

  ctx.save();
  ctx.translate(19, margins.top + plotHeight()/2);
  ctx.rotate(-Math.PI/2);
  ctx.fillText("총 정지거리 S(x) (m)", 0, 0);
  ctx.restore();
}

function drawCurve(curve) {
  const n = Math.max(300, Math.floor(plotWidth()));
  const xMin = view.xMin;
  const xMax = view.xMax;

  function drawSegment(a, b, dashed) {
    if (b <= a) return;
    ctx.save();
    ctx.beginPath();
    ctx.rect(margins.left, margins.top, plotWidth(), plotHeight());
    ctx.clip();

    ctx.beginPath();
    let started = false;
    for (let i=0; i<=n; i++) {
      const x = a + (b-a) * i / n;
      const y = f(curve, x);
      const px = sx(x);
      const py = sy(y);
      if (!isFinite(py) || py < margins.top - 800 || py > margins.top + plotHeight() + 800) {
        started = false;
        continue;
      }
      if (!started) {
        ctx.moveTo(px, py);
        started = true;
      } else {
        ctx.lineTo(px, py);
      }
    }
    ctx.strokeStyle = curve.color;
    ctx.lineWidth = curve.group === "현재 조건" ? 4.5 : 3;
    ctx.globalAlpha = curve.group === "현재 조건" ? 1 : 0.78;
    ctx.setLineDash(dashed ? [10, 8] : []);
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.stroke();
    ctx.restore();
  }

  drawSegment(xMin, Math.min(0, xMax), true);
  drawSegment(Math.max(0, xMin), xMax, false);
}

function drawMarkers() {
  ctx.save();
  ctx.beginPath();
  ctx.rect(margins.left, margins.top, plotWidth(), plotHeight());
  ctx.clip();

  for (let i=0; i<DATA.curves.length; i++) {
    const curve = DATA.curves[i];
    const marker = curve.markerSpeed;
    if (marker < view.xMin || marker > view.xMax) continue;
    const y = f(curve, marker);
    const px = sx(marker);

    ctx.strokeStyle = curve.color;
    ctx.globalAlpha = i === 0 ? 0.82 : 0.45;
    ctx.lineWidth = i === 0 ? 2 : 1.5;
    ctx.setLineDash([6, 6]);
    ctx.beginPath();
    ctx.moveTo(px, margins.top);
    ctx.lineTo(px, margins.top + plotHeight());
    ctx.stroke();

    if (y >= view.yMin && y <= view.yMax) {
      ctx.setLineDash([]);
      ctx.globalAlpha = 1;
      ctx.fillStyle = curve.color;
      ctx.beginPath();
      ctx.arc(px, sy(y), i === 0 ? 6 : 5, 0, Math.PI*2);
      ctx.fill();
      ctx.strokeStyle = "white";
      ctx.lineWidth = 2;
      ctx.stroke();

      ctx.fillStyle = i === 0 ? "#0f172a" : curve.color;
      ctx.font = "900 12px Pretendard, Arial";
      ctx.textAlign = "left";
      ctx.textBaseline = "bottom";
      const shortName = curve.group.replace("비교군 ", "G");
      ctx.fillText(`${shortName}: ${marker.toFixed(0)} km/h, ${y.toFixed(1)} m`, px + 9, sy(y) - 8 - (i % 3) * 14);
    }
  }

  // vertex of current curve
  const current = DATA.curves[0];
  const A = current.A, B = current.B;
  const vx = -B / (2*A);
  const vy = f(current, vx);
  if (vx >= view.xMin && vx <= view.xMax && vy >= view.yMin && vy <= view.yMax) {
    ctx.globalAlpha = 1;
    ctx.setLineDash([]);
    ctx.fillStyle = "#ef4444";
    ctx.beginPath();
    ctx.arc(sx(vx), sy(vy), 5.5, 0, Math.PI*2);
    ctx.fill();
    ctx.font = "900 12px Pretendard, Arial";
    ctx.textAlign = "left";
    ctx.fillText(`꼭짓점 (${vx.toFixed(1)}, ${vy.toFixed(1)})`, sx(vx)+9, sy(vy)+18);
  }

  ctx.restore();
}

function drawTitle() {
  ctx.fillStyle = "#0f172a";
  ctx.font = "950 18px Pretendard, Arial";
  ctx.textAlign = "left";
  ctx.textBaseline = "top";
  ctx.fillText("S(x)=Ax²+Bx+0", margins.left, 12);

  ctx.font = "750 12px Pretendard, Arial";
  ctx.fillStyle = "#64748b";
  ctx.fillText("실선: x ≥ 0, 점선: x < 0", margins.left + 170, 16);
}

function draw() {
  drawGrid();
  for (const curve of DATA.curves) drawCurve(curve);
  drawMarkers();
  drawTitle();
}

function buildLegend() {
  const legend = document.getElementById("legend");
  legend.innerHTML = "";
  for (const curve of DATA.curves) {
    const div = document.createElement("div");
    div.className = "item";
    div.innerHTML = `<span class="swatch" style="background:${curve.color}"></span><span>${curve.name}</span>`;
    legend.appendChild(div);
  }
}

canvas.addEventListener("mousedown", (e) => {
  dragging = true;
  last = {x:e.offsetX, y:e.offsetY};
});
window.addEventListener("mouseup", () => dragging = false);
canvas.addEventListener("mouseleave", () => dragging = false);
canvas.addEventListener("mousemove", (e) => {
  if (!dragging) return;
  const dx = e.offsetX - last.x;
  const dy = e.offsetY - last.y;
  const xSpan = view.xMax - view.xMin;
  const ySpan = view.yMax - view.yMin;
  const dxWorld = -dx / plotWidth() * xSpan;
  const dyWorld = dy / plotHeight() * ySpan;
  view.xMin += dxWorld;
  view.xMax += dxWorld;
  view.yMin += dyWorld;
  view.yMax += dyWorld;
  last = {x:e.offsetX, y:e.offsetY};
  saveView();
  draw();
});

canvas.addEventListener("wheel", (e) => {
  e.preventDefault();
  const factor = e.deltaY < 0 ? 0.86 : 1.16;

  const inPlotX = e.offsetX >= margins.left && e.offsetX <= margins.left + plotWidth();
  const inPlotY = e.offsetY >= margins.top && e.offsetY <= margins.top + plotHeight();
  const onXAxis = inPlotX && e.offsetY > margins.top + plotHeight();
  const onYAxis = e.offsetX < margins.left && inPlotY;

  if (onXAxis) {
    applyZoom(factor, e.offsetX, margins.top + plotHeight()/2, "x");
  } else if (onYAxis) {
    applyZoom(factor, margins.left + plotWidth()/2, e.offsetY, "y");
  } else {
    applyZoom(factor, e.offsetX, e.offsetY, "both");
  }
}, {passive:false});

// touch pan
canvas.addEventListener("touchstart", (e) => {
  if (e.touches.length === 1) {
    dragging = true;
    const r = rect();
    last = {x:e.touches[0].clientX-r.left, y:e.touches[0].clientY-r.top};
  }
}, {passive:false});
canvas.addEventListener("touchmove", (e) => {
  if (!dragging || e.touches.length !== 1) return;
  e.preventDefault();
  const r = rect();
  const x = e.touches[0].clientX-r.left;
  const y = e.touches[0].clientY-r.top;
  const dx = x - last.x;
  const dy = y - last.y;
  const xSpan = view.xMax - view.xMin;
  const ySpan = view.yMax - view.yMin;
  view.xMin += -dx / plotWidth() * xSpan;
  view.xMax += -dx / plotWidth() * xSpan;
  view.yMin += dy / plotHeight() * ySpan;
  view.yMax += dy / plotHeight() * ySpan;
  last = {x, y};
  saveView();
  draw();
}, {passive:false});
canvas.addEventListener("touchend", () => dragging = false);

window.addEventListener("resize", resizeCanvas);
buildLegend();
// 최초 접속 시에는 x축 0~20 km/h, y축 0~15 m.
// 이후 사용자가 드래그/확대해 놓은 시야는 비교군 설정을 바꿔도 localStorage에서 복원한다.
const savedView = loadView();
if (savedView) {
  view = savedView;
} else {
  view = {xMin: 0, xMax: 20, yMin: 0, yMax: 15};
  saveView();
}
resizeCanvas();
</script>
</body>
</html>
"""
    return template.replace("__DATA__", data_json)


def show_interactive_graph(graph_data: dict):
    components.html(build_interactive_graph_html(graph_data), height=820, scrolling=False)


# ------------------------------------------------------------
# 자전거 시뮬레이션 HTML
# ------------------------------------------------------------
def build_simulation_html(data: dict) -> str:
    data_json = json.dumps(data, ensure_ascii=False)
    template = r"""
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
  :root {
    --ink: #0f172a;
    --muted: #64748b;
    --approach: #38bdf8;
    --reaction: #f59e0b;
    --brake: #ef4444;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    background: transparent;
    font-family: Pretendard, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    color: var(--ink);
  }
  .wrap {
    width: 100%;
    padding: 15px;
    border-radius: 22px;
    background: linear-gradient(180deg, #f8fbff 0%, #eef4ff 100%);
    border: 1px solid #e1e8f4;
  }
  .topbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
  }
  .title {
    font-weight: 950;
    font-size: 20px;
    letter-spacing: -0.03em;
  }
  .sub {
    margin-top: 3px;
    color: var(--muted);
    font-size: 13px;
    font-weight: 700;
    line-height: 1.45;
  }
  button {
    border: 0;
    border-radius: 999px;
    background: #111827;
    color: white;
    font-weight: 900;
    padding: 10px 15px;
    cursor: pointer;
    box-shadow: 0 8px 18px rgba(15,23,42,.15);
  }
  button:active { transform: translateY(1px); }
  .panel {
    background: rgba(255,255,255,.86);
    border: 1px solid rgba(219,227,238,.96);
    border-radius: 20px;
    padding: 12px;
    box-shadow: 0 12px 30px rgba(15,23,42,.05);
  }
  .legend {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 14px;
    margin-top: 8px;
    color: #475569;
    font-size: 12px;
    font-weight: 850;
  }
  .chip { display: inline-flex; align-items: center; gap: 5px; }
  .swatch { display: inline-block; width: 18px; height: 7px; border-radius: 999px; }
  svg { width: 100%; height: auto; display: block; }
  .label { fill: #0f172a; font-size: 14px; font-weight: 950; }
  .small { fill: #64748b; font-size: 12px; font-weight: 800; }
  .road-line { stroke: rgba(255,255,255,.55); stroke-width: 3; stroke-dasharray: 21 16; stroke-linecap: round; }
  .wheel { fill: #f8fafc; stroke: #0f172a; stroke-width: 5; }
  .spoke { stroke: #0f172a; stroke-width: 2; opacity: .75; }
  .frame { stroke: #dc2626; stroke-width: 6; fill: none; stroke-linecap: round; stroke-linejoin: round; }
  .black-line { stroke: #0f172a; stroke-width: 6; fill: none; stroke-linecap: round; stroke-linejoin: round; }
  .rider { stroke: #111827; stroke-width: 7; fill: none; stroke-linecap: round; stroke-linejoin: round; }
  .head { fill: #111827; }
  .smoke { fill: #374151; stroke: #111827; stroke-width: 1.8; }
  .skid { stroke: #111827; stroke-width: 6; stroke-linecap: round; opacity: 0; }
  .time-charts {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    margin-top: 14px;
  }
  .time-chart-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 16px;
    padding: 10px 10px 8px;
  }
  .time-chart-title {
    color: #0f172a;
    font-size: 13px;
    font-weight: 950;
    margin: 0 0 6px 2px;
  }
  .time-canvas {
    width: 100%;
    height: 430px;
    display: block;
  }
  .energy-chart-card {
    grid-column: 1 / -1;
  }
  .energy-canvas {
    width: 100%;
    height: 560px;
    display: block;
  }
  @media (max-width: 900px) {
    .time-charts { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>
<div class="wrap">
  <div class="topbar">
    <div>
      <div class="title">🚲 실제 시간 기반 시뮬레이션</div>
      <div class="sub">1배속에서는 물리 시간 1초가 실제 화면에서도 1초입니다. 배속을 낮추면 더 천천히 관찰할 수 있습니다.</div>
    </div>
    <button onclick="restart()">다시 재생</button>
  </div>
  <div class="panel">
    <svg id="sim" viewBox="0 0 1080 430" aria-label="픽시 자전거 정지거리 시뮬레이션">
      <defs>
        <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#dff4ff"/>
          <stop offset="100%" stop-color="#f8fafc"/>
        </linearGradient>
        <linearGradient id="roadGrad" x1="0" x2="1">
          <stop offset="0%" stop-color="#475569"/>
          <stop offset="100%" stop-color="#64748b"/>
        </linearGradient>
      </defs>

      <rect x="0" y="0" width="1080" height="430" fill="url(#sky)"/>
      <rect x="56" y="238" width="968" height="86" rx="28" fill="url(#roadGrad)"/>
      <line x1="78" y1="281" x2="1002" y2="281" class="road-line"/>

      <rect id="approachBar" x="78" y="338" width="0" height="16" rx="8" fill="rgba(56,189,248,.78)"/>
      <rect id="reactionBar" x="78" y="360" width="0" height="16" rx="8" fill="rgba(245,158,11,.78)"/>
      <rect id="brakeBar" x="78" y="382" width="0" height="16" rx="8" fill="rgba(239,68,68,.78)"/>

      <line id="startMark" x1="78" y1="218" x2="78" y2="410" stroke="#0f172a" stroke-width="3"/>
      <line id="dangerMark" x1="78" y1="218" x2="78" y2="410" stroke="#38bdf8" stroke-width="3"/>
      <line id="brakeMark" x1="78" y1="218" x2="78" y2="410" stroke="#f59e0b" stroke-width="3"/>
      <line id="stopMark" x1="1002" y1="218" x2="1002" y2="410" stroke="#ef4444" stroke-width="3"/>

      <text id="phaseText" x="78" y="56" class="label">대기</text>
      <text id="distanceText" x="78" y="78" class="small">시뮬레이션을 시작합니다.</text>
      <text id="clockText" x="78" y="100" class="small">물리 시간 0.00초 / 실제 재생 시간 0.00초</text>

      <text id="startText" x="140" y="210" text-anchor="middle" class="small">출발</text>
      <text id="dangerText" x="78" y="210" text-anchor="middle" class="small">위험 발견</text>
      <text id="brakeText" x="78" y="210" text-anchor="middle" class="small">제동 시작</text>
      <text id="stopText" x="1002" y="210" text-anchor="middle" class="small">정지</text>

      <g id="smokeGroup">
        <circle id="smoke1" class="smoke" opacity="0" cx="0" cy="0" r="10"/>
        <circle id="smoke2" class="smoke" opacity="0" cx="0" cy="0" r="14"/>
        <circle id="smoke3" class="smoke" opacity="0" cx="0" cy="0" r="8"/>
        <circle id="smoke4" class="smoke" opacity="0" cx="0" cy="0" r="12"/>
        <circle id="smoke5" class="smoke" opacity="0" cx="0" cy="0" r="11"/>
        <circle id="smoke6" class="smoke" opacity="0" cx="0" cy="0" r="15"/>
        <circle id="smoke7" class="smoke" opacity="0" cx="0" cy="0" r="9"/>
        <circle id="smoke8" class="smoke" opacity="0" cx="0" cy="0" r="13"/>
      </g>
      <line id="skidLine" class="skid" x1="0" y1="0" x2="0" y2="0"/>

      <g id="bike" transform="translate(78 250)">
        <ellipse cx="0" cy="45" rx="72" ry="11" fill="rgba(15,23,42,.16)"/>

        <g id="rearWheel">
          <circle class="wheel" cx="-48" cy="28" r="27"/>
          <line class="spoke" x1="-48" y1="1" x2="-48" y2="55"/>
          <line class="spoke" x1="-75" y1="28" x2="-21" y2="28"/>
          <line class="spoke" x1="-67" y1="9" x2="-29" y2="47"/>
          <line class="spoke" x1="-67" y1="47" x2="-29" y2="9"/>
        </g>

        <g id="frontWheel">
          <circle class="wheel" cx="62" cy="28" r="27"/>
          <line class="spoke" x1="62" y1="1" x2="62" y2="55"/>
          <line class="spoke" x1="35" y1="28" x2="89" y2="28"/>
          <line class="spoke" x1="43" y1="9" x2="81" y2="47"/>
          <line class="spoke" x1="43" y1="47" x2="81" y2="9"/>
        </g>

        <path class="frame" d="M -48 28 L -14 -22 L 18 28 L -48 28 M -14 -22 L 62 28 M 18 28 L 62 28 M -14 -22 L -4 -50 M 45 -13 L 62 28 M 45 -13 L 72 -22"/>
        <line class="black-line" x1="-21" y1="-54" x2="11" y2="-54"/>
        <line class="black-line" x1="61" y1="-23" x2="78" y2="-28"/>

        <circle class="head" cx="-3" cy="-91" r="13"/>
        <path class="rider" d="M -4 -76 L 14 -44"/>
        <path class="rider" d="M 6 -61 L 45 -18"/>
        <path class="rider" d="M 12 -44 L -15 -22"/>
        <path class="rider" d="M 12 -44 L 18 28"/>
        <path class="rider" d="M -15 -22 L -4 -50"/>
        <path class="rider" d="M 18 28 L 35 12"/>
      </g>
    </svg>

    <div class="legend">
      <span class="chip"><span class="swatch" style="background:var(--approach)"></span>등속 주행: 위험 발견 전</span>
      <span class="chip"><span class="swatch" style="background:var(--reaction)"></span>반응 거리: 위험을 봤지만 아직 제동 전</span>
      <span class="chip"><span class="swatch" style="background:var(--brake)"></span>제동 거리: 마찰력이 일을 하며 운동에너지 감소</span>
    </div>

    <div class="time-charts">
      <div class="time-chart-card">
        <div class="time-chart-title">속도-시간 그래프</div>
        <canvas id="speedChart" class="time-canvas"></canvas>
      </div>
      <div class="time-chart-card">
        <div class="time-chart-title">이동거리-시간 그래프</div>
        <canvas id="distanceChart" class="time-canvas"></canvas>
      </div>
      <div class="time-chart-card energy-chart-card">
        <div class="time-chart-title">에너지 전환 그래프: 운동에너지 + 마찰로 잃은 에너지 = 총에너지</div>
        <canvas id="energyChart" class="energy-canvas"></canvas>
      </div>
    </div>
  </div>
</div>

<script>
const DATA = __DATA__;

const X0 = 78;      // 자전거 그룹의 시작 translate x
const X1 = 1002;    // 정지 기준선: 앞바퀴 중심이 도달해야 하는 위치
const ROAD_Y = 250;
const WHEEL_Y = ROAD_Y + 28;

// 자전거 SVG 내부 좌표 기준
// 앞으로 이동한 거리의 기준점은 자전거 몸통 중심이 아니라 앞바퀴 중심이다.
const REAR_WHEEL_LOCAL_X = -48;
const FRONT_WHEEL_LOCAL_X = 62;
const FRONT_REF_START_X = X0 + FRONT_WHEEL_LOCAL_X;
const FRONT_REF_END_X = X1;
const VISUAL_PATH_WIDTH = FRONT_REF_END_X - FRONT_REF_START_X;

let raf = null;
let startReal = null;

function setAttr(id, key, val) {
  const el = document.getElementById(id);
  if (el) el.setAttribute(key, val);
}
function setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}
function fmt(x) {
  if (x >= 100) return `${x.toFixed(0)} m`;
  return `${x.toFixed(1)} m`;
}


const speedCanvas = document.getElementById("speedChart");
const distanceCanvas = document.getElementById("distanceChart");
const energyCanvas = document.getElementById("energyChart");

function resizeChartCanvas(canvas) {
  if (!canvas) return null;
  const r = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.max(1, Math.round(r.width * dpr));
  canvas.height = Math.max(1, Math.round(r.height * dpr));
  const c = canvas.getContext("2d");
  c.setTransform(dpr, 0, 0, dpr, 0, 0);
  return {ctx: c, w: r.width, h: r.height};
}

function speedAtTime(t) {
  const v = DATA.speedMs;
  const a = DATA.aEff;
  if (DATA.speedKmh <= 0) return 0;
  if (t < DATA.approachTime + DATA.reactionTime) return v;
  const tb = t - DATA.approachTime - DATA.reactionTime;
  return Math.max(0, v - a * tb);
}

function distanceAtTime(t) {
  const v = DATA.speedMs;
  const a = DATA.aEff;
  if (DATA.speedKmh <= 0) return 0;
  if (t < DATA.approachTime) return v * t;
  if (t < DATA.approachTime + DATA.reactionTime) {
    return DATA.approachDistance + v * (t - DATA.approachTime);
  }
  const tb = t - DATA.approachTime - DATA.reactionTime;
  const s = DATA.approachDistance + DATA.reactionDistance + v * tb - 0.5 * a * tb * tb;
  return Math.max(0, Math.min(DATA.approachDistance + DATA.totalStoppingDistance, s));
}

function niceChartStep(raw) {
  if (!isFinite(raw) || raw <= 0) return 1;
  const mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const norm = raw / mag;
  if (norm < 1.5) return 1 * mag;
  if (norm < 3.5) return 2 * mag;
  if (norm < 7.5) return 5 * mag;
  return 10 * mag;
}

function chartTickLabel(v, step) {
  if (Math.abs(step) >= 10) return String(Math.round(v));
  if (Math.abs(step) >= 1) return v.toFixed(1).replace(/\.0$/, "");
  return v.toFixed(2);
}

function drawTimeChart(canvas, kind, currentT) {
  const info = resizeChartCanvas(canvas);
  if (!info) return;
  const ctx = info.ctx, w = info.w, h = info.h;
  const m = {left: 54, right: 18, top: 20, bottom: 38};
  const pw = w - m.left - m.right;
  const ph = h - m.top - m.bottom;
  const totalT = Math.max(0.001, DATA.approachTime + DATA.reactionTime + DATA.brakingTime);
  // y축 최대값은 실제 최대값에 맞추고, 그래프 패널 자체를 세로로 길게 만들어 모양이 잘 보이게 한다.
  const yMaxRaw = kind === "speed"
    ? Math.max(5, DATA.speedMs * 3.6)
    : Math.max(5, DATA.approachDistance + DATA.totalStoppingDistance);
  const yStep = niceChartStep(yMaxRaw / 5);
  const yMax = Math.ceil(yMaxRaw / yStep) * yStep;
  const xStep = niceChartStep(totalT / 6);

  const sxT = t => m.left + (t / totalT) * pw;
  const syV = y => m.top + ph - (y / yMax) * ph;
  const valueAt = t => kind === "speed" ? speedAtTime(t) * 3.6 : distanceAtTime(t);

  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, w, h);

  // grid and y labels
  ctx.strokeStyle = "#e7edf6";
  ctx.lineWidth = 1;
  ctx.fillStyle = "#64748b";
  ctx.font = "800 11px Pretendard, Arial";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  for (let y=0; y<=yMax+1e-9; y+=yStep) {
    const py = syV(y);
    ctx.beginPath();
    ctx.moveTo(m.left, py);
    ctx.lineTo(m.left + pw, py);
    ctx.stroke();
    ctx.fillText(chartTickLabel(y, yStep), m.left - 8, py);
  }

  // x labels
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  for (let t=0; t<=totalT+1e-9; t+=xStep) {
    const px = sxT(t);
    ctx.beginPath();
    ctx.moveTo(px, m.top);
    ctx.lineTo(px, m.top + ph);
    ctx.stroke();
    ctx.fillText(chartTickLabel(t, xStep), px, m.top + ph + 8);
  }

  // axes
  ctx.strokeStyle = "#1f2937";
  ctx.lineWidth = 1.8;
  ctx.beginPath();
  ctx.moveTo(m.left, m.top);
  ctx.lineTo(m.left, m.top + ph);
  ctx.lineTo(m.left + pw, m.top + ph);
  ctx.stroke();

  // event markers
  const events = [
    {t: DATA.approachTime, label: "위험 발견", color: "#38bdf8"},
    {t: DATA.approachTime + DATA.reactionTime, label: "제동 시작", color: "#f59e0b"},
    {t: totalT, label: "정지", color: "#ef4444"},
  ];
  ctx.font = "850 10px Pretendard, Arial";
  for (const ev of events) {
    const px = sxT(ev.t);
    ctx.strokeStyle = ev.color;
    ctx.lineWidth = 1.5;
    ctx.setLineDash([5, 5]);
    ctx.beginPath();
    ctx.moveTo(px, m.top);
    ctx.lineTo(px, m.top + ph);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.save();
    ctx.translate(px + 4, m.top + 10);
    ctx.rotate(-Math.PI/2);
    ctx.fillStyle = ev.color;
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    ctx.fillText(ev.label, 0, 0);
    ctx.restore();
  }

  // curve
  ctx.save();
  ctx.beginPath();
  ctx.rect(m.left, m.top, pw, ph);
  ctx.clip();
  ctx.beginPath();
  const n = 240;
  for (let i=0; i<=n; i++) {
    const t = totalT * i / n;
    const x = sxT(t);
    const y = syV(valueAt(t));
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.strokeStyle = kind === "speed" ? "#2563eb" : "#059669";
  ctx.lineWidth = 3;
  ctx.lineCap = "round";
  ctx.lineJoin = "round";
  ctx.stroke();
  ctx.restore();

  // current marker
  const tNow = Math.max(0, Math.min(totalT, currentT));
  const xNow = sxT(tNow);
  const yNow = syV(valueAt(tNow));
  ctx.strokeStyle = "#111827";
  ctx.lineWidth = 1.5;
  ctx.setLineDash([5,5]);
  ctx.beginPath();
  ctx.moveTo(xNow, m.top);
  ctx.lineTo(xNow, m.top + ph);
  ctx.stroke();
  ctx.setLineDash([]);
  ctx.fillStyle = "#111827";
  ctx.beginPath();
  ctx.arc(xNow, yNow, 5, 0, Math.PI*2);
  ctx.fill();

  ctx.fillStyle = "#0f172a";
  ctx.font = "900 11px Pretendard, Arial";
  ctx.textAlign = "left";
  ctx.textBaseline = "bottom";
  const unit = kind === "speed" ? "km/h" : "m";
  ctx.fillText(`${valueAt(tNow).toFixed(1)} ${unit}`, Math.min(xNow + 8, m.left + pw - 70), Math.max(yNow - 7, m.top + 12));

  // axis labels
  ctx.fillStyle = "#334155";
  ctx.font = "850 11px Pretendard, Arial";
  ctx.textAlign = "center";
  ctx.textBaseline = "bottom";
  ctx.fillText("시간 t (s)", m.left + pw/2, h - 2);
  ctx.save();
  ctx.translate(12, m.top + ph/2);
  ctx.rotate(-Math.PI/2);
  ctx.fillText(kind === "speed" ? "속도 (km/h)" : "이동거리 (m)", 0, 0);
  ctx.restore();
}

function energyValuesAtTime(t) {
  const mass = DATA.massKg;
  const vNow = speedAtTime(t);
  const initialKE = 0.5 * mass * DATA.speedMs * DATA.speedMs;
  const kinetic = 0.5 * mass * vNow * vNow;
  const frictionLoss = Math.max(0, initialKE - kinetic);
  return {
    kinetic,
    frictionLoss,
    total: kinetic + frictionLoss,
    initialKE
  };
}

function jouleLabel(v, step) {
  if (!isFinite(v)) return "";
  if (Math.abs(v) >= 1000) return `${(v/1000).toFixed(Math.abs(step) >= 1000 ? 0 : 1)}k`;
  if (Math.abs(step) >= 10) return String(Math.round(v));
  return v.toFixed(1).replace(/\.0$/, "");
}

function drawEnergyChart(currentT) {
  const canvas = energyCanvas;
  const info = resizeChartCanvas(canvas);
  if (!info) return;
  const ctx = info.ctx, w = info.w, h = info.h;

  // 0J x축을 화면 바닥에 붙이지 않고 충분히 위로 올려 고정한다.
  // 이렇게 해야 0J 축, 0J 숫자, 시간 눈금이 절대 잘리지 않는다.
  const m = {left: 78, right: 24, top: 30, bottom: 118};
  const pw = w - m.left - m.right;
  const xAxisY = h - m.bottom;
  const ph = xAxisY - m.top;

  const totalT = Math.max(0.001, DATA.approachTime + DATA.reactionTime + DATA.brakingTime);
  const initialKE = 0.5 * DATA.massKg * DATA.speedMs * DATA.speedMs;
  const yMaxRaw = Math.max(100, initialKE * 1.10);
  const yStep = niceChartStep(yMaxRaw / 5);
  const yMax = Math.ceil(yMaxRaw / yStep) * yStep;
  const xStep = niceChartStep(totalT / 7);

  const sxT = t => m.left + (t / totalT) * pw;
  const syE = e => xAxisY - (Math.max(0, e) / yMax) * ph;

  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, w, h);

  // grid and y labels
  ctx.strokeStyle = "#e7edf6";
  ctx.lineWidth = 1;
  ctx.fillStyle = "#64748b";
  ctx.font = "800 11px Pretendard, Arial";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  for (let y=0; y<=yMax+1e-9; y+=yStep) {
    const py = syE(y);
    ctx.beginPath();
    ctx.moveTo(m.left, py);
    ctx.lineTo(m.left + pw, py);
    ctx.stroke();
    ctx.fillText(jouleLabel(y, yStep), m.left - 8, py);
  }

  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  for (let t=0; t<=totalT+1e-9; t+=xStep) {
    const px = sxT(t);
    ctx.beginPath();
    ctx.moveTo(px, m.top);
    ctx.lineTo(px, xAxisY);
    ctx.stroke();
    ctx.fillText(chartTickLabel(t, xStep), px, xAxisY + 9);
  }

  // y축과 0J x축을 화면 안쪽에 분명하게 그린다.
  ctx.strokeStyle = "#0f172a";
  ctx.lineWidth = 3.0;
  ctx.beginPath();
  ctx.moveTo(m.left, m.top);
  ctx.lineTo(m.left, xAxisY);
  ctx.lineTo(m.left + pw, xAxisY);
  ctx.stroke();

  // 0J가 반드시 보이도록 축 옆에 굵게 다시 표시한다.
  ctx.save();
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(4, xAxisY - 13, m.left - 10, 26);
  ctx.fillStyle = "#0f172a";
  ctx.font = "950 13px Pretendard, Arial";
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  ctx.fillText("0 J", m.left - 9, xAxisY);
  ctx.restore();

  const events = [
    {t: DATA.approachTime, label: "위험 발견", color: "#38bdf8"},
    {t: DATA.approachTime + DATA.reactionTime, label: "제동 시작", color: "#f59e0b"},
    {t: totalT, label: "정지", color: "#ef4444"},
  ];
  ctx.font = "850 10px Pretendard, Arial";
  for (const ev of events) {
    const px = sxT(ev.t);
    ctx.strokeStyle = ev.color;
    ctx.lineWidth = 1.5;
    ctx.setLineDash([5, 5]);
    ctx.beginPath();
    ctx.moveTo(px, m.top);
    ctx.lineTo(px, xAxisY);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.save();
    ctx.translate(px + 4, m.top + 10);
    ctx.rotate(-Math.PI/2);
    ctx.fillStyle = ev.color;
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    ctx.fillText(ev.label, 0, 0);
    ctx.restore();
  }

  function drawEnergyLine(kind, color, width=3) {
    ctx.save();
    ctx.beginPath();
    ctx.rect(m.left, m.top, pw, ph);
    ctx.clip();
    ctx.beginPath();
    const n = 280;
    for (let i=0; i<=n; i++) {
      const t = totalT * i / n;
      const vals = energyValuesAtTime(t);
      const val = vals[kind];
      const x = sxT(t);
      const y = syE(val);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.stroke();
    ctx.restore();
  }

  drawEnergyLine("kinetic", "#2563eb", 3.2);
  drawEnergyLine("frictionLoss", "#ef4444", 3.2);
  drawEnergyLine("total", "#059669", 2.8);

  const tNow = Math.max(0, Math.min(totalT, currentT));
  const xNow = sxT(tNow);
  ctx.strokeStyle = "#111827";
  ctx.lineWidth = 1.5;
  ctx.setLineDash([5,5]);
  ctx.beginPath();
  ctx.moveTo(xNow, m.top);
  ctx.lineTo(xNow, xAxisY);
  ctx.stroke();
  ctx.setLineDash([]);

  const valsNow = energyValuesAtTime(tNow);
  const markers = [
    {kind:"kinetic", color:"#2563eb", label:"운동"},
    {kind:"frictionLoss", color:"#ef4444", label:"마찰 손실"},
    {kind:"total", color:"#059669", label:"총"},
  ];
  for (const mk of markers) {
    ctx.fillStyle = mk.color;
    ctx.beginPath();
    ctx.arc(xNow, syE(valsNow[mk.kind]), 4.8, 0, Math.PI*2);
    ctx.fill();
  }

  // legend inside chart
  const legend = [
    {label:"운동에너지", color:"#2563eb"},
    {label:"마찰로 잃은 에너지", color:"#ef4444"},
    {label:"총에너지", color:"#059669"},
  ];
  let lx = m.left + 8;
  const ly = m.top + 12;
  ctx.font = "900 11px Pretendard, Arial";
  ctx.textAlign = "left";
  ctx.textBaseline = "middle";
  for (const item of legend) {
    ctx.strokeStyle = item.color;
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(lx, ly);
    ctx.lineTo(lx+22, ly);
    ctx.stroke();
    ctx.fillStyle = "#334155";
    ctx.fillText(item.label, lx+28, ly);
    lx += item.label.length * 12 + 64;
  }

  ctx.fillStyle = "#334155";
  ctx.font = "850 11px Pretendard, Arial";
  ctx.textAlign = "center";
  ctx.textBaseline = "bottom";
  ctx.fillText("시간 t (s)", m.left + pw/2, xAxisY + 46);
  ctx.save();
  ctx.translate(18, m.top + ph/2);
  ctx.rotate(-Math.PI/2);
  ctx.fillText("에너지 (J)", 0, 0);
  ctx.restore();
}

function drawTimeCharts(currentT) {
  drawTimeChart(speedCanvas, "speed", currentT);
  drawTimeChart(distanceCanvas, "distance", currentT);
  drawEnergyChart(currentT);
}

function setupMarks() {
  const totalVisual = DATA.approachDistance + DATA.totalStoppingDistance;
  const approachRatio = totalVisual <= 0 ? 0 : DATA.approachDistance / totalVisual;
  const reactionRatio = totalVisual <= 0 ? 0 : DATA.reactionDistance / totalVisual;
  const brakeRatio = totalVisual <= 0 ? 0 : DATA.brakingDistance / totalVisual;

  // 기준점은 자전거 그룹의 translate x가 아니라 앞바퀴 중심이다.
  const startX = FRONT_REF_START_X;
  const endX = FRONT_REF_END_X;
  const pathW = VISUAL_PATH_WIDTH;

  const dangerX = startX + pathW * approachRatio;
  const brakeX = dangerX + pathW * reactionRatio;

  setAttr("startMark", "x1", startX);
  setAttr("startMark", "x2", startX);
  setAttr("startText", "x", startX);

  setAttr("approachBar", "x", startX);
  setAttr("approachBar", "width", Math.max(2, pathW*approachRatio));

  setAttr("reactionBar", "x", dangerX);
  setAttr("reactionBar", "width", Math.max(2, pathW*reactionRatio));

  setAttr("brakeBar", "x", brakeX);
  setAttr("brakeBar", "width", Math.max(2, pathW*brakeRatio));

  setAttr("dangerMark", "x1", dangerX);
  setAttr("dangerMark", "x2", dangerX);
  setAttr("dangerText", "x", dangerX);

  setAttr("brakeMark", "x1", brakeX);
  setAttr("brakeMark", "x2", brakeX);
  setAttr("brakeText", "x", brakeX);

  setAttr("stopMark", "x1", endX);
  setAttr("stopMark", "x2", endX);
  setAttr("stopText", "x", endX);
}

function restart() {
  if (raf) cancelAnimationFrame(raf);
  startReal = null;
  setupMarks();
  drawTimeCharts(0);
  raf = requestAnimationFrame(animate);
}

function animate(ts) {
  if (startReal === null) startReal = ts;

  // 핵심: 물리 시간 = 실제 경과 시간 × 배속
  // 1배속이면 실제 1초가 물리 1초, 0.1배속이면 실제 1초가 물리 0.1초
  const realElapsed = (ts - startReal) / 1000;
  const t = realElapsed * DATA.playbackSpeed;

  const v = DATA.speedMs;
  const a = DATA.aEff;
  const totalPhysical = DATA.approachTime + DATA.reactionTime + DATA.brakingTime;
  const cappedT = Math.min(t, totalPhysical);

  let s = 0;
  let phase = "대기";
  let braking = false;
  let lockedWheel = false;
  let currentSpeed = v;

  if (DATA.speedKmh <= 0) {
    s = 0;
    currentSpeed = 0;
    phase = "정지 상태";
  } else if (cappedT < DATA.approachTime) {
    s = v * cappedT;
    phase = "등속 운동: 위험 발견 전";
    currentSpeed = v;
  } else if (cappedT < DATA.approachTime + DATA.reactionTime) {
    s = DATA.approachDistance + v * (cappedT - DATA.approachTime);
    phase = "반응 시간: 아직 제동하지 못함";
    currentSpeed = v;
  } else {
    const tb = cappedT - DATA.approachTime - DATA.reactionTime;
    s = DATA.approachDistance + DATA.reactionDistance + v * tb - 0.5 * a * tb * tb;
    s = Math.min(DATA.approachDistance + DATA.totalStoppingDistance, s);
    currentSpeed = Math.max(0, v - a * tb);
    phase = "제동 중: 바퀴 잠김 + 마찰 작용";
    braking = true;
    lockedWheel = true;
  }

  s = Math.max(0, Math.min(DATA.approachDistance + DATA.totalStoppingDistance, s));

  const totalVisual = Math.max(0.001, DATA.approachDistance + DATA.totalStoppingDistance);
  const fraction = s / totalVisual;

  // 핵심 수정:
  // 화면상의 현재 위치는 자전거 몸통이나 그룹 기준점이 아니라 앞바퀴 중심으로 계산한다.
  // 따라서 정지 순간에는 앞바퀴 중심이 빨간 정지선에 정확히 맞는다.
  const frontWheelX = FRONT_REF_START_X + VISUAL_PATH_WIDTH * fraction;
  const bikeX = frontWheelX - FRONT_WHEEL_LOCAL_X;

  // 위아래 흔들림 없이 수평 이동
  setAttr("bike", "transform", `translate(${bikeX.toFixed(2)} ${ROAD_Y})`);

  // 제동 전에는 바퀴 회전, 제동 시작 후에는 바퀴 잠김 표현
  let wheelAngle = 0;
  if (!lockedWheel) {
    wheelAngle = s * 31;
  } else {
    wheelAngle = (DATA.approachDistance + DATA.reactionDistance) * 31;
  }
  setAttr("rearWheel", "transform", `rotate(${wheelAngle.toFixed(2)} -48 28)`);
  setAttr("frontWheel", "transform", `rotate(${wheelAngle.toFixed(2)} 62 28)`);

  const brakeStartS = DATA.approachDistance + DATA.reactionDistance;
  const brakeStartFrontX = FRONT_REF_START_X + VISUAL_PATH_WIDTH * (brakeStartS / totalVisual);
  const brakeStartBikeX = brakeStartFrontX - FRONT_WHEEL_LOCAL_X;

  if (braking && currentSpeed > 0.05) {
    const rearWheelX = bikeX + REAR_WHEEL_LOCAL_X;
    const rearWheelAtBrakeStartX = brakeStartBikeX + REAR_WHEEL_LOCAL_X;
    const skidLen = Math.max(10, rearWheelX - rearWheelAtBrakeStartX);

    setAttr("skidLine", "x1", Math.max(rearWheelAtBrakeStartX, rearWheelX - skidLen));
    setAttr("skidLine", "y1", WHEEL_Y + 28);
    setAttr("skidLine", "x2", rearWheelX + 4);
    setAttr("skidLine", "y2", WHEEL_Y + 28);
    setAttr("skidLine", "opacity", 0.55);

    const pulse = (Math.sin(realElapsed * 12) + 1) / 2;

    // 바퀴가 잠기며 미끄러질 때, 뒤·앞바퀴 주변에 연기가 퍼지는 것처럼 강조한다.
    const rearX = bikeX + REAR_WHEEL_LOCAL_X;
    const frontX = bikeX + FRONT_WHEEL_LOCAL_X;
    const smokeY = WHEEL_Y + 16;
    const smokes = [
      ["smoke1", rearX - 4 - pulse*12, smokeY - 14, 22 + pulse*10, .96],
      ["smoke2", rearX - 30 - pulse*18, smokeY - 29, 30 + pulse*13, .92],
      ["smoke3", rearX - 58 - pulse*25, smokeY - 8, 24 + pulse*11, .88],
      ["smoke4", rearX - 88 - pulse*32, smokeY - 34, 26 + pulse*12, .80],
      ["smoke5", frontX - 4 - pulse*10, smokeY - 12, 20 + pulse*9, .94],
      ["smoke6", frontX - 28 - pulse*16, smokeY - 27, 26 + pulse*11, .88],
      ["smoke7", rearX - 22 - pulse*20, smokeY + 10, 20 + pulse*9, .86],
      ["smoke8", frontX - 50 - pulse*22, smokeY + 6, 22 + pulse*10, .82],
    ];
    for (const [id, cx, cy, r, op] of smokes) {
      setAttr(id, "cx", cx);
      setAttr(id, "cy", cy);
      setAttr(id, "r", r);
      setAttr(id, "opacity", op);
      const smokeEl = document.getElementById(id);
      if (smokeEl) smokeEl.style.opacity = op;
    }
  } else {
    setAttr("skidLine", "opacity", 0);
    for (const id of ["smoke1","smoke2","smoke3","smoke4","smoke5","smoke6","smoke7","smoke8"]) {
      setAttr(id, "opacity", 0);
      const smokeEl = document.getElementById(id);
      if (smokeEl) smokeEl.style.opacity = 0;
    }
  }

  setText("phaseText", phase);
  setText("distanceText", `현재 이동 거리: ${fmt(s)} / 현재 속력: ${(currentSpeed*3.6).toFixed(1)} km/h`);
  setText("clockText", `물리 시간 ${cappedT.toFixed(2)}초 / 실제 재생 시간 ${realElapsed.toFixed(2)}초 / ${DATA.playbackSpeed.toFixed(1)}배속`);
  drawTimeCharts(cappedT);

  if (t < totalPhysical) {
    raf = requestAnimationFrame(animate);
  } else {
    setText("phaseText", "정지 완료");
    setText("distanceText", `위험 발견 후 총 정지거리: ${fmt(DATA.totalStoppingDistance)}`);
    setText("clockText", `총 물리 시간 ${totalPhysical.toFixed(2)}초 / 실제 재생 시간 ${(totalPhysical / DATA.playbackSpeed).toFixed(2)}초`);
    drawTimeCharts(totalPhysical);
    setAttr("skidLine", "opacity", 0.35);
    for (const id of ["smoke1","smoke2","smoke3","smoke4","smoke5","smoke6","smoke7","smoke8"]) {
      setAttr(id, "opacity", 0);
      const smokeEl = document.getElementById(id);
      if (smokeEl) smokeEl.style.opacity = 0;
    }
  }
}

window.addEventListener("resize", () => drawTimeCharts(0));
setupMarks();
restart();
</script>
</body>
</html>
"""
    return template.replace("__DATA__", data_json)


def show_simulation(data: dict):
    components.html(build_simulation_html(data), height=1780, scrolling=False)


# ------------------------------------------------------------
# 비교군 1 값을 자동 반영한 Web VPython 코드 제공
# ------------------------------------------------------------
def build_vpython_student_code(
    speed_kmh: float,
    speed_ms: float,
    reaction_time: float,
    mass_kg: float,
    mu_value: float,
    road_name: str,
) -> str:
    """학생이 Web VPython에 바로 붙여넣어 실행할 수 있는 코드."""
    v0 = max(0.0, float(speed_ms))
    return f"""Web VPython 3.2

# ==========================================
# 1. 시뮬레이션 기본 변수
#    아래 값은 Streamlit 앱의 비교군 1 설정값이 자동 반영된 것입니다.
# ==========================================
speed_kmh = {float(speed_kmh):.2f}      # 참고용: 앱에서 설정한 초기 속력 (km/h)
v0 = {v0:.4f}             # 초기 속력 (m/s)
t_reaction = {float(reaction_time):.4f} # 반응 시간 (초)
g = 9.8                  # 중력가속도 (m/s^2)
m = {float(mass_kg):.2f}                 # 자전거+탑승자 질량 (kg)
mu = {float(mu_value):.4f}               # 마찰계수: {road_name}

# Web VPython 화면에서 출발선~위험선을 보기 좋게 벌려 놓기 위한 거리입니다.
# 정지거리의 핵심 계산에는 v0, t_reaction, mu가 반영됩니다.
run_up_distance = 80.0
running = False

# ==========================================
# 2. 배경 및 노면(바닥) 설정
# ==========================================
scene.width = 800
scene.height = 400
scene.background = color.cyan

road = box(
    pos=vector(200, -0.1, 0),
    size=vector(500, 0.2, 40),
    color=color.gray(0.6),
    texture=textures.rough
)

start_line = box(
    pos=vector(0, 0, 0),
    size=vector(0.5, 1.0, 30),
    color=color.white
)

danger_line = box(
    pos=vector(run_up_distance, 0, 0),
    size=vector(0.5, 1.0, 30),
    color=color.green
)

brake_line = box(
    pos=vector(run_up_distance + v0 * t_reaction, 0, 0),
    size=vector(0.5, 1.0, 30),
    color=color.yellow
)

# ==========================================
# 3. 자전거 조립
# ==========================================
bike_scale = 15.0

def make_wheel():
    w = ring(
        axis=vector(0, 0, 1),
        radius=0.4 * bike_scale,
        thickness=0.04 * bike_scale,
        color=color.black
    )
    spoke1 = cylinder(
        axis=vector(0.8 * bike_scale, 0, 0),
        pos=vector(-0.4 * bike_scale, 0, 0),
        radius=0.015 * bike_scale,
        color=color.white
    )
    spoke2 = cylinder(
        axis=vector(0, 0.8 * bike_scale, 0),
        pos=vector(0, -0.4 * bike_scale, 0),
        radius=0.015 * bike_scale,
        color=color.white
    )
    return compound([w, spoke1, spoke2])

wheel_rear = make_wheel()
wheel_front = make_wheel()

n1 = vector(-0.6 * bike_scale, 0.4 * bike_scale, 0)
n2 = vector(0, 0.4 * bike_scale, 0)
n3 = vector(-0.2 * bike_scale, 1.0 * bike_scale, 0)
n4 = vector(0.4 * bike_scale, 1.1 * bike_scale, 0)
n5 = vector(0.6 * bike_scale, 0.4 * bike_scale, 0)

parts = []
frame_r = 0.03 * bike_scale

parts.append(cylinder(pos=n1, axis=n2-n1, radius=frame_r, color=color.red))
parts.append(cylinder(pos=n2, axis=n3-n2, radius=frame_r, color=color.red))
parts.append(cylinder(pos=n3, axis=n1-n3, radius=frame_r, color=color.red))
parts.append(cylinder(pos=n3, axis=n4-n3, radius=frame_r, color=color.red))
parts.append(cylinder(pos=n2, axis=n4-n2, radius=frame_r, color=color.red))
parts.append(cylinder(pos=n4, axis=n5-n4, radius=frame_r, color=color.red))

# 안장
parts.append(
    box(
        pos=n3 + vector(0, 0.05 * bike_scale, 0),
        size=vector(0.3 * bike_scale, 0.1 * bike_scale, 0.15 * bike_scale),
        color=color.black
    )
)

# 핸들바
parts.append(
    cylinder(
        pos=n4 + vector(0, 0, -0.3 * bike_scale),
        axis=vector(0, 0, 0.6 * bike_scale),
        radius=frame_r,
        color=color.black
    )
)

# 전조등 느낌의 표시
parts.append(
    sphere(
        pos=n4 + vector(0.1 * bike_scale, 0, 0),
        radius=0.08 * bike_scale,
        color=color.yellow,
        emissive=True
    )
)

bike_frame = compound(parts)

def update_bike_pos(x):
    bike_frame.pos.x = x
    wheel_rear.pos = n1 + vector(x, 0, 0)
    wheel_front.pos = n5 + vector(x, 0, 0)

update_bike_pos(0)

max_distance = run_up_distance + (v0 * t_reaction) + (v0**2) / (2 * mu * g) if mu > 0 else run_up_distance
scene.center = vector(max_distance / 2, 0.5 * bike_scale, 0)

# ==========================================
# 4. UI
# ==========================================
def toggle_run(b):
    global running
    running = True

scene.append_to_caption('\\n')
button(text='▶ 시뮬레이션 시작 / 다시하기', bind=toggle_run, background=color.orange)
scene.append_to_caption('\\n\\n')

# ==========================================
# 5. 그래프 설정
# ==========================================
position_ymax = max_distance * 1.4
initial_KE = 0.5 * m * (v0**2)
energy_ymax = max(1, initial_KE * 1.4)

g1 = graph(
    title="<b>Position-Time Graph</b> (검은선:주행 / 파란선:반응 / 빨간선:제동)",
    xtitle="Time (s)",
    ytitle="Position (m)",
    width=800,
    height=600,
    ymin=0,
    ymax=position_ymax
)

g2 = graph(
    title="<b>Energy Conservation</b>",
    xtitle="Time (s)",
    ytitle="Energy (J)",
    width=800,
    height=300,
    ymin=0,
    ymax=energy_ymax
)

pos_curve = gcurve(graph=g1, color=color.black, width=2)
ke_curve = gcurve(graph=g2, color=color.orange, label="Kinetic Energy")
work_curve = gcurve(graph=g2, color=color.red, label="Friction Work")
total_e_curve = gcurve(graph=g2, color=color.green, label="Total Energy")

# ==========================================
# 6. 메인 애니메이션 루프
# ==========================================
while True:
    rate(60)

    if running:
        current_v = v0
        current_x = 0
        t = 0
        dt = 0.01
        work_friction = 0
        update_bike_pos(current_x)

        t_danger = run_up_distance / v0 if v0 > 0 else 0
        t_brake = t_danger + t_reaction

        brake_line.pos.x = run_up_distance + v0 * t_reaction

        pos_curve.delete()
        ke_curve.delete()
        work_curve.delete()
        total_e_curve.delete()

        pos_curve = gcurve(graph=g1, color=color.black, width=2)
        ke_curve = gcurve(graph=g2, color=color.orange, label="Kinetic Energy")
        work_curve = gcurve(graph=g2, color=color.red, label="Friction Work")
        total_e_curve = gcurve(graph=g2, color=color.green, label="Total Energy")

        while current_v > 0 and running:
            rate(400)

            # [0구간] 출발선 ~ 초록색 위험선: 등속 운동
            if t < t_danger:
                a = 0
                pos_curve.color = color.black

            # [1구간] 위험 감지 ~ 노란색 브레이크선: 반응 시간 동안 등속 운동
            elif t < t_brake:
                a = 0
                pos_curve.color = color.blue

            # [2구간] 브레이크 이후: 마찰력에 의한 감속 운동
            else:
                a = -mu * g
                pos_curve.color = color.red

                distance_moved = current_v * dt
                work_friction += (mu * m * g) * distance_moved

            current_v += a * dt
            if current_v < 0:
                current_v = 0

            current_x += current_v * dt
            update_bike_pos(current_x)

            current_radius = 0.4 * bike_scale
            d_theta = (current_v / current_radius) * dt if current_radius > 0 else 0
            wheel_front.rotate(angle=-d_theta, axis=vector(0, 0, 1))
            wheel_rear.rotate(angle=-d_theta, axis=vector(0, 0, 1))

            KE = 0.5 * m * (current_v**2)
            pos_curve.plot(t, current_x)
            ke_curve.plot(t, KE)
            work_curve.plot(t, work_friction)
            total_e_curve.plot(t, KE + work_friction)

            t += dt

        running = False
"""


def build_copyable_code_html(code_text: str) -> str:
    code_json = json.dumps(code_text, ensure_ascii=False)
    return f"""
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: transparent;
    font-family: Pretendard, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    color: #0f172a;
  }}
  .wrap {{
    width: 100%;
    border: 1px solid #dbe3ee;
    border-radius: 20px;
    background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
    overflow: hidden;
  }}
  .top {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    padding: 14px 16px;
    border-bottom: 1px solid #e2e8f0;
    background: #f8fafc;
  }}
  .title {{
    font-size: 18px;
    font-weight: 950;
    letter-spacing: -0.035em;
  }}
  .sub {{
    color: #64748b;
    font-size: 12px;
    font-weight: 750;
    margin-top: 3px;
  }}
  button {{
    border: 0;
    border-radius: 999px;
    background: #111827;
    color: white;
    padding: 10px 15px;
    font-size: 13px;
    font-weight: 900;
    cursor: pointer;
    box-shadow: 0 8px 18px rgba(15, 23, 42, .16);
    white-space: nowrap;
  }}
  button:active {{ transform: translateY(1px); }}
  textarea {{
    width: 100%;
    height: 640px;
    display: block;
    border: 0;
    outline: none;
    resize: vertical;
    padding: 16px;
    background: #0f172a;
    color: #e5e7eb;
    font-family: "D2Coding", "Consolas", "Menlo", monospace;
    font-size: 13px;
    line-height: 1.55;
    tab-size: 4;
  }}
  .msg {{
    padding: 9px 16px 12px;
    color: #475569;
    font-size: 12px;
    font-weight: 760;
    background: white;
    border-top: 1px solid #e2e8f0;
  }}
  .ok {{
    color: #16a34a;
    font-weight: 950;
  }}
</style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <div>
      <div class="title">Web VPython 코드</div>
      <div class="sub">비교군 1의 속도, 반응 시간, 질량, 노면 마찰계수가 자동 반영됩니다.</div>
    </div>
    <button onclick="copyCode()">코드 복사</button>
  </div>
  <textarea id="codeBox" spellcheck="false"></textarea>
  <div class="msg" id="msg">복사한 코드를 Web VPython 편집기에 붙여넣고 실행하면 됩니다.</div>
</div>
<script>
const CODE = {code_json};
const box = document.getElementById("codeBox");
const msg = document.getElementById("msg");
box.value = CODE;

function fallbackCopy() {{
  box.focus();
  box.select();
  document.execCommand("copy");
}}

async function copyCode() {{
  try {{
    await navigator.clipboard.writeText(CODE);
  }} catch (e) {{
    fallbackCopy();
  }}
  msg.innerHTML = "<span class='ok'>코드를 복사했습니다.</span> Web VPython 편집기에 붙여넣어 실행하세요.";
}}
</script>
</body>
</html>
"""


def show_copyable_code(code_text: str):
    components.html(build_copyable_code_html(code_text), height=760, scrolling=False)


# ------------------------------------------------------------
# 전체 페이지 스타일
# ------------------------------------------------------------
st.markdown(
    """
<style>
.block-container {
    padding-top: 1.4rem;
    padding-bottom: 3.2rem;
}
.main-title {
    font-size: 2.35rem;
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
.section-title {
    font-size: 1.55rem;
    font-weight: 950;
    letter-spacing: -0.035em;
    margin-top: 2.2rem;
    margin-bottom: .6rem;
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
.formula-box {
    background: #111827;
    color: white;
    border-radius: 18px;
    padding: 1rem 1.15rem;
    font-size: 1.05rem;
    font-weight: 900;
    margin: .6rem 0 1rem;
}
.small-caption {
    color: #64748b;
    font-size: .85rem;
    font-weight: 650;
}
hr {
    margin-top: 2rem;
    margin-bottom: 2rem;
}
</style>
""",
    unsafe_allow_html=True,
)


# ------------------------------------------------------------
# 화면 상단: 제목 + 메인 화면 입력 패널
# ------------------------------------------------------------
st.markdown("<div class='main-title'>🚲 픽시 자전거 정지거리와 이차함수</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='main-subtitle'>속도, 반응 시간, 노면 상태가 정지거리 함수 S(x)=Ax²+Bx+0의 계수를 어떻게 바꾸는지 확인합니다.</div>",
    unsafe_allow_html=True,
)

st.markdown("<div class='section-title'>⚙️ 조건 설정</div>", unsafe_allow_html=True)
st.markdown(
    """
<div class='info-box'>
사이드바는 페이지 이동 영역으로 비워두고, 비교군 설정과 시뮬레이션 배속은 메인 화면 안쪽에서 조절합니다.
비교군 1은 자전거 시뮬레이션의 기준값이며, 비교군 2·3은 이차함수 그래프에 함께 표시됩니다.
</div>
""",
    unsafe_allow_html=True,
)

with st.expander("비교군 및 시뮬레이션 설정 열기 / 닫기", expanded=True):
    group_col1, group_col2, group_col3 = st.columns(3)

    with group_col1:
        st.markdown("### 비교군 1: 시뮬레이션 기준")
        bike_mass = st.slider(
            "질량(kg)",
            min_value=40.0,
            max_value=100.0,
            value=65.0,
            step=1.0,
            key="mass1_main",
            help="현실감을 위해 사람+자전거 전체 질량 범위로 두었습니다. 단순 마찰 모델에서는 정지거리 계산식에서 질량이 약분됩니다.",
        )
        speed_kmh = st.slider(
            "초기 속도 x (km/h)",
            min_value=0,
            max_value=60,
            value=30,
            step=1,
            key="speed1_main",
        )
        reaction_time = st.slider(
            "반응 시간(초)",
            min_value=0.20,
            max_value=2.50,
            value=1.00,
            step=0.01,
            format="%.2f",
            key="reaction1_main",
        )
        road_label = st.selectbox(
            "노면 상태",
            list(ROAD_OPTIONS.keys()),
            index=0,
            key="road1_main",
        )
        mu = ROAD_OPTIONS[road_label]["mu"]
        playback_speed = st.slider(
            "시뮬레이션 배속",
            min_value=0.1,
            max_value=1.0,
            value=1.0,
            step=0.1,
            key="playback_speed_main",
            help="1.0배속이면 물리 시간 1초가 실제 화면에서도 1초입니다. 0.1배속이면 10배 느리게 관찰합니다.",
        )

    with group_col2:
        st.markdown("### 비교군 2")
        use_group2 = st.checkbox("비교군 2 표시", value=True, key="use_group2_main")
        mass2 = st.slider(
            "질량(kg)",
            40.0,
            100.0,
            65.0,
            1.0,
            key="mass2",
            disabled=not use_group2,
        )
        speed2 = st.slider(
            "초기 속도(km/h)",
            0,
            60,
            40,
            1,
            key="speed2",
            disabled=not use_group2,
        )
        reaction2 = st.slider(
            "반응 시간(초)",
            0.20,
            2.50,
            1.00,
            0.01,
            format="%.2f",
            key="reaction2",
            disabled=not use_group2,
        )
        road2 = st.selectbox(
            "노면 상태",
            list(ROAD_OPTIONS.keys()),
            index=1,
            key="road2",
            disabled=not use_group2,
        )
        if not use_group2:
            mass2, speed2, reaction2, road2 = 65.0, 40, 1.00, "젖은 아스팔트"

    with group_col3:
        st.markdown("### 비교군 3")
        use_group3 = st.checkbox("비교군 3 표시", value=True, key="use_group3_main")
        mass3 = st.slider(
            "질량(kg)",
            40.0,
            100.0,
            65.0,
            1.0,
            key="mass3",
            disabled=not use_group3,
        )
        speed3 = st.slider(
            "초기 속도(km/h)",
            0,
            60,
            50,
            1,
            key="speed3",
            disabled=not use_group3,
        )
        reaction3 = st.slider(
            "반응 시간(초)",
            0.20,
            2.50,
            1.20,
            0.01,
            format="%.2f",
            key="reaction3",
            disabled=not use_group3,
        )
        road3 = st.selectbox(
            "노면 상태",
            list(ROAD_OPTIONS.keys()),
            index=2,
            key="road3",
            disabled=not use_group3,
        )
        if not use_group3:
            mass3, speed3, reaction3, road3 = 65.0, 50, 1.20, "모래·낙엽길"

# ------------------------------------------------------------
# 현재 조건 계산
# ------------------------------------------------------------
result = calc_result(speed_kmh, reaction_time, mu)
risk, risk_text = risk_label(result["total_stopping_distance"])

# 그래프 곡선 구성: 비교군 1, 2, 3
curves = [
    make_curve(
        name=f"비교군 1: {bike_mass:.0f}kg, {speed_kmh}km/h, 반응 {reaction_time:.2f}s, {road_label}",
        mass=bike_mass,
        speed_kmh=speed_kmh,
        reaction_time=reaction_time,
        mu=mu,
        color=CURVE_COLORS[0],
        group="비교군 1",
    )
]

if use_group2:
    curves.append(
        make_curve(
            name=f"비교군 2: {mass2:.0f}kg, {speed2}km/h, 반응 {reaction2:.2f}s, {road2}",
            mass=mass2,
            speed_kmh=speed2,
            reaction_time=reaction2,
            mu=ROAD_OPTIONS[road2]["mu"],
            color=CURVE_COLORS[1],
            group="비교군 2",
        )
    )

if use_group3:
    curves.append(
        make_curve(
            name=f"비교군 3: {mass3:.0f}kg, {speed3}km/h, 반응 {reaction3:.2f}s, {road3}",
            mass=mass3,
            speed_kmh=speed3,
            reaction_time=reaction3,
            mu=ROAD_OPTIONS[road3]["mu"],
            color=CURVE_COLORS[2],
            group="비교군 3",
        )
    )

curves = dedupe_curves(curves)

# ------------------------------------------------------------
# 화면 출력
# ------------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("반응거리", fmt_m(result["reaction_distance"]), help="위험을 발견했지만 아직 제동하지 못한 동안 이동한 거리")
c2.metric("제동거리", fmt_m(result["braking_distance"]), help="제동을 시작한 뒤 완전히 멈출 때까지 이동한 거리")
c3.metric("총 정지거리", fmt_m(result["total_stopping_distance"]), help="반응거리 + 제동거리")
c4.metric("유효 감속도", f"{result['a_eff']:.2f} m/s²", help="μ × g")

c5, c6, c7, c8 = st.columns(4)
c5.metric("반응 시간", f"{reaction_time:.2f} s")
c6.metric("제동 시간", fmt_time(result["braking_time"]))
c7.metric("총 물리 시간", fmt_time(result["physical_total_time"]), help="등속 접근 구간 + 반응 시간 + 제동 시간")
c8.metric("재생 예상 시간", fmt_time(result["physical_total_time"] / playback_speed if playback_speed > 0 else math.inf), help="총 물리 시간 ÷ 배속")

st.markdown(
    f"""
<div class='{"warn-box" if risk in ["위험", "매우 위험"] else "info-box"}'>
<b>현재 위험도: {html.escape(risk)}</b><br>
{html.escape(risk_text)}
</div>
""",
    unsafe_allow_html=True,
)

st.markdown("<div class='section-title'>1. 이차함수 그래프</div>", unsafe_allow_html=True)
st.markdown(
    """
<div class='info-box'>
그래프 위에서 <b>드래그</b>하면 화면을 이동할 수 있고, <b>마우스 휠</b>로 확대·축소할 수 있습니다.
비교군 1, 2, 3의 질량, 초기 속도, 반응 시간, 노면 상태를 설정하고 그래프를 한 화면에 중첩해 비교할 수 있습니다.
</div>
""",
    unsafe_allow_html=True,
)

graph_data = {
    "curves": curves,
    "selectedSpeed": float(speed_kmh),
}
show_interactive_graph(graph_data)

A = result["A"]
B = result["B"]
st.markdown(
    f"""
<div class='formula-box'>
현재 조건의 함수: S(x) = {A:.5f}x² + {B:.3f}x + 0<br>
완전제곱식: S(x) = {A:.5f}(x + {B/(2*A):.2f})² - {B*B/(4*A):.2f}
</div>
""",
    unsafe_allow_html=True,
)

st.markdown("<div class='section-title'>2. 자전거 시뮬레이션</div>", unsafe_allow_html=True)
st.markdown(
    f"""
<div class='info-box'>
시뮬레이션은 <b>등속 운동 → 반응 거리 → 제동 거리</b> 순서로 진행됩니다.
현재 배속은 <b>{playback_speed:.1f}배속</b>입니다.
1.0배속에서는 물리 시간 1초가 실제 화면에서도 1초로 진행되고, 0.1배속에서는 10배 느리게 관찰됩니다.
제동 구간에서는 바퀴가 잠긴 것처럼 회전이 멈추고, 연기와 미끄럼 자국이 나타납니다.
</div>
""",
    unsafe_allow_html=True,
)

sim_data = {
    "speedKmh": float(speed_kmh),
    "speedMs": float(result["speed_ms"]),
    "massKg": float(bike_mass),
    "aEff": float(result["a_eff"]),
    "approachDistance": float(APPROACH_DISTANCE),
    "reactionDistance": float(result["reaction_distance"]),
    "brakingDistance": float(result["braking_distance"]),
    "totalStoppingDistance": float(result["total_stopping_distance"]),
    "approachTime": float(result["approach_time"]),
    "reactionTime": float(result["reaction_time"]),
    "brakingTime": float(result["braking_time"]),
    "playbackSpeed": float(playback_speed),
}
show_simulation(sim_data)

st.markdown("<div class='section-title'>3. 이론 정리</div>", unsafe_allow_html=True)

st.markdown("### 3-1. 수학: 이차함수와 완전제곱식")
st.markdown(
    """
총 정지거리 함수는 초기 속도 \(x\)에 대한 이차함수입니다.  
여기서 \(x\)는 km/h 단위의 초기 속도, \(S(x)\)는 m 단위의 총 정지거리입니다.
"""
)
st.latex(r"S(x)=Ax^2+Bx+0")
st.markdown(
    """
반응 시간 동안 이동한 거리는 속도에 비례하므로 일차항 \(Bx\)가 됩니다.  
제동거리는 속도의 제곱에 비례하므로 이차항 \(Ax^2\)가 됩니다.
"""
)

st.markdown("#### 완전제곱식으로 바꾸기")
st.latex(r"S(x)=Ax^2+Bx")
st.latex(r"S(x)=A\left(x^2+\frac{B}{A}x\right)")
st.latex(r"S(x)=A\left[\left(x+\frac{B}{2A}\right)^2-\left(\frac{B}{2A}\right)^2\right]")
st.latex(r"S(x)=A\left(x+\frac{B}{2A}\right)^2-\frac{B^2}{4A}")

st.markdown(
    f"""
<div class='info-box'>
현재 조건에서는 <b>A={A:.5f}</b>, <b>B={B:.3f}</b>입니다.<br>
꼭짓점은 대략 <b>({result["vertex_x"]:.2f}, {result["vertex_y"]:.2f})</b>입니다.
이 꼭짓점은 음수 속도 영역에 있으므로 실제 주행에서 직접 나타나는 지점은 아니지만,
그래프가 기본 포물선 \(y=Ax^2\)을 평행이동한 형태임을 보여줍니다.
</div>
""",
    unsafe_allow_html=True,
)

st.markdown("### 3-2. 과학(물리): 운동에너지, 마찰력, 일")
st.markdown(
    """
달리는 자전거는 운동에너지를 가지고 있습니다. 속도가 커질수록 운동에너지는 \(v^2\)에 비례하여 커집니다.
"""
)
st.latex(r"E_k=\frac{1}{2}mv^2")

st.markdown(
    """
제동할 때 타이어와 노면 사이의 마찰력이 자전거의 운동을 방해합니다.
이 마찰력이 이동 방향과 반대 방향으로 작용하면서 일을 하고, 그 결과 운동에너지가 줄어듭니다.
"""
)
st.latex(r"W=Fd")
st.latex(r"F_{\mathrm{마찰}}\approx \mu mg")

st.markdown(
    """
제동 과정에서 운동에너지는 사라지는 것이 아니라 열에너지, 소리, 타이어와 노면의 변형 등으로 전환됩니다.
시뮬레이션에서 연기와 미끄럼 자국은 이 에너지 전환을 눈에 보이게 표현한 것입니다.
"""
)
st.latex(r"\frac{1}{2}mv^2=\mu mg\cdot d")

st.markdown(
    """
위 식에서 질량 \(m\)은 양쪽에 모두 들어 있으므로 약분됩니다.
그래서 이 단순 모델에서는 자전거+탑승자 질량을 바꾸어도 정지거리가 직접 변하지 않습니다.
"""
)
st.latex(r"d=\frac{v^2}{2\mu g}")

st.markdown("### 3-3. 정지거리 식 만들기")
st.markdown("반응거리는 다음과 같습니다.")
st.latex(r"\text{반응거리}=vt_r")

st.markdown("제동거리는 다음과 같습니다.")
st.latex(r"\text{제동거리}=\frac{v^2}{2\mu g}")

st.markdown("따라서 총 정지거리는 다음과 같습니다.")
st.latex(r"S(v)=vt_r+\frac{v^2}{2\mu g}")

st.markdown("앱에서는 속도 단위를 km/h로 사용하므로 \(v=x/3.6\)을 대입합니다.")
st.latex(r"v=\frac{x}{3.6}")
st.latex(r"S(x)=\frac{1}{25.92\mu g}x^2+\frac{t_r}{3.6}x+0")

st.markdown(
    """
<div class='info-box'>
정리하면, 픽시 자전거의 위험성은 속도가 조금 증가할 때 정지거리가 단순히 조금 늘어나는 정도가 아니라,
제동거리 항 때문에 <b>제곱에 가깝게 빠르게 증가한다</b>는 데 있습니다.
특히 노면 마찰계수 \(\mu\)가 작으면 이차항의 계수 \(A\)가 커져 그래프가 더 가파르게 올라갑니다.
</div>
""",
    unsafe_allow_html=True,
)

st.markdown("---")

st.markdown("<div class='section-title'>4. Web VPython 실습 코드</div>", unsafe_allow_html=True)

st.markdown(
    """
<div class='info-box'>
아래 코드는 <b>비교군 1</b>의 현재 설정값을 자동으로 넣어 만든 Web VPython 코드입니다.
코드 복사 버튼을 누른 뒤 Web VPython 편집기에 붙여넣으면 학생들이 같은 조건의 시뮬레이션을 직접 실행해볼 수 있습니다.
</div>
""",
    unsafe_allow_html=True,
)

vpython_code = build_vpython_student_code(
    speed_kmh=float(speed_kmh),
    speed_ms=float(result["speed_ms"]),
    reaction_time=float(reaction_time),
    mass_kg=float(bike_mass),
    mu_value=float(mu),
    road_name=str(road_label),
)
show_copyable_code(vpython_code)

st.markdown("---")
st.markdown(
    f"""
<div class='small-caption'>
모델 가정: 공기저항 무시, 평지, 반응 시간 동안 등속 운동, 제동 중 일정한 감속도, 노면 상태를 하나의 마찰계수 μ로 단순화.
자전거+탑승자 질량 {bike_mass:.0f} kg은 현실감 있는 탐구 변수로 표시하지만, 이상적인 마찰 모델의 정지거리 계산에는 직접 반영하지 않음.
</div>
""",
    unsafe_allow_html=True,
)
