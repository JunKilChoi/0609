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
APPROACH_DISTANCE = 8.0  # 위험 발견 전 짧은 등속 주행 구간. 정지거리 함수 S(v)에는 포함하지 않음.

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
    """S(v)=Av^2+Bv+0. v 단위는 km/h, S 단위는 m."""
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


def inverse_max_speed_kmh(available_distance: float, reaction_time: float, mu: float) -> dict:
    """주어진 거리 안에서 멈출 수 있는 최대 초기 속력을 역산한다.

    available_distance: 위험 발견 지점부터 보행자 또는 장애물까지의 거리(m)
    reaction_time: 반응 시간(s)
    mu: 노면 마찰계수
    """
    if available_distance <= 0 or reaction_time < 0 or mu <= 0:
        return {
            "speed_ms": 0.0,
            "speed_kmh": 0.0,
            "reaction_distance": 0.0,
            "braking_distance": 0.0,
            "total_distance": 0.0,
            "a_eff": max(0.0, mu * G),
        }

    a_eff = mu * G

    # S = v t_r + v^2/(2 μ g) = d 를 v에 대해 푼다.
    # v^2/(2a) + t v - d = 0, a = μg
    speed_ms = -a_eff * reaction_time + math.sqrt((a_eff * reaction_time) ** 2 + 2 * a_eff * available_distance)
    speed_kmh = speed_ms * 3.6
    reaction_distance = speed_ms * reaction_time
    braking_distance = (speed_ms * speed_ms) / (2 * a_eff)
    total_distance = reaction_distance + braking_distance

    return {
        "speed_ms": speed_ms,
        "speed_kmh": speed_kmh,
        "reaction_distance": reaction_distance,
        "braking_distance": braking_distance,
        "total_distance": total_distance,
        "a_eff": a_eff,
    }


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
  ctx.fillText("총 정지거리 S(v) (m)", 0, 0);
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
  ctx.fillText("S(v)=Av²+Bv+0", margins.left, 12);

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
  .sim-scroll {
    width: 100%;
    overflow-x: auto;
    overflow-y: hidden;
    border-radius: 18px;
    background: #eaf6ff;
    padding-bottom: 6px;
  }
  #sim {
    width: 1080px;
    max-width: none;
    height: 430px;
    display: block;
  }
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
      <div class="sub">1 m 눈금을 기준으로 실제 거리 비율을 유지합니다. 경로가 길어지면 가로 스크롤로 이어서 볼 수 있습니다.</div>
    </div>
    <button onclick="restart()">다시 재생</button>
  </div>
  <div class="panel">
    <div id="simScroll" class="sim-scroll">
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

      <rect id="skyRect" x="0" y="0" width="1080" height="430" fill="url(#sky)"/>
      <rect id="roadRect" x="56" y="238" width="968" height="86" rx="28" fill="url(#roadGrad)"/>
      <line id="centerLine" x1="78" y1="281" x2="1002" y2="281" class="road-line"/>

      <rect id="approachBar" x="78" y="338" width="0" height="16" rx="8" fill="rgba(56,189,248,.78)"/>
      <rect id="reactionBar" x="78" y="360" width="0" height="16" rx="8" fill="rgba(245,158,11,.78)"/>
      <rect id="brakeBar" x="78" y="382" width="0" height="16" rx="8" fill="rgba(239,68,68,.78)"/>

      <g id="distanceTickGroup"></g>

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
    </div>

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

// 실제 거리 스케일
// 이 값이 클수록 1 m가 화면에서 더 길게 보인다.
// 전체 경로가 길어지면 SVG가 넓어지고, 아래 가로 스크롤로 확인한다.
const METER_PX = 50;

const ROAD_Y = 250;
const WHEEL_Y = ROAD_Y + 28;
const SVG_MIN_WIDTH = 1080;
const ROAD_LEFT = 56;
const ROAD_RIGHT_PAD = 56;

// 자전거 SVG 내부 좌표 기준
// 앞으로 이동한 거리의 기준점은 자전거 몸통 중심이 아니라 앞바퀴 중심이다.
const REAR_WHEEL_LOCAL_X = -48;
const FRONT_WHEEL_LOCAL_X = 62;

// 출발 순간 앞바퀴 중심의 화면 좌표.
// 위험 발견선은 DATA.approachDistance만큼 떨어진 위치에 고정된다.
const FRONT_REF_START_X = 140;
const X0 = FRONT_REF_START_X - FRONT_WHEEL_LOCAL_X;

// 전체 실제 경로: 출발 → 위험 발견 → 반응거리 → 제동거리
const TOTAL_ROUTE_METERS = Math.max(0.001, DATA.approachDistance + DATA.totalStoppingDistance);
const VISUAL_PATH_WIDTH = TOTAL_ROUTE_METERS * METER_PX;
const FRONT_REF_END_X = FRONT_REF_START_X + VISUAL_PATH_WIDTH;
const X1 = FRONT_REF_END_X;
const SVG_WIDTH = Math.max(SVG_MIN_WIDTH, FRONT_REF_END_X + 130);

const scrollBox = document.getElementById("simScroll");

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

function setupSvgSize() {
  const sim = document.getElementById("sim");
  if (sim) {
    sim.setAttribute("viewBox", `0 0 ${SVG_WIDTH} 430`);
    sim.style.width = `${SVG_WIDTH}px`;
  }

  setAttr("skyRect", "width", SVG_WIDTH);
  setAttr("roadRect", "x", ROAD_LEFT);
  setAttr("roadRect", "width", Math.max(0, SVG_WIDTH - ROAD_LEFT - ROAD_RIGHT_PAD));
  setAttr("centerLine", "x1", FRONT_REF_START_X);
  setAttr("centerLine", "x2", Math.max(FRONT_REF_END_X, SVG_WIDTH - 78));
}

