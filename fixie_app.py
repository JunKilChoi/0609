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

BRAKE_OPTIONS = {
    "일반 자전거 브레이크": {"k": 0.85, "desc": "손 브레이크를 사용해 비교적 안정적으로 제동"},
    "픽시 + 보조 브레이크": {"k": 0.60, "desc": "보조 브레이크가 있는 픽시 자전거"},
    "픽시 페달 제동 중심": {"k": 0.40, "desc": "페달을 버티며 속도를 줄이는 상황"},
    "픽시 미숙련 상황": {"k": 0.25, "desc": "빠르고 안정적인 제동이 어려운 상황"},
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


def calc_coefficients(reaction_time: float, mu: float, k: float) -> dict:
    """S(x)=Ax^2+Bx+0. x 단위는 km/h, S 단위는 m."""
    a_eff = mu * G * k
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


def calc_result(speed_kmh: float, reaction_time: float, mu: float, k: float) -> dict:
    v = speed_kmh / 3.6
    coeff = calc_coefficients(reaction_time, mu, k)
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
    return "매우 위험", "속도와 제동 조건 때문에 정지거리가 급격히 길어졌습니다."


def make_curve(name: str, reaction_time: float, mu: float, k: float, color: str, group: str) -> dict:
    c = calc_coefficients(reaction_time, mu, k)
    return {
        "name": name,
        "reactionTime": float(reaction_time),
        "mu": float(mu),
        "k": float(k),
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
        key = (round(c["reactionTime"], 4), round(c["mu"], 4), round(c["k"], 4), c["group"])
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
let view = {xMin: -40, xMax: 80, yMin: -20, yMax: 80};
let dragging = false;
let last = null;

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
  }
  for (const marker of DATA.speedMarkers) {
    if (marker >= xMin && marker <= xMax) {
      for (const curve of DATA.curves) ys.push(f(curve, marker));
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
  setBestView(-50, Math.max(70, DATA.selectedSpeed + 25));
  draw();
}

function focusPositive() {
  setBestView(0, Math.max(60, DATA.selectedSpeed + 20));
  draw();
}

function zoom(factor, anchorX, anchorY) {
  const x0 = invX(anchorX);
  const y0 = invY(anchorY);

  const newXMin = x0 + (view.xMin - x0) * factor;
  const newXMax = x0 + (view.xMax - x0) * factor;
  const newYMin = y0 + (view.yMin - y0) * factor;
  const newYMax = y0 + (view.yMax - y0) * factor;

  if (Math.abs(newXMax - newXMin) < 3 || Math.abs(newYMax - newYMin) < 1) return;
  if (Math.abs(newXMax - newXMin) > 1000 || Math.abs(newYMax - newYMin) > 2000) return;

  view = {xMin:newXMin, xMax:newXMax, yMin:newYMin, yMax:newYMax};
  draw();
}

function zoomAtCenter(factor) {
  const r = rect();
  zoom(factor, r.width/2, r.height/2);
}

function resizeCanvas() {
  const r = rect();
  const dpr = window.devicePixelRatio || 1;
  canvas.width = Math.round(r.width * dpr);
  canvas.height = Math.round(r.height * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  draw();
}

function drawGrid() {
  const r = rect();
  const w = r.width, h = r.height;
  ctx.clearRect(0, 0, w, h);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, w, h);

  const xStep = niceStep((view.xMax - view.xMin) / 9);
  const yStep = niceStep((view.yMax - view.yMin) / 8);

  ctx.save();
  ctx.beginPath();
  ctx.rect(margins.left, margins.top, plotWidth(), plotHeight());
  ctx.clip();

  ctx.strokeStyle = "#e7edf6";
  ctx.lineWidth = 1;
  ctx.fillStyle = "#64748b";
  ctx.font = "12px Pretendard, Arial";
  ctx.textAlign = "center";
  ctx.textBaseline = "top";

  let x = Math.floor(view.xMin / xStep) * xStep;
  while (x <= view.xMax + 1e-9) {
    const px = sx(x);
    ctx.beginPath();
    ctx.moveTo(px, margins.top);
    ctx.lineTo(px, margins.top + plotHeight());
    ctx.stroke();
    ctx.fillText(String(Math.round(x)), px, margins.top + plotHeight() + 10);
    x += xStep;
  }

  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  let y = Math.floor(view.yMin / yStep) * yStep;
  while (y <= view.yMax + 1e-9) {
    const py = sy(y);
    ctx.beginPath();
    ctx.moveTo(margins.left, py);
    ctx.lineTo(margins.left + plotWidth(), py);
    ctx.stroke();
    ctx.fillText(String(Math.round(y)), margins.left - 10, py);
    y += yStep;
  }

  // axes
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

  // labels
  ctx.fillStyle = "#0f172a";
  ctx.font = "800 15px Pretendard, Arial";
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

  for (const marker of DATA.speedMarkers) {
    if (marker < view.xMin || marker > view.xMax) continue;
    const px = sx(marker);
    ctx.strokeStyle = marker === DATA.selectedSpeed ? "#111827" : "#94a3b8";
    ctx.lineWidth = marker === DATA.selectedSpeed ? 2 : 1.3;
    ctx.setLineDash([6, 6]);
    ctx.beginPath();
    ctx.moveTo(px, margins.top);
    ctx.lineTo(px, margins.top + plotHeight());
    ctx.stroke();

    for (let i=0; i<DATA.curves.length; i++) {
      const curve = DATA.curves[i];
      const y = f(curve, marker);
      if (y < view.yMin || y > view.yMax) continue;
      ctx.setLineDash([]);
      ctx.fillStyle = curve.color;
      ctx.beginPath();
      ctx.arc(px, sy(y), marker === DATA.selectedSpeed && i === 0 ? 6 : 4, 0, Math.PI*2);
      ctx.fill();
    }
  }

  // current label
  const current = DATA.curves[0];
  const cy = f(current, DATA.selectedSpeed);
  if (DATA.selectedSpeed >= view.xMin && DATA.selectedSpeed <= view.xMax && cy >= view.yMin && cy <= view.yMax) {
    const px = sx(DATA.selectedSpeed), py = sy(cy);
    ctx.fillStyle = "#0f172a";
    ctx.font = "900 13px Pretendard, Arial";
    ctx.textAlign = "left";
    ctx.textBaseline = "bottom";
    ctx.fillText(`현재 ${DATA.selectedSpeed.toFixed(0)} km/h, ${cy.toFixed(1)} m`, px + 10, py - 10);
  }

  // vertex of current curve
  const A = current.A, B = current.B;
  const vx = -B / (2*A);
  const vy = f(current, vx);
  if (vx >= view.xMin && vx <= view.xMax && vy >= view.yMin && vy <= view.yMax) {
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
  draw();
});

canvas.addEventListener("wheel", (e) => {
  e.preventDefault();
  const factor = e.deltaY < 0 ? 0.86 : 1.16;
  zoom(factor, e.offsetX, e.offsetY);
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
  draw();
}, {passive:false});
canvas.addEventListener("touchend", () => dragging = false);

window.addEventListener("resize", resizeCanvas);
buildLegend();
setBestView(-50, Math.max(70, DATA.selectedSpeed + 25));
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
  .smoke { fill: #d1d5db; opacity: 0; }
  .skid { stroke: #111827; stroke-width: 5; stroke-linecap: round; opacity: 0; }
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

      <text x="78" y="210" text-anchor="middle" class="small">출발</text>
      <text id="dangerText" x="78" y="210" text-anchor="middle" class="small">위험 발견</text>
      <text id="brakeText" x="78" y="210" text-anchor="middle" class="small">제동 시작</text>
      <text id="stopText" x="1002" y="210" text-anchor="middle" class="small">정지</text>

      <g id="smokeGroup">
        <circle id="smoke1" class="smoke" cx="0" cy="0" r="10"/>
        <circle id="smoke2" class="smoke" cx="0" cy="0" r="14"/>
        <circle id="smoke3" class="smoke" cx="0" cy="0" r="8"/>
        <circle id="smoke4" class="smoke" cx="0" cy="0" r="12"/>
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
  </div>
</div>

<script>
const DATA = __DATA__;

const X0 = 78;
const X1 = 1002;
const ROAD_Y = 250;
const WHEEL_Y = ROAD_Y + 28;
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

function setupMarks() {
  const totalVisual = DATA.approachDistance + DATA.totalStoppingDistance;
  const approachRatio = totalVisual <= 0 ? 0 : DATA.approachDistance / totalVisual;
  const reactionRatio = totalVisual <= 0 ? 0 : DATA.reactionDistance / totalVisual;
  const brakeRatio = totalVisual <= 0 ? 0 : DATA.brakingDistance / totalVisual;

  const dangerX = X0 + (X1 - X0) * approachRatio;
  const brakeX = dangerX + (X1 - X0) * reactionRatio;

  setAttr("approachBar", "x", X0);
  setAttr("approachBar", "width", Math.max(2, (X1-X0)*approachRatio));

  setAttr("reactionBar", "x", dangerX);
  setAttr("reactionBar", "width", Math.max(2, (X1-X0)*reactionRatio));

  setAttr("brakeBar", "x", brakeX);
  setAttr("brakeBar", "width", Math.max(2, (X1-X0)*brakeRatio));

  setAttr("dangerMark", "x1", dangerX);
  setAttr("dangerMark", "x2", dangerX);
  setAttr("dangerText", "x", dangerX);

  setAttr("brakeMark", "x1", brakeX);
  setAttr("brakeMark", "x2", brakeX);
  setAttr("brakeText", "x", brakeX);

  setAttr("stopText", "x", X1);
}

function restart() {
  if (raf) cancelAnimationFrame(raf);
  startReal = null;
  setupMarks();
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
  const bikeX = X0 + (X1 - X0) * fraction;

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
  const brakeStartX = X0 + (X1 - X0) * (brakeStartS / totalVisual);

  if (braking && currentSpeed > 0.05) {
    const skidLen = Math.max(10, bikeX - brakeStartX);
    setAttr("skidLine", "x1", Math.max(brakeStartX, bikeX - skidLen));
    setAttr("skidLine", "y1", WHEEL_Y + 28);
    setAttr("skidLine", "x2", bikeX - 45);
    setAttr("skidLine", "y2", WHEEL_Y + 28);
    setAttr("skidLine", "opacity", 0.55);

    const pulse = (Math.sin(realElapsed * 12) + 1) / 2;
    const baseX = bikeX - 78;
    const baseY = WHEEL_Y + 18;

    const smokes = [
      ["smoke1", baseX - 5 - pulse*8, baseY - 10, 9 + pulse*5, .35 + pulse*.25],
      ["smoke2", baseX - 22 - pulse*12, baseY - 20, 13 + pulse*8, .22 + pulse*.20],
      ["smoke3", baseX - 40 - pulse*16, baseY - 6, 8 + pulse*7, .18 + pulse*.18],
      ["smoke4", baseX - 56 - pulse*20, baseY - 24, 10 + pulse*8, .12 + pulse*.15],
    ];
    for (const [id, cx, cy, r, op] of smokes) {
      setAttr(id, "cx", cx);
      setAttr(id, "cy", cy);
      setAttr(id, "r", r);
      setAttr(id, "opacity", op);
    }
  } else {
    setAttr("skidLine", "opacity", 0);
    for (const id of ["smoke1","smoke2","smoke3","smoke4"]) setAttr(id, "opacity", 0);
  }

  setText("phaseText", phase);
  setText("distanceText", `현재 이동 거리: ${fmt(s)} / 현재 속력: ${(currentSpeed*3.6).toFixed(1)} km/h`);
  setText("clockText", `물리 시간 ${cappedT.toFixed(2)}초 / 실제 재생 시간 ${realElapsed.toFixed(2)}초 / ${DATA.playbackSpeed.toFixed(1)}배속`);

  if (t < totalPhysical) {
    raf = requestAnimationFrame(animate);
  } else {
    setText("phaseText", "정지 완료");
    setText("distanceText", `위험 발견 후 총 정지거리: ${fmt(DATA.totalStoppingDistance)}`);
    setText("clockText", `총 물리 시간 ${totalPhysical.toFixed(2)}초 / 실제 재생 시간 ${(totalPhysical / DATA.playbackSpeed).toFixed(2)}초`);
    setAttr("skidLine", "opacity", 0.35);
    for (const id of ["smoke1","smoke2","smoke3","smoke4"]) setAttr(id, "opacity", 0);
  }
}

setupMarks();
restart();
</script>
</body>
</html>
"""
    return template.replace("__DATA__", data_json)


def show_simulation(data: dict):
    components.html(build_simulation_html(data), height=650, scrolling=False)


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
# 사이드바 입력
# ------------------------------------------------------------
st.sidebar.header("⚙️ 현재 조건 설정")

bike_mass = st.sidebar.slider(
    "자전거+탑승자 질량(kg)",
    min_value=40.0,
    max_value=100.0,
    value=65.0,
    step=1.0,
    help="현실감을 위해 사람+자전거 전체 질량 범위로 두었습니다. 단순 마찰 모델에서는 정지거리 계산식에서 질량이 약분됩니다.",
)

speed_kmh = st.sidebar.slider(
    "초기 속도 x (km/h)",
    min_value=0,
    max_value=60,
    value=30,
    step=1,
)

reaction_time = st.sidebar.slider(
    "반응 시간(초)",
    min_value=0.20,
    max_value=2.50,
    value=1.00,
    step=0.01,
    format="%.2f",
)

road_label = st.sidebar.selectbox("노면 상태", list(ROAD_OPTIONS.keys()), index=0)
mu = ROAD_OPTIONS[road_label]["mu"]

brake_label = st.sidebar.selectbox("제동 방식", list(BRAKE_OPTIONS.keys()), index=2)
k = BRAKE_OPTIONS[brake_label]["k"]

playback_speed = st.sidebar.slider(
    "시뮬레이션 배속",
    min_value=0.1,
    max_value=1.0,
    value=1.0,
    step=0.1,
    help="1.0배속이면 물리 시간 1초가 실제 화면에서도 1초입니다. 0.1배속이면 10배 느리게 관찰합니다.",
)

st.sidebar.divider()
st.sidebar.header("📊 그래프 중첩 비교")

compare_reaction = st.sidebar.checkbox("반응 시간별 그래프 중첩", value=True)
reaction_choices = st.sidebar.multiselect(
    "비교할 반응 시간(초)",
    options=[0.30, 0.50, 0.70, 1.00, 1.30, 1.50, 2.00],
    default=[0.50, 1.00, 1.50] if compare_reaction else [],
    format_func=lambda x: f"{x:.2f}초",
    disabled=not compare_reaction,
)

compare_roads = st.sidebar.checkbox("노면 상태별 그래프 중첩", value=True)
road_choices = st.sidebar.multiselect(
    "비교할 노면",
    options=list(ROAD_OPTIONS.keys()),
    default=["마른 아스팔트", "젖은 아스팔트", "빙판길"] if compare_roads else [],
    disabled=not compare_roads,
)

compare_brakes = st.sidebar.checkbox("제동 방식별 그래프 중첩", value=False)
brake_choices = st.sidebar.multiselect(
    "비교할 제동 방식",
    options=list(BRAKE_OPTIONS.keys()),
    default=["일반 자전거 브레이크", "픽시 페달 제동 중심", "픽시 미숙련 상황"] if compare_brakes else [],
    disabled=not compare_brakes,
)

speed_marker_choices = st.sidebar.multiselect(
    "그래프에 표시할 초기 속도 마커",
    options=[10, 20, 30, 40, 50, 60],
    default=[20, 30, 40],
)

# ------------------------------------------------------------
# 현재 조건 계산
# ------------------------------------------------------------
result = calc_result(speed_kmh, reaction_time, mu, k)
risk, risk_text = risk_label(result["total_stopping_distance"])

# 그래프 곡선 구성
curves = [
    make_curve(
        name=f"현재 조건: {road_label}, {brake_label}, 반응 {reaction_time:.2f}s",
        reaction_time=reaction_time,
        mu=mu,
        k=k,
        color=CURVE_COLORS[0],
        group="현재 조건",
    )
]

color_i = 1
if compare_reaction:
    for rt in reaction_choices:
        curves.append(make_curve(
            name=f"반응 {rt:.2f}s",
            reaction_time=rt,
            mu=mu,
            k=k,
            color=CURVE_COLORS[color_i % len(CURVE_COLORS)],
            group="반응 시간 비교",
        ))
        color_i += 1

if compare_roads:
    for rl in road_choices:
        curves.append(make_curve(
            name=f"{rl} μ={ROAD_OPTIONS[rl]['mu']:.2f}",
            reaction_time=reaction_time,
            mu=ROAD_OPTIONS[rl]["mu"],
            k=k,
            color=CURVE_COLORS[color_i % len(CURVE_COLORS)],
            group="노면 비교",
        ))
        color_i += 1

if compare_brakes:
    for bl in brake_choices:
        curves.append(make_curve(
            name=f"{bl} k={BRAKE_OPTIONS[bl]['k']:.2f}",
            reaction_time=reaction_time,
            mu=mu,
            k=BRAKE_OPTIONS[bl]["k"],
            color=CURVE_COLORS[color_i % len(CURVE_COLORS)],
            group="제동 방식 비교",
        ))
        color_i += 1

curves = dedupe_curves(curves)
speed_markers = sorted(set([speed_kmh] + speed_marker_choices))


# ------------------------------------------------------------
# 화면 출력
# ------------------------------------------------------------
st.markdown("<div class='main-title'>🚲 픽시 자전거 정지거리와 이차함수</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='main-subtitle'>속도, 반응 시간, 노면, 제동 방식이 정지거리 함수 S(x)=Ax²+Bx+0의 계수를 어떻게 바꾸는지 확인합니다.</div>",
    unsafe_allow_html=True,
)

c1, c2, c3, c4 = st.columns(4)
c1.metric("반응거리", fmt_m(result["reaction_distance"]), help="위험을 발견했지만 아직 제동하지 못한 동안 이동한 거리")
c2.metric("제동거리", fmt_m(result["braking_distance"]), help="제동을 시작한 뒤 완전히 멈출 때까지 이동한 거리")
c3.metric("총 정지거리", fmt_m(result["total_stopping_distance"]), help="반응거리 + 제동거리")
c4.metric("유효 감속도", f"{result['a_eff']:.2f} m/s²", help="μ × g × k")

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
여러 반응 시간, 노면 상태, 제동 방식의 그래프를 한 화면에 중첩해 비교할 수 있습니다.
</div>
""",
    unsafe_allow_html=True,
)

graph_data = {
    "curves": curves,
    "selectedSpeed": float(speed_kmh),
    "speedMarkers": [float(x) for x in speed_markers],
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
st.latex(r"F_{\mathrm{마찰}}\approx \mu mgk")

st.markdown(
    """
제동 과정에서 운동에너지는 사라지는 것이 아니라 열에너지, 소리, 타이어와 노면의 변형 등으로 전환됩니다.
시뮬레이션에서 연기와 미끄럼 자국은 이 에너지 전환을 눈에 보이게 표현한 것입니다.
"""
)
st.latex(r"\frac{1}{2}mv^2=\mu mgk\cdot d")

st.markdown(
    """
위 식에서 질량 \(m\)은 양쪽에 모두 들어 있으므로 약분됩니다.
그래서 이 단순 모델에서는 자전거+탑승자 질량을 바꾸어도 정지거리가 직접 변하지 않습니다.
"""
)
st.latex(r"d=\frac{v^2}{2\mu gk}")

st.markdown("### 3-3. 정지거리 식 만들기")
st.markdown("반응거리는 다음과 같습니다.")
st.latex(r"\text{반응거리}=vt_r")

st.markdown("제동거리는 다음과 같습니다.")
st.latex(r"\text{제동거리}=\frac{v^2}{2\mu gk}")

st.markdown("따라서 총 정지거리는 다음과 같습니다.")
st.latex(r"S(v)=vt_r+\frac{v^2}{2\mu gk}")

st.markdown("앱에서는 속도 단위를 km/h로 사용하므로 \(v=x/3.6\)을 대입합니다.")
st.latex(r"v=\frac{x}{3.6}")
st.latex(r"S(x)=\frac{1}{25.92\mu gk}x^2+\frac{t_r}{3.6}x+0")

st.markdown(
    """
<div class='info-box'>
정리하면, 픽시 자전거의 위험성은 속도가 조금 증가할 때 정지거리가 단순히 조금 늘어나는 정도가 아니라,
제동거리 항 때문에 <b>제곱에 가깝게 빠르게 증가한다</b>는 데 있습니다.
특히 노면 마찰계수 \(\mu\)가 작거나 제동 효율 \(k\)가 작으면 이차항의 계수 \(A\)가 커져 그래프가 더 가파르게 올라갑니다.
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
