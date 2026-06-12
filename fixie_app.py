import math
import json
import html as html_lib
import streamlit as st
import streamlit.components.v1 as components

# ============================================================
# 픽시 자전거 정지거리 & 이차함수 그래프 시뮬레이터
# GitHub / Streamlit Cloud용 단일 파일 app.py
# ============================================================

st.set_page_config(
    page_title="픽시 자전거 정지거리와 이차함수",
    page_icon="🚲",
    layout="wide",
    initial_sidebar_state="expanded",
)

G = 9.8

ROAD_PRESETS = {
    "마른 아스팔트": (0.75, "마찰이 비교적 큰 노면"),
    "젖은 아스팔트": (0.45, "비가 온 뒤처럼 미끄러운 노면"),
    "모래·낙엽 있는 길": (0.25, "타이어가 쉽게 미끄러질 수 있는 노면"),
    "빙판길": (0.10, "제동이 매우 어려운 노면"),
    "직접 설정": (0.50, "마찰계수를 직접 조절"),
}

BRAKE_PRESETS = {
    "일반 자전거 브레이크": (0.85, "손 브레이크를 사용해 비교적 안정적으로 제동"),
    "픽시 + 보조 브레이크": (0.60, "픽시지만 보조 브레이크가 있는 상황"),
    "픽시 페달 제동 중심": (0.40, "페달을 버티며 속도를 줄이는 상황"),
    "픽시 미숙련 상황": (0.25, "숙련도가 낮아 빠른 제동이 어려운 상황"),
}


def m_fmt(x: float) -> str:
    if x is None or not math.isfinite(x):
        return "-"
    if abs(x) >= 100:
        return f"{x:.0f} m"
    return f"{x:.1f} m"


def n_fmt(x: float, digits: int = 3) -> str:
    if x is None or not math.isfinite(x):
        return "-"
    return f"{x:.{digits}f}"


def calc_values(speed_kmh: float, reaction_time: float, mu: float, brake_eff: float) -> dict:
    """속도 x(km/h)에 대한 정지거리 모델 계산."""
    v = speed_kmh / 3.6
    a_eff = max(0.001, mu * G * brake_eff)

    reaction_distance = v * reaction_time
    braking_distance = (v * v) / (2 * a_eff)
    total_distance = reaction_distance + braking_distance

    # x가 km/h일 때: S(x)=Ax^2+Bx+0
    A = 1 / (25.92 * a_eff)
    B = reaction_time / 3.6

    # 완전제곱식: S(x)=A(x+p)^2-q
    p = B / (2 * A)
    q = (B * B) / (4 * A)

    return {
        "speed_kmh": speed_kmh,
        "speed_ms": v,
        "a_eff": a_eff,
        "reaction_distance": reaction_distance,
        "braking_distance": braking_distance,
        "total_distance": total_distance,
        "A": A,
        "B": B,
        "p": p,
        "q": q,
        "vertex_x": -p,
        "vertex_y": -q,
        "braking_time": v / a_eff if a_eff > 0 else 0,
    }


def S_of_x(x: float, A: float, B: float) -> float:
    return A * x * x + B * x


def make_metric_card(label: str, value: str, note: str = "") -> str:
    note_html = f"<div class='metric-note'>{html_lib.escape(note)}</div>" if note else ""
    return f"""
    <div class="metric-card">
        <div class="metric-label">{html_lib.escape(label)}</div>
        <div class="metric-value">{html_lib.escape(value)}</div>
        {note_html}
    </div>
    """