function setupDistanceTicks() {
  const group = document.getElementById("distanceTickGroup");
  if (!group) return;
  group.innerHTML = "";

  const totalMeters = Math.ceil(TOTAL_ROUTE_METERS);
  for (let meter = 0; meter <= totalMeters; meter++) {
    const x = FRONT_REF_START_X + meter * METER_PX;
    const major = meter % 5 === 0;
    const y1 = major ? 404 : 412;
    const y2 = 426;

    const tick = document.createElementNS("http://www.w3.org/2000/svg", "line");
    tick.setAttribute("x1", x);
    tick.setAttribute("x2", x);
    tick.setAttribute("y1", y1);
    tick.setAttribute("y2", y2);
    tick.setAttribute("stroke", major ? "#eab308" : "#ffffff");
    tick.setAttribute("stroke-width", major ? "2.5" : "1.4");
    tick.setAttribute("opacity", major ? "1" : ".75");
    group.appendChild(tick);

    if (major) {
      const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
      label.setAttribute("x", x);
      label.setAttribute("y", 424);
      label.setAttribute("text-anchor", "middle");
      label.setAttribute("fill", "#facc15");
      label.setAttribute("font-size", "10");
      label.setAttribute("font-weight", "900");
      label.textContent = `${meter}m`;
      group.appendChild(label);
    }
  }
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
  setupSvgSize();
  setupDistanceTicks();

  // 기준점은 자전거 그룹의 translate x가 아니라 앞바퀴 중심이다.
  // 모든 선 위치는 실제 거리 m × METER_PX로 환산한다.
  const startX = FRONT_REF_START_X;
  const dangerX = startX + DATA.approachDistance * METER_PX;
  const brakeX = dangerX + DATA.reactionDistance * METER_PX;
  const stopX = dangerX + DATA.totalStoppingDistance * METER_PX;

  setAttr("startMark", "x1", startX);
  setAttr("startMark", "x2", startX);
  setAttr("startText", "x", startX);

  setAttr("approachBar", "x", startX);
  setAttr("approachBar", "width", Math.max(2, DATA.approachDistance * METER_PX));

  setAttr("reactionBar", "x", dangerX);
  setAttr("reactionBar", "width", Math.max(2, DATA.reactionDistance * METER_PX));

  setAttr("brakeBar", "x", brakeX);
  setAttr("brakeBar", "width", Math.max(2, DATA.brakingDistance * METER_PX));

  setAttr("dangerMark", "x1", dangerX);
  setAttr("dangerMark", "x2", dangerX);
  setAttr("dangerText", "x", dangerX);

  setAttr("brakeMark", "x1", brakeX);
  setAttr("brakeMark", "x2", brakeX);
  setAttr("brakeText", "x", brakeX);

  setAttr("stopMark", "x1", stopX);
  setAttr("stopMark", "x2", stopX);
  setAttr("stopText", "x", stopX);
}

function restart() {
  if (raf) cancelAnimationFrame(raf);
  startReal = null;
  setupMarks();
  if (scrollBox) scrollBox.scrollLeft = 0;
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

  // 실제 이동거리 s(m)를 고정 스케일로 환산한다.
  // 전체 길이에 맞춰 비율로 압축하지 않으므로, 제동 시작선과 정지선이 실제 거리만큼 오른쪽으로 밀려난다.
  const frontWheelX = FRONT_REF_START_X + s * METER_PX;
  const bikeX = frontWheelX - FRONT_WHEEL_LOCAL_X;

  // 위아래 흔들림 없이 수평 이동
  setAttr("bike", "transform", `translate(${bikeX.toFixed(2)} ${ROAD_Y})`);

  // 경로가 화면보다 길면 스크롤을 자연스럽게 따라가게 한다.
  if (scrollBox) {
    const targetScroll = Math.max(0, frontWheelX - scrollBox.clientWidth * 0.55);
    scrollBox.scrollLeft += (targetScroll - scrollBox.scrollLeft) * 0.10;
  }

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
  const brakeStartFrontX = FRONT_REF_START_X + brakeStartS * METER_PX;
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
    """학생이 Web VPython에 바로 붙여넣어 실행할 수 있는 코드.

    비교군 1의 현재 설정값을 최종 VPython 코드의 주요 변수에 자동 반영한다.
    """
    template = 'Web VPython 3.2\n\n# ==========================================\n# 1. 시뮬레이션 기본 변수\n# ==========================================\nspeed_kmh = 30\nv0 = speed_kmh / 3.6\n\nt_reaction = 0.4\ng = 9.8\nm = 60\nmu = 0.70\n\n# ==========================================\n# 실험 상황의 고정 위치\n# ==========================================\n# 조건을 바꾸어도 아래 두 위치는 바뀌지 않습니다.\n# 비교 실험에서는 보행자 위치와 위험 발견 위치가 고정되어야 의미가 있습니다.\ndanger_x = 5.0       # 위험 발견 위치: 출발선 기준 5 m\npedestrian_x = 10.0   # 보행자 위치: 출발선 기준 10 m\n\n# 기존 코드와의 호환을 위해 run_up_distance는 danger_x와 같은 값으로 둡니다.\nrun_up_distance = danger_x\n\nplay_speed = 1.0\n\nframe_rate = 60\n\nrunning = False\n\n# 충돌 모션 상태 변수\ncollision_happened = False\npedestrian_v = vector(0, 0, 0)\npedestrian_omega = 0\n\n# ==========================================\n# 2. 실제 길이 스케일 설정\n# ==========================================\n# 이 코드에서는 VPython의 거리 1칸을 실제 1 m로 해석합니다.\n# 자전거 전체 길이: 약 2 m\n# 도로 중앙선 한 칸 길이: 1 m\n\nbike_length = 2.0\nwheel_radius = 0.34\nwheelbase = bike_length - 2 * wheel_radius\n\n# 자전거 기준점 current_x는 자전거 몸체 기준점입니다.\n# 앞바퀴의 가장 앞부분을 위치 판단 기준으로 쓰기 위해 offset을 따로 둡니다.\nrear_wheel_center_offset = -wheelbase / 2\nfront_wheel_center_offset = wheelbase / 2\nfront_edge_offset = front_wheel_center_offset + wheel_radius\n\n# 처음에 앞바퀴 앞부분이 출발선 x=0에 오도록 배치합니다.\ninitial_bike_x = -front_edge_offset\n\n# 보행자, 자전거, 도로 크기도 실제 m 단위에 가깝게 설정합니다.\nroad_width = 5.0\nlane_mark_length = 1.0\nlane_mark_gap = 1.0\nlane_mark_width = 0.12\n\n# ==========================================\n# 3. 정지거리 및 보행자 위치 계산\n# ==========================================\nreaction_distance = v0 * t_reaction\nbraking_distance = (v0**2) / (2 * mu * g)\ndanger_to_stop_distance = reaction_distance + braking_distance\n\n# 앞바퀴 앞부분 기준 정지 예상 위치\n# 위험 발견 위치는 danger_x로 고정되고, 조건에 따라 정지 예상 위치만 달라집니다.\nmax_distance = danger_x + danger_to_stop_distance\n\n# 보행자는 위에서 설정한 pedestrian_x에 고정됩니다.\n# 화면에는 위험 발견 지점으로부터 보행자가 몇 m 앞에 있는지 표시합니다.\npedestrian_distance_from_danger = round(pedestrian_x - danger_x, 1)\n\nroad_length = max(60, max_distance + 15, pedestrian_x + 15)\n\n# ==========================================\n# 4. 배경 및 노면 설정\n# ==========================================\nscene.width = 900\nscene.height = 420\nscene.background = color.black\n\n# 실제 스케일에 맞추면 물체가 작아지므로 카메라를 더 좁게 잡아 속도감을 살립니다.\nscene.range = 7\n\nroad = box(\n    pos=vector(road_length / 2, -0.04, 0),\n    size=vector(road_length, 0.08, road_width),\n    color=color.gray(0.58),\n    texture=textures.rough\n)\n\n# 도로 중앙선: 실제 길이 1 m\nlane_marks = []\nx = -5\nwhile x < road_length + 5:\n    mark = box(\n        pos=vector(x, 0.02, 0),\n        size=vector(lane_mark_length, 0.035, lane_mark_width),\n        color=color.white\n    )\n    lane_marks.append(mark)\n    x += lane_mark_length + lane_mark_gap\n\n# ==========================================\n# 도로 옆 거리 눈금\n# ==========================================\n# 1 m마다 작은 눈금을 표시하고, 5 m마다 숫자를 표시합니다.\n# 위치 기준은 자전거 앞바퀴의 가장 앞부분입니다.\nruler_z = -road_width / 2 - 0.45\nruler_y = 0.045\n\nruler_base = cylinder(\n    pos=vector(0, ruler_y, ruler_z),\n    axis=vector(road_length, 0, 0),\n    radius=0.01,\n    color=color.white\n)\n\nruler_ticks = []\nruler_labels = []\n\nmeter = 0\nwhile meter <= int(road_length):\n    if meter % 5 == 0:\n        tick_len = 0.55\n        tick_radius = 0.018\n        tick_color = color.yellow\n    else:\n        tick_len = 0.28\n        tick_radius = 0.010\n        tick_color = color.white\n\n    tick = cylinder(\n        pos=vector(meter, ruler_y, ruler_z - tick_len / 2),\n        axis=vector(0, 0, tick_len),\n        radius=tick_radius,\n        color=tick_color\n    )\n    ruler_ticks.append(tick)\n\n    # 숫자는 너무 복잡하지 않게 5 m마다만 표시합니다.\n    if meter % 5 == 0:\n        ruler_labels.append(\n            label(\n                pos=vector(meter, 0.22, ruler_z - 0.78),\n                text=str(meter) + " m",\n                height=8,\n                box=False,\n                color=color.yellow\n            )\n        )\n\n    meter += 1\n\n# 기준선\nstart_line = box(\n    pos=vector(0, 0.05, 0),\n    size=vector(0.08, 0.20, road_width),\n    color=color.white\n)\n\ndanger_line = box(\n    pos=vector(danger_x, 0.05, 0),\n    size=vector(0.08, 0.20, road_width),\n    color=color.green\n)\n\nbrake_line = box(\n    pos=vector(danger_x + reaction_distance, 0.05, 0),\n    size=vector(0.08, 0.20, road_width),\n    color=color.yellow\n)\n\nstop_line = box(\n    pos=vector(max_distance, 0.05, 0),\n    size=vector(0.08, 0.20, road_width),\n    color=color.red\n)\n\nlabel(pos=vector(0, 1.7, 0), text="출발", height=11, box=False, color=color.white)\nlabel(pos=vector(danger_x, 1.7, 0), text="위험 발견", height=11, box=False, color=color.green)\nlabel(pos=vector(danger_x + reaction_distance, 1.7, 0), text="제동 시작", height=11, box=False, color=color.yellow)\nlabel(pos=vector(max_distance, 1.7, 0), text="정지 예상", height=11, box=False, color=color.red)\n\n# ==========================================\n# 5. 도로 위 보행자 조형물\n# ==========================================\ndef make_pedestrian():\n    person_parts = []\n\n    # 사람 키 약 1.7 m\n    foot_y = 0.0\n    hip_y = 0.85\n    shoulder_y = 1.35\n    head_y = 1.62\n\n    leg_r = 0.045\n    arm_r = 0.035\n    body_r = 0.11\n\n    skin = vector(1.0, 0.82, 0.65)\n\n    # 아래 도형들은 x=0을 기준으로 만든 뒤 compound 전체를 pedestrian_x로 옮깁니다.\n    # 이렇게 해야 충돌 후 보행자를 통째로 움직이고 회전시키기 쉽습니다.\n\n    # 다리\n    person_parts.append(\n        cylinder(\n            pos=vector(-0.08, foot_y, 0),\n            axis=vector(0.04, hip_y - foot_y, 0),\n            radius=leg_r,\n            color=color.blue\n        )\n    )\n    person_parts.append(\n        cylinder(\n            pos=vector(0.08, foot_y, 0),\n            axis=vector(-0.04, hip_y - foot_y, 0),\n            radius=leg_r,\n            color=color.blue\n        )\n    )\n\n    # 몸통\n    person_parts.append(\n        cylinder(\n            pos=vector(0, hip_y, 0),\n            axis=vector(0, shoulder_y - hip_y, 0),\n            radius=body_r,\n            color=color.orange\n        )\n    )\n\n    # 머리\n    person_parts.append(\n        sphere(\n            pos=vector(0, head_y, 0),\n            radius=0.14,\n            color=skin\n        )\n    )\n\n    # 팔\n    person_parts.append(\n        cylinder(\n            pos=vector(-0.08, shoulder_y - 0.03, 0),\n            axis=vector(-0.18, -0.38, 0),\n            radius=arm_r,\n            color=skin\n        )\n    )\n    person_parts.append(\n        cylinder(\n            pos=vector(0.08, shoulder_y - 0.03, 0),\n            axis=vector(0.18, -0.38, 0),\n            radius=arm_r,\n            color=skin\n        )\n    )\n\n    # 발\n    person_parts.append(\n        box(\n            pos=vector(-0.09, 0.02, 0),\n            size=vector(0.22, 0.04, 0.12),\n            color=color.black\n        )\n    )\n    person_parts.append(\n        box(\n            pos=vector(0.09, 0.02, 0),\n            size=vector(0.22, 0.04, 0.12),\n            color=color.black\n        )\n    )\n\n    # origin을 발끝 위치 y=0에 둡니다.\n    # compound의 기본 origin은 물체 중심 쪽으로 잡힐 수 있어서,\n    # 그대로 pos.y=0을 주면 사람이 도로에 박혀 보일 수 있습니다.\n    return compound(person_parts, origin=vector(0, 0, 0))\n\npedestrian = make_pedestrian()\n\n# 도로의 윗면은 road.pos.y + road.size.y/2 = 0 입니다.\n# 따라서 발끝 기준 origin을 y=0에 두면 발끝이 도로 표면에 정확히 닿습니다.\nroad_surface_y = road.pos.y + road.size.y / 2\npedestrian.pos = vector(pedestrian_x, road_surface_y, 0)\n\npedestrian_label = label(\n    pos=vector(pedestrian_x, 2.05, 0),\n    text="보행자\\n위험 발견 +" + str(pedestrian_distance_from_danger) + " m",\n    height=11,\n    box=False,\n    color=color.orange\n)\n\n# 위험 발견 지점에서 보행자까지의 실제 거리 표시선\ndistance_line = cylinder(\n    pos=vector(danger_x, 0.08, -2.0),\n    axis=vector(pedestrian_distance_from_danger, 0, 0),\n    radius=0.018,\n    color=color.magenta\n)\n\ndistance_label = label(\n    pos=vector(danger_x + pedestrian_distance_from_danger / 2, 0.45, -2.0),\n    text="위험 발견 후 " + str(pedestrian_distance_from_danger) + " m",\n    height=10,\n    box=True,\n    color=color.magenta\n)\n\n# 충돌 표시용\ncollision_label = label(\n    pos=vector(pedestrian_x, 2.55, 0),\n    text="",\n    height=14,\n    box=False,\n    color=color.red\n)\n\n# ==========================================\n# 6. 자전거 조립\n# ==========================================\n\ndef make_wheel():\n    tire = ring(\n        axis=vector(0, 0, 1),\n        radius=wheel_radius,\n        thickness=0.035,\n        color=color.black\n    )\n\n    rim = ring(\n        axis=vector(0, 0, 1),\n        radius=wheel_radius * 0.78,\n        thickness=0.012,\n        color=color.white\n    )\n\n    spokes = []\n    for angle in [0, pi/4, pi/2, 3*pi/4]:\n        dx = wheel_radius * 0.76 * cos(angle)\n        dy = wheel_radius * 0.76 * sin(angle)\n        spokes.append(\n            cylinder(\n                pos=vector(-dx, -dy, 0),\n                axis=vector(2 * dx, 2 * dy, 0),\n                radius=0.004,\n                color=color.white\n            )\n        )\n\n    hub = sphere(\n        pos=vector(0, 0, 0),\n        radius=0.035,\n        color=color.gray(0.2)\n    )\n\n    return compound([tire, rim, hub] + spokes)\n\nwheel_rear = make_wheel()\nwheel_front = make_wheel()\n\n# 실제 스케일 기반 자전거 프레임 좌표\nn1 = vector(rear_wheel_center_offset, wheel_radius, 0)       # 뒷바퀴 중심\nn5 = vector(front_wheel_center_offset, wheel_radius, 0)      # 앞바퀴 중심\nn2 = vector(-0.10, wheel_radius + 0.05, 0)                   # 크랭크\nn3 = vector(-0.35, 0.95, 0)                                  # 안장 아래\nn4 = vector(0.48, 1.03, 0)                                   # 핸들 아래\n\nparts = []\nframe_r = 0.025\n\n# 자전거 프레임\nparts.append(cylinder(pos=n1, axis=n2-n1, radius=frame_r, color=color.red))\nparts.append(cylinder(pos=n2, axis=n3-n2, radius=frame_r, color=color.red))\nparts.append(cylinder(pos=n3, axis=n1-n3, radius=frame_r, color=color.red))\nparts.append(cylinder(pos=n3, axis=n4-n3, radius=frame_r, color=color.red))\nparts.append(cylinder(pos=n2, axis=n4-n2, radius=frame_r, color=color.red))\nparts.append(cylinder(pos=n4, axis=n5-n4, radius=frame_r, color=color.red))\n\n# 포크\nparts.append(cylinder(pos=n4, axis=n5-n4, radius=0.018, color=color.black))\n\n# 안장\nparts.append(\n    box(\n        pos=n3 + vector(-0.05, 0.08, 0),\n        size=vector(0.32, 0.055, 0.12),\n        color=color.black\n    )\n)\n\n# 핸들바\nparts.append(\n    cylinder(\n        pos=n4 + vector(0.05, 0.08, -0.20),\n        axis=vector(0, 0, 0.40),\n        radius=0.018,\n        color=color.black\n    )\n)\n\n# 크랭크\nparts.append(\n    ring(\n        pos=n2,\n        axis=vector(0, 0, 1),\n        radius=0.11,\n        thickness=0.012,\n        color=color.black\n    )\n)\n\n# ==========================================\n# 6-1. 자전거 위 라이더 조형물\n# ==========================================\nskin = vector(1.0, 0.82, 0.65)\nshirt = color.blue\npants = color.black\nshoe = color.white\n\n# 라이더 키가 실제 사람보다 약간 작게 보이도록 1.5~1.6 m 정도로 구성\nhip = n3 + vector(0.00, 0.10, 0)\nshoulder = hip + vector(0.22, 0.43, 0)\nhead_center = shoulder + vector(0.07, 0.24, 0)\n\nhand_target = n4 + vector(0.10, 0.08, 0)\n\npedal_target_front = n2 + vector(0.11, -0.08, 0)\npedal_target_back = n2 + vector(-0.11, -0.09, 0)\n\n# 머리\nparts.append(\n    sphere(\n        pos=head_center,\n        radius=0.11,\n        color=skin\n    )\n)\n\n# 몸통\nparts.append(\n    cylinder(\n        pos=hip,\n        axis=shoulder - hip,\n        radius=0.045,\n        color=shirt\n    )\n)\n\n# 팔\nelbow1 = shoulder + vector(0.16, -0.05, 0)\nparts.append(cylinder(pos=shoulder, axis=elbow1 - shoulder, radius=0.025, color=shirt))\nparts.append(cylinder(pos=elbow1, axis=hand_target - elbow1, radius=0.020, color=skin))\n\nshoulder2 = shoulder + vector(-0.03, -0.01, 0)\nelbow2 = shoulder2 + vector(0.14, -0.07, 0)\nhand_target2 = hand_target + vector(-0.03, -0.02, 0)\n\nparts.append(cylinder(pos=shoulder2, axis=elbow2 - shoulder2, radius=0.025, color=shirt))\nparts.append(cylinder(pos=elbow2, axis=hand_target2 - elbow2, radius=0.020, color=skin))\n\n# 다리\nknee1 = hip + vector(0.10, -0.35, 0)\nparts.append(cylinder(pos=hip, axis=knee1 - hip, radius=0.030, color=pants))\nparts.append(cylinder(pos=knee1, axis=pedal_target_front - knee1, radius=0.026, color=pants))\nparts.append(sphere(pos=pedal_target_front, radius=0.030, color=shoe))\n\nhip2 = hip + vector(-0.03, -0.01, 0)\nknee2 = hip2 + vector(-0.05, -0.30, 0)\n\nparts.append(cylinder(pos=hip2, axis=knee2 - hip2, radius=0.030, color=pants))\nparts.append(cylinder(pos=knee2, axis=pedal_target_back - knee2, radius=0.026, color=pants))\nparts.append(sphere(pos=pedal_target_back, radius=0.030, color=shoe))\n\nbike_frame = compound(parts)\n\n# 속도감용 잔상: 실제 스케일에 맞춰 얇고 짧게 표시\nmotion_streaks = []\nfor i in range(7):\n    streak = cylinder(\n        pos=vector(-1.0 - i * 0.35, 0.9 + i * 0.04, 0),\n        axis=vector(-0.55, 0, 0),\n        radius=0.012,\n        color=color.white,\n        opacity=0.28\n    )\n    motion_streaks.append(streak)\n\ndef update_bike_pos(x):\n    bike_frame.pos.x = x\n    wheel_rear.pos = n1 + vector(x, 0, 0)\n    wheel_front.pos = n5 + vector(x, 0, 0)\n\n    for i, streak in enumerate(motion_streaks):\n        streak.pos = vector(x - 0.7 - i * 0.30, 0.95 + i * 0.04, 0)\n        streak.axis = vector(-0.45 - i * 0.07, 0, 0)\n\nupdate_bike_pos(initial_bike_x)\n\nscene.center = vector(4, 1.1, 0)\n\n# ==========================================\n# 7. UI\n# ==========================================\ndef toggle_run(b):\n    global running\n    running = True\n\nscene.append_to_caption("\\n")\nbutton(text="▶ 시뮬레이션 시작 / 다시하기", bind=toggle_run, background=color.orange)\nscene.append_to_caption("\\n\\n")\n\nscene.append_to_caption("초기 속력: " + str(speed_kmh) + " km/h = " + str(round(v0, 2)) + " m/s\\n")\nscene.append_to_caption("반응 시간: " + str(t_reaction) + " s\\n")\nscene.append_to_caption("마찰계수 μ: " + str(mu) + "\\n")\nscene.append_to_caption("화면 재생 속도 배율: " + str(play_speed) + "배\\n")\nscene.append_to_caption("시간 스케일: play_speed = 1.0일 때 실제 시간과 거의 1:1\\n")\nscene.append_to_caption("기준점: 자전거 앞바퀴의 가장 앞부분\\n")\nscene.append_to_caption("자전거 길이: " + str(bike_length) + " m\\n")\nscene.append_to_caption("도로 중앙선 한 칸 길이: " + str(lane_mark_length) + " m\\n")\nscene.append_to_caption("도로 옆 거리 눈금: 1 m 간격, 5 m마다 숫자 표시\\n")\nscene.append_to_caption("위험 발견 고정 위치: 출발선 기준 " + str(danger_x) + " m\\n")\nscene.append_to_caption("보행자 고정 위치: 출발선 기준 " + str(pedestrian_x) + " m\\n")\nscene.append_to_caption("위험 발견 후 보행자까지 거리: " + str(pedestrian_distance_from_danger) + " m\\n")\nscene.append_to_caption("위험 발견 후 예상 정지거리: " + str(round(danger_to_stop_distance, 1)) + " m\\n")\nscene.append_to_caption("충돌 시: 보행자가 만화처럼 앞으로 튕겨 나갑니다.\\n\\n")\n\n# ==========================================\n# 8. 그래프 설정\n# ==========================================\nposition_ymax = max_distance * 1.15\ninitial_KE = 0.5 * m * (v0**2)\nenergy_ymax = initial_KE * 1.25\n\ng1 = graph(\n    title="<b>Position-Time Graph</b> (앞바퀴 앞부분 기준)",\n    xtitle="Time (s)",\n    ytitle="Position (m)",\n    width=800,\n    height=420,\n    ymin=0,\n    ymax=position_ymax\n)\n\ng2 = graph(\n    title="<b>Energy Conservation</b>",\n    xtitle="Time (s)",\n    ytitle="Energy (J)",\n    width=800,\n    height=300,\n    ymin=0,\n    ymax=energy_ymax\n)\n\npos_curve = gcurve(graph=g1, color=color.black, width=2)\nke_curve = gcurve(graph=g2, color=color.orange, label="Kinetic Energy")\nwork_curve = gcurve(graph=g2, color=color.red, label="Friction Work")\ntotal_e_curve = gcurve(graph=g2, color=color.green, label="Total Energy")\n\n# ==========================================\n# 9. 메인 애니메이션 루프\n# ==========================================\nwhile True:\n    rate(frame_rate)\n\n    if running:\n        current_v = v0\n        current_x = initial_bike_x\n        t = 0\n        dt = (1 / frame_rate) * play_speed\n        work_friction = 0\n\n        # 보행자와 충돌 상태 초기화\n        collision_happened = False\n        pedestrian_v = vector(0, 0, 0)\n        pedestrian_omega = 0\n        pedestrian.pos = vector(pedestrian_x, road_surface_y, 0)\n        pedestrian.up = vector(0, 1, 0)\n        pedestrian.axis = vector(1, 0, 0)\n        pedestrian_label.visible = True\n        pedestrian_label.pos = vector(pedestrian_x, 2.05, 0)\n        collision_label.text = ""\n\n        update_bike_pos(current_x)\n\n        # 앞바퀴 앞부분 기준 이벤트 시각\n        # 위험 발견 위치는 항상 danger_x로 고정됩니다.\n        t_danger = danger_x / v0\n        t_brake = t_danger + t_reaction\n\n        # 제동 시작선은 위험 발견 후 반응거리만큼 앞에 생깁니다.\n        # 따라서 조건을 바꾸면 이 선은 달라질 수 있습니다.\n        brake_line.pos.x = danger_x + reaction_distance\n\n        pos_curve.delete()\n        ke_curve.delete()\n        work_curve.delete()\n        total_e_curve.delete()\n\n        pos_curve = gcurve(graph=g1, color=color.black, width=2)\n        ke_curve = gcurve(graph=g2, color=color.orange, label="Kinetic Energy")\n        work_curve = gcurve(graph=g2, color=color.red, label="Friction Work")\n        total_e_curve = gcurve(graph=g2, color=color.green, label="Total Energy")\n\n        while current_v > 0 and running:\n            rate(frame_rate)\n\n            front_edge_x = current_x + front_edge_offset\n\n            # 충돌 판정:\n            # 앞바퀴의 가장 앞부분이 보행자 중심 근처에 닿으면 보행자를 앞으로 튕깁니다.\n            # 시각적 효과를 위한 간단한 만화식 모션이며, 실제 인체 운동을 정확히 나타내는 것은 아닙니다.\n            if (not collision_happened) and front_edge_x >= pedestrian_x - 0.18:\n                collision_happened = True\n                pedestrian_label.visible = False\n                collision_label.text = "충돌!"\n                collision_label.pos = vector(pedestrian_x, 2.55, 0)\n\n                # 충돌 순간 자전거 속도 일부를 보행자의 초기 속도로 넘겨주는 느낌\n                pedestrian_v = vector(max(2.0, current_v * 0.75), 3.2, 0)\n                pedestrian_omega = -10.0\n\n            # 충돌 후 보행자 포물선 운동 + 회전\n            if collision_happened:\n                pedestrian_v.y = pedestrian_v.y - g * dt\n                pedestrian.pos = pedestrian.pos + pedestrian_v * dt\n\n                # 보행자 몸 전체를 z축 기준으로 회전시켜 날아가는 느낌을 줍니다.\n                pedestrian.rotate(\n                    angle=pedestrian_omega * dt,\n                    axis=vector(0, 0, 1),\n                    origin=pedestrian.pos\n                )\n\n                collision_label.pos = pedestrian.pos + vector(0, 2.2, 0)\n\n                # 바닥 아래로 너무 깊게 내려가지 않도록 간단히 멈춤\n                if pedestrian.pos.y < road_surface_y:\n                    pedestrian.pos.y = road_surface_y\n                    pedestrian_v = vector(pedestrian_v.x * 0.35, 0, 0)\n                    pedestrian_omega = pedestrian_omega * 0.65\n\n            # 카메라가 앞바퀴 앞부분을 기준으로 따라가되, 약간 앞쪽을 보여줍니다.\n            target_center_x = front_edge_x + 1.4\n            scene.center = vector(target_center_x, 1.25, 0)\n\n            if t < t_danger:\n                a = 0\n                pos_curve.color = color.black\n\n            elif t < t_brake:\n                a = 0\n                pos_curve.color = color.blue\n\n            else:\n                a = -mu * g\n                pos_curve.color = color.red\n\n                distance_moved = current_v * dt\n                work_friction += (mu * m * g) * distance_moved\n\n            current_v += a * dt\n            if current_v < 0:\n                current_v = 0\n\n            current_x += current_v * dt\n            update_bike_pos(current_x)\n\n            current_radius = wheel_radius\n            d_theta = (current_v / current_radius) * dt\n            wheel_front.rotate(angle=-d_theta, axis=vector(0, 0, 1))\n            wheel_rear.rotate(angle=-d_theta, axis=vector(0, 0, 1))\n\n            KE = 0.5 * m * (current_v**2)\n            pos_curve.plot(t, front_edge_x)\n            ke_curve.plot(t, KE)\n            work_curve.plot(t, work_friction)\n            total_e_curve.plot(t, KE + work_friction)\n\n            t += dt\n\n        running = False\n'

    # Streamlit 비교군 1 설정값을 VPython 코드 변수에 반영
    code = template
    code = code.replace(
        "speed_kmh = 30",
        f"speed_kmh = {float(speed_kmh):.2f}   # Streamlit 비교군 1 초기 속력 (km/h)",
        1,
    )
    code = code.replace(
        "t_reaction = 0.4",
        f"t_reaction = {float(reaction_time):.4f}   # Streamlit 비교군 1 반응 시간 (초)",
        1,
    )
    code = code.replace(
        "m = 60",
        f"m = {float(mass_kg):.2f}   # Streamlit 비교군 1 질량 (kg)",
        1,
    )
    code = code.replace(
        "mu = 0.70",
        f"mu = {float(mu_value):.4f}   # Streamlit 비교군 1 노면 마찰계수: {road_name}",
        1,
    )

    # v0는 speed_kmh에서 자동 계산되도록 유지한다.
    # 즉, 학생이 speed_kmh만 바꾸어도 v0가 함께 바뀐다.
    return code



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
    padding-top: 2.4rem !important;
    padding-top: 1.4rem;
    padding-bottom: 3.2rem;
}
.main-title {
    margin-top: 0.6rem;
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
# 화면 상단: 제목 + 안내, 입력값은 사이드바에서 조절
# ------------------------------------------------------------
st.markdown("<div class='main-title'>🚲 픽시 자전거 정지거리와 이차함수</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='main-subtitle'>속도, 반응 시간, 노면 상태가 정지거리 함수 S(v)=Av²+Bv+0의 계수를 어떻게 바꾸는지 확인합니다.</div>",
    unsafe_allow_html=True,
)

st.markdown("<div class='section-title'>⚙️ 조건 설정</div>", unsafe_allow_html=True)
st.markdown(
    """
<div class='info-box'>
조건 설정은 왼쪽 사이드 바에서 조절할 수 있습니다. 시뮬레이션은 비교군 1의 조건을 통해 실행됩니다. 비교군2, 3을 통해 여러 상황에서의 제동 거리를 비교할 수 있습니다.
</div>
""",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# 왼쪽 사이드바: 비교군 1, 2, 3 설정
# ------------------------------------------------------------
with st.sidebar:
    st.markdown("## ⚙️ 조건 설정")
    st.caption("비교군 1은 시뮬레이션과 VPython 코드의 기준값입니다.")
    st.divider()

    st.markdown("### 비교군 1")
    bike_mass = st.slider(
        "비교군 1 질량(kg)",
        min_value=40.0,
        max_value=100.0,
        value=65.0,
        step=1.0,
        key="mass1_sidebar",
        help="현실감을 위해 사람+자전거 전체 질량 범위로 두었습니다. 단순 마찰 모델에서는 정지거리 계산식에서 질량이 약분됩니다.",
    )
    speed_kmh = st.slider(
        "비교군 1 초기 속도 x (km/h)",
        min_value=0,
        max_value=60,
        value=30,
        step=1,
        key="speed1_sidebar",
    )
    reaction_time = st.slider(
        "비교군 1 반응 시간(초)",
        min_value=0.20,
        max_value=2.50,
        value=1.00,
        step=0.01,
        format="%.2f",
        key="reaction1_sidebar",
    )
    road_label = st.selectbox(
        "비교군 1 노면 상태",
        list(ROAD_OPTIONS.keys()),
        index=0,
        key="road1_sidebar",
    )
    mu = ROAD_OPTIONS[road_label]["mu"]

    playback_speed = st.slider(
        "시뮬레이션 배속",
        min_value=0.1,
        max_value=1.0,
        value=1.0,
        step=0.1,
        key="playback_speed_sidebar",
        help="1.0배속이면 물리 시간 1초가 실제 화면에서도 1초입니다. 0.1배속이면 10배 느리게 관찰합니다.",
    )

    st.divider()

    st.markdown("### 비교군 2")
    use_group2 = st.checkbox("비교군 2 표시", value=True, key="use_group2_sidebar")
    mass2 = st.slider(
        "비교군 2 질량(kg)",
        40.0,
        100.0,
        65.0,
        1.0,
        key="mass2_sidebar",
        disabled=not use_group2,
    )
    speed2 = st.slider(
        "비교군 2 초기 속도(km/h)",
        0,
        60,
        40,
        1,
        key="speed2_sidebar",
        disabled=not use_group2,
    )
    reaction2 = st.slider(
        "비교군 2 반응 시간(초)",
        0.20,
        2.50,
        1.00,
        0.01,
        format="%.2f",
        key="reaction2_sidebar",
        disabled=not use_group2,
    )
    road2 = st.selectbox(
        "비교군 2 노면 상태",
        list(ROAD_OPTIONS.keys()),
        index=1,
        key="road2_sidebar",
        disabled=not use_group2,
    )
    if not use_group2:
        mass2, speed2, reaction2, road2 = 65.0, 40, 1.00, "젖은 아스팔트"

    st.divider()

    st.markdown("### 비교군 3")
    use_group3 = st.checkbox("비교군 3 표시", value=True, key="use_group3_sidebar")
    mass3 = st.slider(
        "비교군 3 질량(kg)",
        40.0,
        100.0,
        65.0,
        1.0,
        key="mass3_sidebar",
        disabled=not use_group3,
    )
    speed3 = st.slider(
        "비교군 3 초기 속도(km/h)",
        0,
        60,
        50,
        1,
        key="speed3_sidebar",
        disabled=not use_group3,
    )
    reaction3 = st.slider(
        "비교군 3 반응 시간(초)",
        0.20,
        2.50,
        1.20,
        0.01,
        format="%.2f",
        key="reaction3_sidebar",
        disabled=not use_group3,
    )
    road3 = st.selectbox(
        "비교군 3 노면 상태",
        list(ROAD_OPTIONS.keys()),
        index=2,
        key="road3_sidebar",
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
현재 조건의 함수: S(v) = {A:.5f}v² + {B:.3f}v + 0<br>
완전제곱식: S(v) = {A:.5f}(v + {B/(2*A):.2f})² - {B*B/(4*A):.2f}
</div>
""",
    unsafe_allow_html=True,
)

st.markdown("<div class='section-title'>2. 자전거 시뮬레이션</div>", unsafe_allow_html=True)
st.markdown(
    f"""
<div class='info-box'>
시뮬레이션은 <b>등속 운동 → 반응 거리 → 제동 거리</b> 순서로 진행됩니다.
위험 발견선은 출발점으로부터 일정한 실제 거리 위치에 고정되어 있고, 조건이 바뀌면 제동 시작선과 정지선만 실제 거리만큼 오른쪽으로 이동합니다.
경로가 화면보다 길어지면 가로 스크롤이 생기며, 1 m 눈금으로 절대적인 길이 감각을 확인할 수 있습니다.
현재 배속은 <b>{playback_speed:.1f}배속</b>입니다.
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
총 정지거리 함수는 초기 속도 $v$에 대한 이차함수입니다.  
여기서 $v$는 km/h 단위의 초기 속도, $S(v)$는 m 단위의 총 정지거리입니다.
"""
)
st.latex(r"S(v)=Av^2+Bv+0")
st.markdown(
    """
반응 시간 동안 이동한 거리는 속도에 비례하므로 일차항 $Bv$가 됩니다.  
제동거리는 속도의 제곱에 비례하므로 이차항 $Av^2$가 됩니다.
"""
)

st.markdown("#### 완전제곱식으로 바꾸기")
st.latex(r"S(v)=Av^2+Bv")
st.latex(r"S(v)=A\left(v^2+\frac{B}{A}v\right)")
st.latex(r"S(v)=A\left[\left(v+\frac{B}{2A}\right)^2-\left(\frac{B}{2A}\right)^2\right]")
st.latex(r"S(v)=A\left(v+\frac{B}{2A}\right)^2-\frac{B^2}{4A}")

st.markdown(
    f"""
<div class='info-box'>
현재 조건에서는 <b>A={A:.5f}</b>, <b>B={B:.3f}</b>입니다.<br>
꼭짓점은 대략 <b>(v={result["vertex_x"]:.2f}, S={result["vertex_y"]:.2f})</b>입니다.
이 꼭짓점은 음수 속도 영역에 있으므로 실제 주행에서 직접 나타나는 지점은 아니지만,
그래프가 기본 포물선 <b>y=Av²</b>을 평행이동한 형태임을 보여줍니다.
</div>
""",
    unsafe_allow_html=True,
)

st.markdown("### 3-2. 과학(물리): 운동에너지, 마찰력, 일")
st.markdown(
    """
달리는 자전거는 운동에너지를 가지고 있습니다. 속도가 커질수록 운동에너지는 $v^2$에 비례하여 커집니다.
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
위 식에서 질량 $m$은 양쪽에 모두 들어 있으므로 약분됩니다.
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

st.markdown("앱의 그래프에서 쓰는 속도 변수 $v$는 km/h 단위입니다. 따라서 실제 m/s 단위 속도는 $v/3.6$입니다.")
st.latex(r"v_{\mathrm{m/s}}=\frac{v}{3.6}")
st.latex(r"S(v)=\frac{1}{25.92\mu g}v^2+\frac{t_r}{3.6}v+0")

st.markdown(
    """
<div class='info-box'>
정리하면, 픽시 자전거의 위험성은 속도가 조금 증가할 때 정지거리가 단순히 조금 늘어나는 정도가 아니라,
제동거리 항 때문에 <b>제곱에 가깝게 빠르게 증가한다</b>는 데 있습니다.
특히 노면 마찰계수 μ가 작으면 이차항의 계수 A가 커져 그래프가 더 가파르게 올라갑니다.
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
초기 속력, 반응 시간, 질량, 노면 마찰계수가 자동 반영됩니다.
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

st.markdown("<div class='section-title'>5. 내 반응속도 기준 안전 속도 역산</div>", unsafe_allow_html=True)

st.markdown(
    """
<div class='info-box'>
아래 계산은 VPython 실습 코드의 상황을 기준으로 합니다.
위험 발견 위치는 출발선 기준 <b>5 m</b>, 보행자 위치는 출발선 기준 <b>10 m</b>이므로,
위험을 발견한 뒤 보행자까지 남은 거리는 <b>5 m</b>입니다.
본인의 반응속도와 현재 비교군 1의 노면 조건에서, 이 5 m 안에 멈추려면 몇 km/h 이하로 달려야 하는지 역산합니다.
</div>
""",
    unsafe_allow_html=True,
)

VPYTHON_DANGER_X = 5.0
VPYTHON_PEDESTRIAN_X = 10.0
available_distance = VPYTHON_PEDESTRIAN_X - VPYTHON_DANGER_X

c_inv1, c_inv2 = st.columns([1, 1])

with c_inv1:
    personal_reaction_time = st.number_input(
        "본인 반응속도 입력(초)",
        min_value=0.10,
        max_value=3.00,
        value=float(reaction_time),
        step=0.01,
        format="%.2f",
        help="반응속도 측정 페이지에서 나온 평균값을 초 단위로 입력합니다. 예: 420 ms = 0.420초",
    )

    st.caption(
        f"현재 비교군 1 노면: {road_label} / 마찰계수 μ = {mu:.2f} / 위험 발견 후 보행자까지 거리 = {available_distance:.1f} m"
    )

inverse_result = inverse_max_speed_kmh(
    available_distance=available_distance,
    reaction_time=float(personal_reaction_time),
    mu=float(mu),
)

current_total_for_personal = calc_result(
    speed_kmh=float(speed_kmh),
    reaction_time=float(personal_reaction_time),
    mu=float(mu),
)

with c_inv2:
    safe_speed_kmh = inverse_result["speed_kmh"]
    margin = available_distance - current_total_for_personal["total_stopping_distance"]

    st.metric(
        "5 m 안에 멈추기 위한 최대 속력",
        f"{safe_speed_kmh:.1f} km/h",
        delta=f"현재 비교군 1 속도 {float(speed_kmh):.0f} km/h",
    )

    if margin >= 0:
        st.success(
            f"현재 속도 {float(speed_kmh):.0f} km/h에서는 약 {margin:.1f} m 여유를 두고 멈출 수 있습니다."
        )
    else:
        st.error(
            f"현재 속도 {float(speed_kmh):.0f} km/h에서는 약 {abs(margin):.1f} m만큼 더 필요합니다. 보행자 위치를 지나서 멈추는 조건입니다."
        )

st.latex(r"S = vt_r + \frac{v^2}{2\mu g}")

st.markdown("#### 근의 공식으로 최대 속력 구하기")
st.markdown(
    """
위 식에서 멈출 수 있는 거리 $S$, 반응 시간 $t_r$, 마찰계수 $\mu$, 중력가속도 $g$가 정해져 있다고 보면,
미지수는 속도 $v$입니다. 따라서 이 식은 $v$에 대한 이차방정식으로 볼 수 있습니다.
"""
)

st.latex(r"\frac{1}{2\mu g}v^2+t_rv-S=0")
st.markdown("양변에 $2\mu g$를 곱하면 다음과 같이 정리됩니다.")
st.latex(r"v^2+2\mu g t_r v-2\mu g S=0")

st.markdown("이차방정식 $av^2+bv+c=0$에서 각 계수는 다음과 같습니다.")
st.latex(r"a=1,\quad b=2\mu g t_r,\quad c=-2\mu gS")

st.markdown("근의 공식을 적용하면 다음과 같습니다.")
st.latex(r"v=\frac{-2\mu g t_r\pm\sqrt{(2\mu g t_r)^2+8\mu gS}}{2}")

st.markdown(
    """
여기서 구하는 값은 방향을 포함한 속도가 아니라 빠르기만 나타내는 속력입니다. 속도는 빠르기와 운동의 방향을 포함한 개념이지만, 속력은 빠르기만 있는 개념이기 때문에 음수가 될 수 없습니다. 따라서 물리적으로 의미 있는 해는 양의 근입니다.
"""
)
st.latex(r"v=-\mu g t_r+\sqrt{(\mu g t_r)^2+2\mu gS}")

st.markdown("이때 위 식으로 구한 $v$는 m/s 단위이므로, km/h로 바꾸려면 3.6을 곱합니다.")
st.latex(r"v_{\mathrm{km/h}}=3.6\left[-\mu g t_r+\sqrt{(\mu g t_r)^2+2\mu gS}\right]")

st.markdown(
    f"""
<div class='info-box'>
현재 계산에서는 <b>S={available_distance:.1f} m</b>, <b>t<sub>r</sub>={personal_reaction_time:.2f} s</b>,
<b>μ={mu:.2f}</b>, <b>g=9.8 m/s²</b>를 대입합니다.<br>
따라서 최대 속력은 <b>{inverse_result["speed_ms"]:.2f} m/s</b>,
즉 <b>{safe_speed_kmh:.1f} km/h</b>입니다.
</div>
""",
    unsafe_allow_html=True,
)

st.markdown(
    f"""
<div class='info-box'>
역산 결과, 본인 반응속도 <b>{personal_reaction_time:.2f}초</b>와 현재 노면 <b>{road_label}</b> 조건에서
위험 발견 후 <b>{available_distance:.1f} m</b> 안에 멈추려면 초기 속도는 약
<b>{safe_speed_kmh:.1f} km/h 이하</b>여야 합니다.<br>
이때 반응거리는 약 <b>{inverse_result["reaction_distance"]:.1f} m</b>,
제동거리는 약 <b>{inverse_result["braking_distance"]:.1f} m</b>입니다.
</div>
""",
    unsafe_allow_html=True,
)

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