def build_quadratic_svg(A: float, B: float, selected_x: float) -> str:
    width, height = 980, 560
    left, right, top, bottom = 76, 34, 48, 70
    plot_w = width - left - right
    plot_h = height - top - bottom

    p = B / (2 * A)
    q = (B * B) / (4 * A)
    vx, vy = -p, -q

    x_min = min(-40.0, vx * 1.65 - 6)
    x_max = 60.0

    samples = []
    for i in range(241):
        x = x_min + (x_max - x_min) * i / 240
        y = S_of_x(x, A, B)
        samples.append((x, y))

    y_values = [y for _, y in samples]
    selected_y = S_of_x(selected_x, A, B)
    y_values.append(selected_y)
    y_min = min(y_values)
    y_max = max(y_values)

    # 완전제곱식의 평행이동을 보이도록 y축 아래쪽도 조금 확보
    y_min = min(y_min * 1.25, -3.0)
    y_max = max(y_max * 1.18, 10.0)

    # 보기 좋은 grid 간격
    span = y_max - y_min
    rough_step = span / 6
    mag = 10 ** math.floor(math.log10(rough_step)) if rough_step > 0 else 1
    norm = rough_step / mag
    if norm < 1.5:
        y_step = 1 * mag
    elif norm < 3.5:
        y_step = 2 * mag
    elif norm < 7.5:
        y_step = 5 * mag
    else:
        y_step = 10 * mag
    y_min = math.floor(y_min / y_step) * y_step
    y_max = math.ceil(y_max / y_step) * y_step

    def sx(x):
        return left + (x - x_min) / (x_max - x_min) * plot_w

    def sy(y):
        return top + plot_h - (y - y_min) / (y_max - y_min) * plot_h

    grid = []
    # x grid: 10 km/h 단위
    x_tick_start = math.ceil(x_min / 10) * 10
    x_tick = x_tick_start
    while x_tick <= x_max + 0.0001:
        px = sx(x_tick)
        cls = "axis0" if abs(x_tick) < 0.001 else "grid"
        grid.append(f"<line x1='{px:.1f}' y1='{top}' x2='{px:.1f}' y2='{top+plot_h}' class='{cls}'/>")
        grid.append(f"<text x='{px:.1f}' y='{height-38}' text-anchor='middle' class='axis-text'>{x_tick:.0f}</text>")
        x_tick += 10

    # y grid
    y_tick = y_min
    while y_tick <= y_max + 0.0001:
        py = sy(y_tick)
        cls = "axis0" if abs(y_tick) < 0.001 else "grid"
        grid.append(f"<line x1='{left}' y1='{py:.1f}' x2='{left+plot_w}' y2='{py:.1f}' class='{cls}'/>")
        grid.append(f"<text x='{left-12}' y='{py+4:.1f}' text-anchor='end' class='axis-text'>{y_tick:.0f}</text>")
        y_tick += y_step

    def make_path(points):
        parts = []
        for idx, (x, y) in enumerate(points):
            cmd = "M" if idx == 0 else "L"
            parts.append(f"{cmd} {sx(x):.1f} {sy(y):.1f}")
        return " ".join(parts)

    neg_points = [(x, y) for x, y in samples if x <= 0]
    pos_points = [(x, y) for x, y in samples if x >= 0]

    selected_px, selected_py = sx(selected_x), sy(selected_y)
    vertex_px, vertex_py = sx(vx), sy(vy)

    svg = f"""
    <svg viewBox="0 0 {width} {height}" width="100%" height="560" role="img" aria-label="정지거리 이차함수 그래프">
      <style>
        .bg {{ fill: #ffffff; }}
        .grid {{ stroke: #e5edf7; stroke-width: 1; }}
        .axis0 {{ stroke: #94a3b8; stroke-width: 2.2; }}
        .axis-text {{ fill: #526070; font-size: 13px; font-family: Pretendard, Arial, sans-serif; font-weight: 700; }}
        .title {{ fill: #111827; font-size: 20px; font-weight: 950; font-family: Pretendard, Arial, sans-serif; }}
        .subtitle {{ fill: #64748b; font-size: 13px; font-weight: 750; font-family: Pretendard, Arial, sans-serif; }}
        .pos-curve {{ fill: none; stroke: #2563eb; stroke-width: 5; stroke-linecap: round; stroke-linejoin: round; }}
        .neg-curve {{ fill: none; stroke: #2563eb; stroke-width: 4; stroke-linecap: round; stroke-linejoin: round; stroke-dasharray: 8 8; opacity: .55; }}
        .marker-line {{ stroke: #111827; stroke-width: 1.6; stroke-dasharray: 6 5; opacity: .6; }}
        .marker-dot {{ fill: #111827; stroke: white; stroke-width: 3; }}
        .vertex-dot {{ fill: #ef4444; stroke: white; stroke-width: 3; }}
        .marker-text {{ fill: #111827; font-size: 14px; font-weight: 900; font-family: Pretendard, Arial, sans-serif; }}
        .vertex-text {{ fill: #b91c1c; font-size: 13px; font-weight: 900; font-family: Pretendard, Arial, sans-serif; }}
        .label {{ fill: #263241; font-size: 15px; font-weight: 900; font-family: Pretendard, Arial, sans-serif; }}
        .legend {{ fill: #334155; font-size: 13px; font-weight: 850; font-family: Pretendard, Arial, sans-serif; }}
        .legend-muted {{ fill: #64748b; font-size: 12px; font-weight: 750; font-family: Pretendard, Arial, sans-serif; }}
      </style>
      <rect class="bg" x="0" y="0" width="{width}" height="{height}" rx="20"/>
      <text x="{left}" y="28" class="title">초기 속도 x와 총 정지거리 S(x)</text>
      <text x="{left}" y="48" class="subtitle">실선: 실제 의미가 있는 x ≥ 0, 점선: 수학적 확장을 위해 표시한 x &lt; 0</text>
      {''.join(grid)}
      <path d="{make_path(neg_points)}" class="neg-curve"/>
      <path d="{make_path(pos_points)}" class="pos-curve"/>
      <line x1="{selected_px:.1f}" y1="{top}" x2="{selected_px:.1f}" y2="{top+plot_h}" class="marker-line"/>
      <circle cx="{selected_px:.1f}" cy="{selected_py:.1f}" r="7" class="marker-dot"/>
      <text x="{selected_px+10:.1f}" y="{selected_py-14:.1f}" class="marker-text">현재: {selected_x:.0f} km/h, {selected_y:.1f} m</text>
      <circle cx="{vertex_px:.1f}" cy="{vertex_py:.1f}" r="6" class="vertex-dot"/>
      <text x="{vertex_px+10:.1f}" y="{vertex_py+18:.1f}" class="vertex-text">꼭짓점 ({vx:.1f}, {vy:.1f})</text>
      <line x1="{left+plot_w-245}" y1="{top+22}" x2="{left+plot_w-195}" y2="{top+22}" class="pos-curve"/>
      <text x="{left+plot_w-185}" y="{top+27}" class="legend">실제 속도 영역</text>
      <line x1="{left+plot_w-245}" y1="{top+48}" x2="{left+plot_w-195}" y2="{top+48}" class="neg-curve"/>
      <text x="{left+plot_w-185}" y="{top+53}" class="legend-muted">음수 속도 영역</text>
      <text x="{left + plot_w/2}" y="{height-10}" text-anchor="middle" class="label">초기 속도 x (km/h)</text>
      <text x="18" y="{top + plot_h/2}" text-anchor="middle" transform="rotate(-90 18 {top + plot_h/2})" class="label">총 정지거리 S(x) (m)</text>
    </svg>
    """
    return svg


def show_svg(svg: str, height: int):
    components.html(
        f"""
        <!doctype html><html lang="ko"><head><meta charset="utf-8">
        <style>body {{ margin:0; padding:0; background:transparent; }}</style>
        </head><body>{svg}</body></html>
        """,
        height=height,
        scrolling=False,
    )


def build_bike_sim_html(data: dict) -> str:
    data_json = json.dumps(data, ensure_ascii=False)
    return f"""
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<style>
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 0; background: transparent; font-family: Pretendard, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }}
  .wrap {{ width:100%; min-height:430px; padding:16px; border-radius:22px; border:1px solid #e1e8f4; background:linear-gradient(180deg,#f8fbff 0%,#eef4ff 100%); }}
  .top {{ display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:12px; }}
  .title {{ font-size:19px; font-weight:950; color:#111827; letter-spacing:-.03em; }}
  .sub {{ color:#64748b; font-size:13px; font-weight:750; margin-top:3px; }}
  button {{ border:0; border-radius:999px; background:#111827; color:white; padding:10px 15px; font-weight:900; cursor:pointer; box-shadow:0 8px 20px rgba(15,23,42,.14); }}
  button:active {{ transform:translateY(1px); }}
  .panel {{ background:rgba(255,255,255,.86); border:1px solid #dbe3ee; border-radius:18px; padding:12px; box-shadow:0 12px 30px rgba(15,23,42,.05); }}
  .legend {{ display:flex; gap:16px; flex-wrap:wrap; color:#475569; font-size:13px; font-weight:800; margin-top:9px; }}
  .chip {{ display:inline-flex; align-items:center; gap:6px; }}
  .swatch {{ width:18px; height:8px; border-radius:99px; display:inline-block; }}
  svg {{ width:100%; height:auto; display:block; }}
  .road {{ fill:#485363; }}
  .dash {{ stroke:rgba(255,255,255,.55); stroke-width:3; stroke-dasharray:20 14; stroke-linecap:round; }}
  .reaction {{ fill:rgba(245,158,11,.74); }}
  .brake {{ fill:rgba(239,68,68,.72); }}
  .txt {{ fill:#111827; font-size:14px; font-weight:950; }}
  .small {{ fill:#64748b; font-size:12px; font-weight:800; }}
  .bike-frame {{ stroke:#111827; stroke-width:6; fill:none; stroke-linecap:round; stroke-linejoin:round; }}
  .wheel {{ fill:#f8fafc; stroke:#111827; stroke-width:6; }}
  .spoke {{ stroke:#111827; stroke-width:2; opacity:.65; }}
  .rider {{ fill:#111827; }}
  .shadow {{ fill:rgba(15,23,42,.17); }}
  .notice {{ margin-top:10px; border-radius:14px; padding:11px 13px; background:#fff7ed; border:1px solid #fed7aa; color:#9a3412; font-size:13px; font-weight:850; line-height:1.45; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <div>
      <div class="title">🚲 자전거 정지 과정</div>
      <div class="sub">노란 구간은 반응거리, 빨간 구간은 제동거리입니다.</div>
    </div>
    <button onclick="restart()">다시 재생</button>
  </div>
  <div class="panel">
    <svg viewBox="0 0 980 310" role="img" aria-label="자전거 정지거리 시뮬레이션">
      <defs>
        <linearGradient id="roadGrad" x1="0" x2="1">
          <stop offset="0%" stop-color="#475569"/>
          <stop offset="100%" stop-color="#64748b"/>
        </linearGradient>
      </defs>
      <rect x="36" y="104" width="908" height="110" rx="30" fill="url(#roadGrad)"/>
      <line x1="66" y1="159" x2="914" y2="159" class="dash"/>
      <rect id="reactionBar" x="66" y="226" width="0" height="18" rx="9" class="reaction"/>
      <rect id="brakeBar" x="66" y="252" width="0" height="18" rx="9" class="brake"/>
      <line x1="66" y1="78" x2="66" y2="284" stroke="#111827" stroke-width="3"/>
      <line id="brakeLine" x1="66" y1="78" x2="66" y2="284" stroke="#f59e0b" stroke-width="3"/>
      <line id="stopLine" x1="914" y1="78" x2="914" y2="284" stroke="#ef4444" stroke-width="3"/>
      <text x="66" y="62" text-anchor="middle" class="txt">위험 발견</text>
      <text id="brakeText" x="66" y="62" text-anchor="middle" class="txt">제동 시작</text>
      <text x="914" y="62" text-anchor="middle" class="txt">정지</text>
      <text id="reactionText" x="100" y="240" class="small">반응거리</text>
      <text id="brakeDistText" x="100" y="266" class="small">제동거리</text>

      <g id="bike" transform="translate(66 159)">
        <ellipse class="shadow" cx="0" cy="52" rx="86" ry="13"></ellipse>
        <g id="rearWheel"><circle class="wheel" cx="-52" cy="24" r="27"/><line class="spoke" x1="-52" y1="-3" x2="-52" y2="51"/><line class="spoke" x1="-79" y1="24" x2="-25" y2="24"/><line class="spoke" x1="-71" y1="5" x2="-33" y2="43"/><line class="spoke" x1="-71" y1="43" x2="-33" y2="5"/></g>
        <g id="frontWheel"><circle class="wheel" cx="58" cy="24" r="27"/><line class="spoke" x1="58" y1="-3" x2="58" y2="51"/><line class="spoke" x1="31" y1="24" x2="85" y2="24"/><line class="spoke" x1="39" y1="5" x2="77" y2="43"/><line class="spoke" x1="39" y1="43" x2="77" y2="5"/></g>
        <path class="bike-frame" d="M -52 24 L -14 -22 L 18 24 L -52 24 M -14 -22 L 58 24 M 18 24 L 58 24 M -14 -22 L -4 -49 M 46 -12 L 58 24 M 46 -12 L 68 -23" />
        <line x1="-23" y1="-53" x2="8" y2="-53" stroke="#111827" stroke-width="7" stroke-linecap="round"/>
        <circle class="rider" cx="-12" cy="-84" r="13"/>
        <path d="M -13 -69 C -10 -53 6 -43 20 -33" stroke="#111827" stroke-width="10" stroke-linecap="round" fill="none"/>
        <path d="M -7 -54 L -34 -18" stroke="#111827" stroke-width="8" stroke-linecap="round"/>
        <path d="M 2 -50 L 22 24" stroke="#111827" stroke-width="8" stroke-linecap="round"/>
        <path d="M 10 -49 L 47 -13" stroke="#111827" stroke-width="7" stroke-linecap="round"/>
      </g>
    </svg>
    <div class="legend">
      <span class="chip"><span class="swatch" style="background:#f59e0b"></span>반응거리</span>
      <span class="chip"><span class="swatch" style="background:#ef4444"></span>제동거리</span>
    </div>
    <div class="notice" id="notice"></div>
  </div>
</div>
<script>
const DATA = {data_json};
const trackStart = 66;
const trackEnd = 914;
const trackW = trackEnd - trackStart;
const total = Math.max(DATA.totalDistance, 0.001);
const reactionRatio = Math.min(1, DATA.reactionDistance / total);
const brakeRatio = Math.max(0, 1 - reactionRatio);
const brakeX = trackStart + trackW * reactionRatio;

document.getElementById('reactionBar').setAttribute('width', Math.max(3, trackW * reactionRatio));
document.getElementById('brakeBar').setAttribute('x', brakeX);
document.getElementById('brakeBar').setAttribute('width', Math.max(3, trackW * brakeRatio));
document.getElementById('brakeLine').setAttribute('x1', brakeX);
document.getElementById('brakeLine').setAttribute('x2', brakeX);
document.getElementById('brakeText').setAttribute('x', brakeX);
document.getElementById('reactionText').setAttribute('x', trackStart + Math.max(38, trackW * reactionRatio / 2));
document.getElementById('brakeDistText').setAttribute('x', brakeX + Math.max(38, trackW * brakeRatio / 2));
document.getElementById('notice').innerHTML = `현재 조건에서 총 정지거리는 <b>${{DATA.totalDistance.toFixed(1)}} m</b>입니다. 속도가 커질수록 빨간 제동 구간이 제곱 관계로 빠르게 길어집니다.`;

let raf = null;
let start = null;
function positionAtTime(t) {{
  const v = DATA.speedMs;
  const a = DATA.aEff;
  if (t <= DATA.reactionTime) return v * t;
  const tb = t - DATA.reactionTime;
  return DATA.reactionDistance + v * tb - 0.5 * a * tb * tb;
}}
function animate(ts) {{
  if (start === null) start = ts;
  const duration = 5600;
  const progress = Math.min(1, (ts - start) / duration);
  const physicalTime = DATA.reactionTime + DATA.brakingTime;
  const t = progress * physicalTime;
  const s = Math.max(0, Math.min(DATA.totalDistance, positionAtTime(t)));
  const frac = DATA.totalDistance <= 0 ? 0 : s / DATA.totalDistance;
  const x = trackStart + trackW * frac;
  const y = 159 + Math.sin(progress * Math.PI * 18) * 1.3;
  document.getElementById('bike').setAttribute('transform', `translate(${{x.toFixed(2)}} ${{y.toFixed(2)}})`);
  const angle = s * 30;
  document.getElementById('rearWheel').setAttribute('transform', `rotate(${{angle.toFixed(1)}} -52 24)`);
  document.getElementById('frontWheel').setAttribute('transform', `rotate(${{angle.toFixed(1)}} 58 24)`);
  if (progress < 1) raf = requestAnimationFrame(animate);
}}
function restart() {{
  if (raf) cancelAnimationFrame(raf);
  start = null;
  raf = requestAnimationFrame(animate);
}}
restart();
</script>
</body>
</html>
"""


def bike_sim_component(data: dict, height: int = 470):
    components.html(build_bike_sim_html(data), height=height, scrolling=False)


# ------------------------------------------------------------
# 스타일
# ------------------------------------------------------------
st.markdown(
    """
<style>
.block-container { padding-top: 1.5rem; padding-bottom: 2.5rem; }
.main-title { font-size: 2.35rem; line-height: 1.15; font-weight: 950; letter-spacing: -0.045em; margin-bottom: .25rem; }
.main-subtitle { color: #526070; font-size: 1.02rem; font-weight: 650; margin-bottom: 1.1rem; }
.metric-grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: .72rem; margin: .7rem 0 1rem; }
.metric-card { background: linear-gradient(180deg, #fff 0%, #f8fafc 100%); border: 1px solid #e3e8f0; border-radius: 18px; padding: .95rem 1rem; box-shadow: 0 10px 24px rgba(15,23,42,.05); }
.metric-label { color: #64748b; font-size: .82rem; font-weight: 850; margin-bottom: .25rem; }
.metric-value { color: #0f172a; font-size: 1.48rem; font-weight: 950; letter-spacing: -.035em; }
.metric-note { color: #64748b; font-size: .76rem; font-weight: 650; margin-top: .28rem; }
.info-box { background:#f8fafc; border:1px solid #e2e8f0; border-radius:16px; padding:1rem 1.1rem; color:#334155; line-height:1.65; font-weight:650; }
.warn-box { background:#fff7ed; border:1px solid #fed7aa; border-radius:16px; padding:1rem 1.1rem; color:#9a3412; line-height:1.6; font-weight:800; }
.formula-box { background:#111827; border-radius:18px; color:#f8fafc; padding:1rem 1.15rem; margin:.6rem 0 1rem; font-weight:850; }
.formula-box code { color:#fff; background:transparent; font-size:1.08rem; }
.small-caption { color:#64748b; font-size:.84rem; font-weight:650; }
@media (max-width: 900px) { .metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
</style>
""",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# 사이드바 입력
# ------------------------------------------------------------
st.sidebar.header("⚙️ 변수 설정")

bike_mass = st.sidebar.slider(
    "자전거 무게(kg)", 5.0, 20.0, 9.0, 0.5,
    help="이상적인 마찰 모델에서는 질량이 약분되므로 정지거리 계산에는 직접 반영하지 않습니다.",
)

speed_kmh = st.sidebar.slider("초기 속도 x (km/h)", 0, 60, 30, 1)
reaction_time = st.sidebar.slider("반응 시간 tᵣ (초)", 0.2, 2.5, 1.0, 0.1)

road_label = st.sidebar.selectbox("노면 상태", list(ROAD_PRESETS.keys()), index=0)
base_mu, road_desc = ROAD_PRESETS[road_label]
if road_label == "직접 설정":
    mu = st.sidebar.slider("마찰계수 μ", 0.05, 1.00, base_mu, 0.01)
else:
    mu = base_mu

brake_label = st.sidebar.selectbox("제동 방식", list(BRAKE_PRESETS.keys()), index=2)
brake_eff, brake_desc = BRAKE_PRESETS[brake_label]

st.sidebar.divider()
st.sidebar.markdown("### 현재 모델")
st.sidebar.write(f"노면 마찰계수 μ = **{mu:.2f}**")
st.sidebar.write(f"제동 효율 k = **{brake_eff:.2f}**")
st.sidebar.write(f"자전거 무게 = **{bike_mass:.1f} kg** · 계산식에는 직접 미반영")

values = calc_values(speed_kmh, reaction_time, mu, brake_eff)
A, B, p, q = values["A"], values["B"], values["p"], values["q"]

# ------------------------------------------------------------
# 본문
# ------------------------------------------------------------
st.markdown("<div class='main-title'>🚲 픽시 자전거 정지거리와 이차함수</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='main-subtitle'>초기 속도에 따라 정지거리가 어떻게 증가하는지 보고, 그 관계가 왜 이차함수인지 확인합니다.</div>",
    unsafe_allow_html=True,
)

metric_html = "<div class='metric-grid'>"
metric_html += make_metric_card("반응거리", m_fmt(values["reaction_distance"]), "위험 발견 후 제동 전")
metric_html += make_metric_card("제동거리", m_fmt(values["braking_distance"]), "제동 시작 후 정지까지")
metric_html += make_metric_card("총 정지거리", m_fmt(values["total_distance"]), "반응거리 + 제동거리")
metric_html += make_metric_card("유효 감속도", f"{values['a_eff']:.2f} m/s²", "μ × g × k")
metric_html += "</div>"
st.markdown(metric_html, unsafe_allow_html=True)

left, right = st.columns([1.25, 1])

with left:
    st.subheader("📈 이차함수 그래프")
    svg = build_quadratic_svg(A, B, speed_kmh)
    show_svg(svg, height=590)

with right:
    st.subheader("🧮 현재 조건의 식")
    st.markdown(
        f"""
<div class='formula-box'>
기본형<br>
<code>S(x) = {A:.5f}x² + {B:.3f}x + 0</code>
</div>
""",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
<div class='formula-box'>
완전제곱식<br>
<code>S(x) = {A:.5f}(x + {p:.2f})² - {q:.2f}</code>
</div>
""",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
<div class='info-box'>
<b>x</b>는 초기 속도(km/h), <b>S(x)</b>는 총 정지거리(m)입니다.<br><br>
완전제곱식으로 보면 그래프는 <b>y = {A:.5f}x²</b>를
왼쪽으로 <b>{p:.2f}</b>, 아래로 <b>{q:.2f}</b> 평행이동한 형태입니다.<br><br>
꼭짓점은 <b>({-p:.2f}, {-q:.2f})</b>입니다. 다만 실제 속도는 음수가 될 수 없으므로
물리적으로 해석하는 영역은 <b>x ≥ 0</b>입니다. 그래프의 음수 속도 부분은 그래서 점선으로 표시했습니다.
</div>
""",
        unsafe_allow_html=True,
    )

st.markdown("---")

sim_data = {
    "speedKmh": float(speed_kmh),
    "speedMs": float(values["speed_ms"]),
    "reactionTime": float(reaction_time),
    "reactionDistance": float(values["reaction_distance"]),
    "brakingDistance": float(values["braking_distance"]),
    "brakingTime": float(values["braking_time"]),
    "totalDistance": float(values["total_distance"]),
    "aEff": float(values["a_eff"]),
}

st.subheader("🎬 정지거리 시뮬레이션")
bike_sim_component(sim_data, height=490)

st.markdown("---")

c1, c2 = st.columns(2)
with c1:
    st.subheader("🔍 식의 의미")
    st.latex(r"S(x)=Ax^2+Bx+0")
    st.markdown(
        f"""
<div class='info-box'>
<b>A = {A:.5f}</b> : 제동거리의 이차항 계수입니다. 노면이 미끄럽거나 픽시 제동 효율이 낮으면 A가 커지고, 그래프가 더 가파르게 휘어집니다.<br><br>
<b>B = {B:.3f}</b> : 반응거리의 일차항 계수입니다. 반응 시간이 길어지면 B가 커집니다.
</div>
""",
        unsafe_allow_html=True,
    )

with c2:
    st.subheader("⚖️ 자전거 무게는 왜 직접 반영하지 않을까?")
    st.markdown(
        """
<div class='info-box'>
단순 마찰 모델에서는 질량이 커지면 관성도 커지지만, 노면을 누르는 힘도 커져 마찰력도 함께 커진다고 봅니다.
그래서 계산식에서 질량이 약분되어 정지거리에 직접 들어가지 않습니다.<br><br>
하지만 실제 상황에서는 타이어 상태, 브레이크 상태, 자세, 숙련도, 바퀴 잠김 등이 영향을 줍니다.
</div>
""",
        unsafe_allow_html=True,
    )

with st.expander("학생 활동 질문 보기"):
    st.markdown(
        """
1. 초기 속도를 10, 20, 40 km/h로 바꾸면 총 정지거리는 같은 비율로 늘어나는가?
2. 반응 시간을 늘리면 그래프의 어느 계수 A 또는 B가 바뀌는가?
3. 마른 아스팔트와 젖은 아스팔트를 비교하면 이차함수 그래프의 휘어짐은 어떻게 달라지는가?
4. 일반 자전거 브레이크와 픽시 페달 제동 중심을 비교하면 어떤 차이가 나타나는가?
5. 자전거 무게를 바꾸어도 정지거리가 변하지 않는 이유를 모델의 가정으로 설명해 보자.
6. 완전제곱식에서 그래프가 어느 방향으로 평행이동되었는지 설명해 보자.
7. 음수 속도 영역을 점선으로 표시한 이유를 말해 보자.
"""
    )

st.markdown("---")
st.markdown(
    "<div class='small-caption'>모델 가정: 공기저항 무시, 평지, 반응 시간 동안 속도 일정, 제동 중 일정한 감속도, 노면 상태를 하나의 마찰계수로 단순화.</div>",
    unsafe_allow_html=True,
)
