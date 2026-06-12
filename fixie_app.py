import math
import json
import html
import streamlit as st
import streamlit.components.v1 as components

# ============================================================
# 픽시 자전거 정지거리 & 이차함수 시뮬레이터
# - 파일명: app.py
# - 필요 패키지: streamlit
# ============================================================

st.set_page_config(
    page_title="픽시 자전거 정지거리와 이차함수",
    page_icon="🚲",
    layout="wide",
    initial_sidebar_state="expanded",
)

G = 9.8
APPROACH_DISTANCE = 8.0  # 위험 발견 전, 짧은 등속 주행 구간. 정지거리 함수 S(x)에는 포함하지 않음.

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


# ------------------------------------------------------------
# 계산 함수
# ------------------------------------------------------------
def fmt_m(x: float) -> str:
    if x is None or not math.isfinite(x):
        return "-"
    if abs(x) >= 100:
        return f"{x:.0f} m"
    return f"{x:.1f} m"


def fmt_s(x: float) -> str:
    if x is None or not math.isfinite(x):
        return "-"
    return f"{x:.2f} s"


def fmt_float(x: float, digits: int = 3) -> str:
    if x is None or not math.isfinite(x):
        return "-"
    return f"{x:.{digits}f}"


def calc_result(speed_kmh: float, reaction_time: float, mu: float, k: float) -> dict:
    """정지거리 계산. x는 km/h, 내부 속도 v는 m/s."""
    v = speed_kmh / 3.6
    a_eff = mu * G * k

    reaction_distance = v * reaction_time
    braking_distance = (v * v) / (2 * a_eff) if a_eff > 0 else math.inf
    total_stopping_distance = reaction_distance + braking_distance

    reaction_time_segment = reaction_time
    braking_time = v / a_eff if a_eff > 0 else math.inf

    # S(x)=Ax^2+Bx+0, x는 km/h
    A = 1 / (25.92 * a_eff) if a_eff > 0 else math.inf
    B = reaction_time / 3.6

    # 완전제곱식 S(x)=A(x-h)^2+k_vertex
    # Ax^2+Bx = A(x + B/(2A))^2 - B^2/(4A)
    vertex_x = -B / (2 * A) if A > 0 and math.isfinite(A) else math.nan
    vertex_y = -(B * B) / (4 * A) if A > 0 and math.isfinite(A) else math.nan

    return {
        "speed_kmh": speed_kmh,
        "speed_ms": v,
        "a_eff": a_eff,
        "reaction_distance": reaction_distance,
        "braking_distance": braking_distance,
        "total_stopping_distance": total_stopping_distance,
        "reaction_time": reaction_time_segment,
        "braking_time": braking_time,
        "A": A,
        "B": B,
        "vertex_x": vertex_x,
        "vertex_y": vertex_y,
    }


def risk_label(total_distance: float) -> tuple[str, str]:
    if total_distance < 8:
        return "낮음", "현재 조건에서는 비교적 짧은 거리에서 멈춥니다."
    if total_distance < 18:
        return "주의", "보행자나 장애물이 가까이 있으면 위험할 수 있습니다."
    if total_distance < 35:
        return "위험", "정지거리가 상당히 길어졌습니다. 속도를 낮추는 것이 가장 효과적입니다."
    return "매우 위험", "속도와 제동 조건 때문에 정지거리가 급격히 길어졌습니다."


# ------------------------------------------------------------
# SVG 그래프
# ------------------------------------------------------------
def nice_step(raw_step: float) -> float:
    if raw_step <= 0 or not math.isfinite(raw_step):
        return 1
    magnitude = 10 ** math.floor(math.log10(raw_step))
    norm = raw_step / magnitude
    if norm < 1.5:
        return 1 * magnitude
    if norm < 3.5:
        return 2 * magnitude
    if norm < 7.5:
        return 5 * magnitude
    return 10 * magnitude


def build_quadratic_graph_svg(
    A: float,
    B: float,
    selected_x: float,
    x_center: float,
    x_width: float,
    y_zoom: float,
    y_shift: float,
) -> str:
    width, height = 1040, 620
    left, right, top, bottom = 78, 34, 38, 76
    plot_w = width - left - right
    plot_h = height - top - bottom

    x_min = x_center - x_width / 2
    x_max = x_center + x_width / 2

    def f(x: float) -> float:
        return A * x * x + B * x

    sample_xs = [x_min + (x_max - x_min) * i / 400 for i in range(401)]
    special_xs = [0, selected_x, -B / (2 * A) if A > 0 else 0]
    ys = [f(x) for x in sample_xs + special_xs if x_min <= x <= x_max]

    base_y_min = min(ys + [0])
    base_y_max = max(ys + [0])
    if abs(base_y_max - base_y_min) < 1e-6:
        base_y_min -= 5
        base_y_max += 5

    base_center = (base_y_min + base_y_max) / 2 + y_shift
    base_half = (base_y_max - base_y_min) / 2
    half = base_half / max(y_zoom, 0.1)
    half = max(5, half)

    y_min = base_center - half
    y_max = base_center + half

    def sx(x: float) -> float:
        return left + (x - x_min) / (x_max - x_min) * plot_w

    def sy(y: float) -> float:
        return top + plot_h - (y - y_min) / (y_max - y_min) * plot_h

    def in_y(y: float) -> bool:
        return y_min <= y <= y_max

    # grid
    grid = []
    x_step = nice_step((x_max - x_min) / 8)
    start_x = math.floor(x_min / x_step) * x_step
    x = start_x
    while x <= x_max + 1e-9:
        px = sx(x)
        grid.append(f"<line x1='{px:.2f}' y1='{top}' x2='{px:.2f}' y2='{top+plot_h}' class='grid'/>")
        grid.append(f"<text x='{px:.2f}' y='{height-42}' text-anchor='middle' class='axis-num'>{x:.0f}</text>")
        x += x_step

    y_step = nice_step((y_max - y_min) / 8)
    start_y = math.floor(y_min / y_step) * y_step
    y = start_y
    while y <= y_max + 1e-9:
        py = sy(y)
        grid.append(f"<line x1='{left}' y1='{py:.2f}' x2='{left+plot_w}' y2='{py:.2f}' class='grid'/>")
        grid.append(f"<text x='{left-12}' y='{py+4:.2f}' text-anchor='end' class='axis-num'>{y:.0f}</text>")
        y += y_step

    axes = []
    if x_min <= 0 <= x_max:
        axes.append(f"<line x1='{sx(0):.2f}' y1='{top}' x2='{sx(0):.2f}' y2='{top+plot_h}' class='axis-strong'/>")
    if y_min <= 0 <= y_max:
        axes.append(f"<line x1='{left}' y1='{sy(0):.2f}' x2='{left+plot_w}' y2='{sy(0):.2f}' class='axis-strong'/>")

    def path_for(domain_min: float, domain_max: float, dashed: bool) -> str:
        n = 260
        xs = [domain_min + (domain_max - domain_min) * i / n for i in range(n + 1)]
        segments = []
        current = []
        for x in xs:
            y = f(x)
            # 적당한 범위 밖은 잘라내되, 화면 경계 근처에서 끊김이 너무 심하지 않게 여유를 둔다.
            if y_min - (y_max - y_min) * 0.2 <= y <= y_max + (y_max - y_min) * 0.2:
                current.append((sx(x), sy(y)))
            else:
                if len(current) >= 2:
                    segments.append(current)
                current = []
        if len(current) >= 2:
            segments.append(current)

        cls = "curve dashed" if dashed else "curve solid"
        paths = []
        for seg in segments:
            d = [f"M {seg[0][0]:.2f} {seg[0][1]:.2f}"]
            for px, py in seg[1:]:
                d.append(f"L {px:.2f} {py:.2f}")
            paths.append(f"<path d='{' '.join(d)}' class='{cls}'/>")
        return "".join(paths)

    dashed_path = ""
    solid_path = ""
    if x_min < 0:
        dashed_path = path_for(x_min, min(0, x_max), dashed=True)
    if x_max > 0:
        solid_path = path_for(max(0, x_min), x_max, dashed=False)

    markers = []
    selected_y = f(selected_x)
    if x_min <= selected_x <= x_max and in_y(selected_y):
        px, py = sx(selected_x), sy(selected_y)
        markers.append(f"<line x1='{px:.2f}' y1='{top}' x2='{px:.2f}' y2='{top+plot_h}' class='selected-line'/>")
        markers.append(f"<circle cx='{px:.2f}' cy='{py:.2f}' r='8' class='selected-dot'/>")
        markers.append(f"<text x='{px+12:.2f}' y='{py-12:.2f}' class='selected-text'>현재 속도 {selected_x:.0f} km/h, {selected_y:.1f} m</text>")

    vertex_x = -B / (2 * A) if A > 0 else math.nan
    vertex_y = f(vertex_x) if math.isfinite(vertex_x) else math.nan
    if math.isfinite(vertex_x) and x_min <= vertex_x <= x_max and in_y(vertex_y):
        vx, vy = sx(vertex_x), sy(vertex_y)
        markers.append(f"<circle cx='{vx:.2f}' cy='{vy:.2f}' r='6' class='vertex-dot'/>")
        markers.append(f"<text x='{vx+10:.2f}' y='{vy+18:.2f}' class='vertex-text'>꼭짓점 ({vertex_x:.1f}, {vertex_y:.1f})</text>")

    svg = f"""
    <svg viewBox="0 0 {width} {height}" width="100%" height="{height}" role="img" aria-label="정지거리 이차함수 그래프">
      <style>
        .bg {{ fill: #ffffff; }}
        .grid {{ stroke: #e6edf7; stroke-width: 1; }}
        .axis-strong {{ stroke: #1f2937; stroke-width: 2.2; }}
        .axis-num {{ fill: #64748b; font-size: 13px; font-family: Pretendard, Arial, sans-serif; }}
        .curve {{ fill: none; stroke: #2563eb; stroke-width: 4; stroke-linecap: round; stroke-linejoin: round; }}
        .solid {{ stroke-dasharray: none; }}
        .dashed {{ stroke-dasharray: 10 9; opacity: .58; }}
        .selected-line {{ stroke: #0f172a; stroke-width: 1.8; stroke-dasharray: 6 6; opacity: .72; }}
        .selected-dot {{ fill: #0f172a; stroke: white; stroke-width: 3; }}
        .selected-text {{ fill: #0f172a; font-size: 14px; font-weight: 900; font-family: Pretendard, Arial, sans-serif; }}
        .vertex-dot {{ fill: #ef4444; stroke: white; stroke-width: 3; }}
        .vertex-text {{ fill: #b91c1c; font-size: 13px; font-weight: 900; font-family: Pretendard, Arial, sans-serif; }}
        .title {{ fill: #0f172a; font-size: 20px; font-weight: 950; font-family: Pretendard, Arial, sans-serif; }}
        .label {{ fill: #334155; font-size: 15px; font-weight: 850; font-family: Pretendard, Arial, sans-serif; }}
        .legend {{ fill: #334155; font-size: 13px; font-weight: 850; font-family: Pretendard, Arial, sans-serif; }}
      </style>
      <rect x="0" y="0" width="{width}" height="{height}" rx="20" class="bg"/>
      <text x="{left}" y="25" class="title">S(x)=Ax²+Bx+0 : 초기 속도 x와 총 정지거리 S(x)</text>
      {''.join(grid)}
      {''.join(axes)}
      {dashed_path}
      {solid_path}
      {''.join(markers)}
      <rect x="{left+12}" y="{top+12}" width="18" height="5" rx="2.5" fill="#2563eb"/>
      <text x="{left+38}" y="{top+19}" class="legend">실제 속도 영역 x ≥ 0</text>
      <line x1="{left+210}" y1="{top+15}" x2="{left+245}" y2="{top+15}" stroke="#2563eb" stroke-width="4" stroke-dasharray="10 8" opacity=".58" stroke-linecap="round"/>
      <text x="{left+254}" y="{top+19}" class="legend">수학적 확장 x &lt; 0</text>
      <text x="{left + plot_w/2}" y="{height-10}" text-anchor="middle" class="label">초기 속도 x (km/h)</text>
      <text x="20" y="{top + plot_h/2}" text-anchor="middle" transform="rotate(-90 20 {top + plot_h/2})" class="label">총 정지거리 S(x) (m)</text>
    </svg>
    """
    return svg


def show_svg(svg: str, height: int):
    components.html(
        f"""<!doctype html><html><head><meta charset="utf-8"><style>body{{margin:0;background:transparent;}}</style></head><body>{svg}</body></html>""",
        height=height,
        scrolling=False,
    )


# ------------------------------------------------------------
# SVG/JS 자전거 시뮬레이션
# ------------------------------------------------------------
def build_simulation_html(data: dict) -> str:
    data_json = json.dumps(data, ensure_ascii=False)

    return f"""
<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
  :root {{
    --ink: #0f172a;
    --muted: #64748b;
    --panel: #ffffff;
    --road: #4b5563;
    --approach: #38bdf8;
    --reaction: #f59e0b;
    --brake: #ef4444;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    background: transparent;
    font-family: Pretendard, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    color: var(--ink);
  }}
  .wrap {{
    width: 100%;
    padding: 15px;
    border-radius: 22px;
    background: linear-gradient(180deg, #f8fbff 0%, #eef4ff 100%);
    border: 1px solid #e1e8f4;
  }}
  .topbar {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
  }}
  .title {{
    font-weight: 950;
    font-size: 20px;
    letter-spacing: -0.03em;
  }}
  .sub {{
    margin-top: 3px;
    color: var(--muted);
    font-size: 13px;
    font-weight: 700;
  }}
  button {{
    border: 0;
    border-radius: 999px;
    background: #111827;
    color: white;
    font-weight: 900;
    padding: 10px 15px;
    cursor: pointer;
    box-shadow: 0 8px 18px rgba(15,23,42,.15);
  }}
  button:active {{ transform: translateY(1px); }}
  .panel {{
    background: rgba(255,255,255,.86);
    border: 1px solid rgba(219,227,238,.96);
    border-radius: 20px;
    padding: 12px;
    box-shadow: 0 12px 30px rgba(15,23,42,.05);
  }}
  .legend {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px 14px;
    margin-top: 8px;
    color: #475569;
    font-size: 12px;
    font-weight: 850;
  }}
  .chip {{ display: inline-flex; align-items: center; gap: 5px; }}
  .swatch {{ display: inline-block; width: 18px; height: 7px; border-radius: 999px; }}
  svg {{ width: 100%; height: auto; display: block; }}
  .label {{ fill: #0f172a; font-size: 14px; font-weight: 950; }}
  .small {{ fill: #64748b; font-size: 12px; font-weight: 800; }}
  .road-line {{ stroke: rgba(255,255,255,.55); stroke-width: 3; stroke-dasharray: 21 16; stroke-linecap: round; }}
  .wheel {{ fill: #f8fafc; stroke: #0f172a; stroke-width: 5; }}
  .spoke {{ stroke: #0f172a; stroke-width: 2; opacity: .75; }}
  .frame {{ stroke: #dc2626; stroke-width: 6; fill: none; stroke-linecap: round; stroke-linejoin: round; }}
  .black-line {{ stroke: #0f172a; stroke-width: 6; fill: none; stroke-linecap: round; stroke-linejoin: round; }}
  .rider {{ stroke: #111827; stroke-width: 7; fill: none; stroke-linecap: round; stroke-linejoin: round; }}
  .head {{ fill: #111827; }}
  .smoke {{ fill: #d1d5db; opacity: 0; }}
  .skid {{ stroke: #111827; stroke-width: 5; stroke-linecap: round; opacity: 0; }}
</style>
</head>
<body>
<div class="wrap">
  <div class="topbar">
    <div>
      <div class="title">🚲 등속 운동 → 반응 거리 → 제동 거리</div>
      <div class="sub">제동 구간에서는 바퀴가 잠겨 미끄러지는 모습으로 표현했습니다.</div>
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

        <!-- 자전거 프레임 -->
        <path class="frame" d="M -48 28 L -14 -22 L 18 28 L -48 28 M -14 -22 L 62 28 M 18 28 L 62 28 M -14 -22 L -4 -50 M 45 -13 L 62 28 M 45 -13 L 72 -22"/>
        <line class="black-line" x1="-21" y1="-54" x2="11" y2="-54"/>
        <line class="black-line" x1="61" y1="-23" x2="78" y2="-28"/>

        <!-- 타고 있는 사람: 머리, 몸통, 팔, 다리 -->
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
const DATA = {data_json};

const X0 = 78;
const X1 = 1002;
const ROAD_Y = 250;
const WHEEL_Y = ROAD_Y + 28;
let raf = null;
let t0 = null;

function setAttr(id, key, val) {{
  const el = document.getElementById(id);
  if (el) el.setAttribute(key, val);
}}
function setText(id, val) {{
  const el = document.getElementById(id);
  if (el) el.textContent = val;
}}
function fmt(x) {{
  if (x >= 100) return `${{x.toFixed(0)}} m`;
  return `${{x.toFixed(1)}} m`;
}}

function setupMarks() {{
  const totalVisual = DATA.approachDistance + DATA.totalStoppingDistance;
  const approachRatio = DATA.approachDistance / totalVisual;
  const reactionRatio = DATA.reactionDistance / totalVisual;
  const brakeRatio = DATA.brakingDistance / totalVisual;

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
}}

function restart() {{
  if (raf) cancelAnimationFrame(raf);
  t0 = null;
  setupMarks();
  raf = requestAnimationFrame(animate);
}}

function animate(ts) {{
  if (t0 === null) t0 = ts;

  const duration = 7.5;
  const elapsed = Math.min(duration, (ts - t0) / 1000);
  const progress = elapsed / duration;

  const v = DATA.speedMs;
  const a = DATA.aEff;

  const physicalTotal = Math.max(0.1, DATA.approachTime + DATA.reactionTime + DATA.brakingTime);
  const t = progress * physicalTotal;

  let s = 0;
  let phase = "대기";
  let braking = false;
  let lockedWheel = false;
  let currentSpeed = v;

  if (DATA.speedKmh <= 0) {{
    s = 0;
    currentSpeed = 0;
    phase = "정지 상태";
  }} else if (t < DATA.approachTime) {{
    s = v * t;
    phase = "등속 운동: 위험 발견 전";
    currentSpeed = v;
  }} else if (t < DATA.approachTime + DATA.reactionTime) {{
    s = DATA.approachDistance + v * (t - DATA.approachTime);
    phase = "반응 시간: 아직 제동하지 못함";
    currentSpeed = v;
  }} else {{
    const tb = t - DATA.approachTime - DATA.reactionTime;
    s = DATA.approachDistance + DATA.reactionDistance + v * tb - 0.5 * a * tb * tb;
    s = Math.min(DATA.approachDistance + DATA.totalStoppingDistance, s);
    currentSpeed = Math.max(0, v - a * tb);
    phase = "제동 중: 바퀴 잠김 + 마찰 작용";
    braking = true;
    lockedWheel = true;
  }}

  s = Math.max(0, Math.min(DATA.approachDistance + DATA.totalStoppingDistance, s));

  const totalVisual = DATA.approachDistance + DATA.totalStoppingDistance;
  const fraction = totalVisual <= 0 ? 0 : s / totalVisual;
  const bikeX = X0 + (X1 - X0) * fraction;

  // 위아래 흔들림 없이 수평 이동만 한다.
  setAttr("bike", "transform", `translate(${{bikeX.toFixed(2)}} ${{ROAD_Y}})`);

  // 바퀴 회전: 제동 전에는 회전, 제동 시작 후에는 잠긴 것처럼 회전 정지
  let wheelAngle = 0;
  if (!lockedWheel) {{
    wheelAngle = s * 31;
  }} else {{
    wheelAngle = (DATA.approachDistance + DATA.reactionDistance) * 31;
  }}
  setAttr("rearWheel", "transform", `rotate(${{wheelAngle.toFixed(2)}} -48 28)`);
  setAttr("frontWheel", "transform", `rotate(${{wheelAngle.toFixed(2)}} 62 28)`);

  const brakeStartS = DATA.approachDistance + DATA.reactionDistance;
  const brakeStartX = X0 + (X1 - X0) * (brakeStartS / totalVisual);

  // 마찰 흔적과 연기
  if (braking && currentSpeed > 0.05) {{
    const skidLen = Math.max(10, bikeX - brakeStartX);
    setAttr("skidLine", "x1", Math.max(brakeStartX, bikeX - skidLen));
    setAttr("skidLine", "y1", WHEEL_Y + 28);
    setAttr("skidLine", "x2", bikeX - 45);
    setAttr("skidLine", "y2", WHEEL_Y + 28);
    setAttr("skidLine", "opacity", 0.55);

    const pulse = (Math.sin(elapsed * 12) + 1) / 2;
    const baseX = bikeX - 78;
    const baseY = WHEEL_Y + 18;

    const smokes = [
      ["smoke1", baseX - 5 - pulse*8, baseY - 10, 9 + pulse*5, .35 + pulse*.25],
      ["smoke2", baseX - 22 - pulse*12, baseY - 20, 13 + pulse*8, .22 + pulse*.20],
      ["smoke3", baseX - 40 - pulse*16, baseY - 6, 8 + pulse*7, .18 + pulse*.18],
      ["smoke4", baseX - 56 - pulse*20, baseY - 24, 10 + pulse*8, .12 + pulse*.15],
    ];
    for (const [id, cx, cy, r, op] of smokes) {{
      setAttr(id, "cx", cx);
      setAttr(id, "cy", cy);
      setAttr(id, "r", r);
      setAttr(id, "opacity", op);
    }}
  }} else {{
    setAttr("skidLine", "opacity", 0);
    for (const id of ["smoke1","smoke2","smoke3","smoke4"]) setAttr(id, "opacity", 0);
  }}

  setText("phaseText", phase);
  setText("distanceText", `현재까지 이동 거리: ${{fmt(s)}} / 현재 속력: ${{(currentSpeed*3.6).toFixed(1)}} km/h`);

  if (elapsed < duration) {{
    raf = requestAnimationFrame(animate);
  }} else {{
    setText("phaseText", "정지 완료");
    setText("distanceText", `위험 발견 후 총 정지거리: ${{fmt(DATA.totalStoppingDistance)}}`);
    setAttr("skidLine", "opacity", 0.38);
    for (const id of ["smoke1","smoke2","smoke3","smoke4"]) setAttr(id, "opacity", 0);
  }}
}}

setupMarks();
restart();
</script>
</body>
</html>
"""


def show_simulation(data: dict):
    components.html(build_simulation_html(data), height=640, scrolling=False)


# ------------------------------------------------------------
# 화면 스타일
# ------------------------------------------------------------
st.markdown(
    """
<style>
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 3rem;
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
</style>
""",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# 사이드바 입력
# ------------------------------------------------------------
st.sidebar.header("⚙️ 변수 설정")

bike_mass = st.sidebar.slider(
    "자전거 무게(kg)",
    min_value=5.0,
    max_value=20.0,
    value=9.0,
    step=0.5,
    help="이상적인 마찰 모델에서는 정지거리 계산에 직접 반영하지 않습니다.",
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
    min_value=0.2,
    max_value=2.5,
    value=1.0,
    step=0.1,
)

road_label = st.sidebar.selectbox("노면 상태", list(ROAD_OPTIONS.keys()), index=0)
mu = ROAD_OPTIONS[road_label]["mu"]

brake_label = st.sidebar.selectbox("제동 방식", list(BRAKE_OPTIONS.keys()), index=2)
k = BRAKE_OPTIONS[brake_label]["k"]

st.sidebar.divider()
st.sidebar.header("📈 그래프 보기 조절")

x_center = st.sidebar.slider(
    "x축 중심 이동",
    min_value=-80,
    max_value=100,
    value=20,
    step=5,
)

x_width = st.sidebar.slider(
    "x축 폭: 작을수록 확대",
    min_value=20,
    max_value=180,
    value=100,
    step=5,
)

y_zoom = st.sidebar.slider(
    "y축 확대",
    min_value=0.5,
    max_value=5.0,
    value=1.0,
    step=0.1,
)

y_shift = st.sidebar.slider(
    "y축 위/아래 이동",
    min_value=-100.0,
    max_value=100.0,
    value=0.0,
    step=5.0,
)

result = calc_result(speed_kmh, reaction_time, mu, k)
risk, risk_text = risk_label(result["total_stopping_distance"])

# ------------------------------------------------------------
# 헤더
# ------------------------------------------------------------
st.markdown("<div class='main-title'>🚲 픽시 자전거 정지거리와 이차함수</div>", unsafe_allow_html=True)
st.markdown(
    "<div class='main-subtitle'>속도, 반응 시간, 노면, 제동 방식이 정지거리 함수 S(x)=Ax²+Bx+0의 계수를 어떻게 바꾸는지 확인합니다.</div>",
    unsafe_allow_html=True,
)

# Streamlit 기본 metric 사용: HTML 코드가 화면에 노출되는 오류를 원천 차단
c1, c2, c3, c4 = st.columns(4)
c1.metric("반응거리", fmt_m(result["reaction_distance"]), help="위험을 발견했지만 아직 제동하지 못한 동안 이동한 거리")
c2.metric("제동거리", fmt_m(result["braking_distance"]), help="제동을 시작한 뒤 완전히 멈출 때까지 이동한 거리")
c3.metric("총 정지거리", fmt_m(result["total_stopping_distance"]), help="반응거리 + 제동거리")
c4.metric("유효 감속도", f"{result['a_eff']:.2f} m/s²", help="μ × g × k")

st.markdown(
    f"""
<div class='{"warn-box" if risk in ["위험", "매우 위험"] else "info-box"}'>
<b>현재 위험도: {html.escape(risk)}</b><br>
{html.escape(risk_text)}
</div>
""",
    unsafe_allow_html=True,
)

# ------------------------------------------------------------
# 탭
# ------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs(["📈 이차함수 그래프", "🎬 자전거 시뮬레이션", "🧮 식과 완전제곱식", "📚 이론 정리"])

with tab1:
    st.subheader("이차함수 그래프가 핵심입니다")
    st.markdown(
        """
<div class='info-box'>
실제 속도는 음수가 될 수 없으므로 <b>x ≥ 0</b> 영역을 실선으로 표시했습니다.
반면 <b>x &lt; 0</b> 영역은 수학적으로 식을 확장한 부분이므로 점선으로 표시했습니다.
왼쪽 사이드바의 그래프 조절 기능으로 확대·축소와 이동을 할 수 있습니다.
</div>
""",
        unsafe_allow_html=True,
    )

    graph_svg = build_quadratic_graph_svg(
        A=result["A"],
        B=result["B"],
        selected_x=speed_kmh,
        x_center=x_center,
        x_width=x_width,
        y_zoom=y_zoom,
        y_shift=y_shift,
    )
    show_svg(graph_svg, height=640)

    A = result["A"]
    B = result["B"]
    vx = result["vertex_x"]
    vy = result["vertex_y"]

    st.markdown(
        f"""
<div class='formula-box'>
현재 조건의 함수: S(x) = {A:.5f}x² + {B:.3f}x + 0<br>
완전제곱식: S(x) = {A:.5f}(x + {B/(2*A):.2f})² - {B*B/(4*A):.2f}
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
<div class='info-box'>
꼭짓점은 대략 <b>({vx:.2f}, {vy:.2f})</b>입니다.
하지만 이 꼭짓점은 음수 속도 영역에 있으므로 실제 자전거 운동에서는 직접 관찰되는 지점이 아닙니다.
그래도 수학적으로는 이 그래프가 포물선을 <b>왼쪽과 아래쪽으로 평행이동한 형태</b>임을 보여줍니다.
</div>
""",
        unsafe_allow_html=True,
    )

with tab2:
    st.subheader("부드러운 자전거 애니메이션")
    st.markdown(
        """
<div class='info-box'>
시뮬레이션은 <b>등속 운동 → 반응 거리 → 제동 거리</b> 순서로 진행됩니다.
제동 구간에서는 바퀴가 잠겨 회전이 멈추고, 자전거가 미끄러지며 연기와 마찰 흔적이 나타납니다.
이는 마찰력이 작용해 운동에너지가 열에너지 등으로 전환되는 과정을 시각화한 것입니다.
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
        "approachTime": float(APPROACH_DISTANCE / result["speed_ms"]) if result["speed_ms"] > 0 else 0.0,
        "reactionTime": float(result["reaction_time"]),
        "brakingTime": float(result["braking_time"]),
    }
    show_simulation(sim_data)

with tab3:
    st.subheader("정지거리 함수와 완전제곱식")

    st.markdown("### 1. 총 정지거리")
    st.latex(r"S=\text{반응거리}+\text{제동거리}")

    st.markdown("### 2. 반응거리")
    st.latex(r"\text{반응거리}=v t_r")

    st.markdown("### 3. 제동거리")
    st.latex(r"\text{제동거리}=\frac{v^2}{2\mu g k}")

    st.markdown("### 4. km/h 단위의 이차함수")
    st.latex(r"v=\frac{x}{3.6}")
    st.latex(r"S(x)=\frac{1}{25.92\mu g k}x^2+\frac{t_r}{3.6}x+0")
    st.latex(r"S(x)=Ax^2+Bx+0")

    st.markdown("### 5. 완전제곱식으로 바꾸기")
    st.latex(r"S(x)=Ax^2+Bx")
    st.latex(r"S(x)=A\left(x^2+\frac{B}{A}x\right)")
    st.latex(r"S(x)=A\left[\left(x+\frac{B}{2A}\right)^2-\left(\frac{B}{2A}\right)^2\right]")
    st.latex(r"S(x)=A\left(x+\frac{B}{2A}\right)^2-\frac{B^2}{4A}")

    st.markdown(
        f"""
<div class='formula-box'>
현재 조건<br>
A = {result["A"]:.5f}, B = {result["B"]:.3f}<br>
S(x) = {result["A"]:.5f}x² + {result["B"]:.3f}x + 0<br>
S(x) = {result["A"]:.5f}(x + {result["B"]/(2*result["A"]):.2f})² - {result["B"]*result["B"]/(4*result["A"]):.2f}
</div>
""",
        unsafe_allow_html=True,
    )

    st.markdown(
        """
<div class='info-box'>
이 식은 수학 시간의 이차함수와 똑같은 구조입니다.
다만 실제 운동에서는 속도 x가 음수가 될 수 없으므로, 물리적으로 의미 있는 부분은 x ≥ 0인 오른쪽 구간입니다.
음수 속도 영역은 그래프의 전체 모양과 평행이동을 이해하기 위한 수학적 확장입니다.
</div>
""",
        unsafe_allow_html=True,
    )

with tab4:
    st.subheader("이론 정리")

    st.markdown("## 1. 운동에너지")
    st.markdown(
        """
자전거가 빠르게 달릴수록 더 큰 운동에너지를 가집니다.
운동에너지는 속도의 제곱에 비례합니다.
"""
    )
    st.latex(r"E_k=\frac{1}{2}mv^2")

    st.markdown("## 2. 마찰력과 일")
    st.markdown(
        """
제동할 때 타이어와 노면 사이의 마찰력이 자전거의 운동을 방해합니다.
마찰력이 이동 방향과 반대로 작용하면서 일을 하고, 그 결과 자전거의 운동에너지가 줄어듭니다.
"""
    )
    st.latex(r"W=Fd")
    st.latex(r"F_{\text{마찰}}\approx \mu mgk")

    st.markdown("## 3. 에너지 전환과 보존")
    st.markdown(
        """
제동 중 자전거의 운동에너지는 사라지는 것이 아니라 주로 열에너지, 소리, 타이어와 노면의 변형 등으로 전환됩니다.
시뮬레이션에서 제동 구간의 연기와 미끄럼 흔적은 이 과정을 눈에 보이게 표현한 것입니다.
"""
    )
    st.latex(r"\frac{1}{2}mv^2=\mu mgk \cdot d")

    st.markdown("## 4. 질량이 약분되는 이유")
    st.markdown(
        """
위 식을 정리하면 질량 m이 양쪽에서 약분됩니다.
그래서 이 단순 모델에서는 자전거 무게를 바꾸어도 정지거리가 직접 변하지 않습니다.
"""
    )
    st.latex(r"d=\frac{v^2}{2\mu gk}")

    st.markdown("## 5. 정지거리가 이차함수가 되는 이유")
    st.markdown(
        """
총 정지거리는 반응거리와 제동거리의 합입니다.
반응거리는 속도에 비례하므로 일차항이 되고, 제동거리는 속도의 제곱에 비례하므로 이차항이 됩니다.
"""
    )
    st.latex(r"S(v)=vt_r+\frac{v^2}{2\mu gk}")

    st.markdown("## 6. km/h 단위로 바꾼 이차함수")
    st.markdown(
        """
앱에서는 학생들이 익숙한 km/h를 사용합니다.
초기 속도를 x km/h라고 하면, m/s 단위 속도는 x/3.6입니다.
"""
    )
    st.latex(r"S(x)=\frac{1}{25.92\mu gk}x^2+\frac{t_r}{3.6}x+0")

    st.markdown("## 7. 이차함수의 평행이동")
    st.markdown(
        """
현재 식은 S(x)=Ax²+Bx+0 꼴입니다.
완전제곱식으로 바꾸면 그래프가 기본 포물선 y=Ax²를 평행이동한 형태임을 알 수 있습니다.
"""
    )
    st.latex(r"S(x)=A\left(x+\frac{B}{2A}\right)^2-\frac{B^2}{4A}")

    st.markdown(
        """
<div class='info-box'>
정리하면, 픽시 자전거의 위험성은 속도가 조금 증가할 때 정지거리가 단순히 조금 늘어나는 정도가 아니라,
제동거리 항 때문에 <b>제곱에 가깝게 빠르게 증가한다</b>는 데 있습니다.
특히 노면 마찰계수 μ가 작거나 제동 효율 k가 작으면 이차항의 계수 A가 커져 그래프가 더 가파르게 올라갑니다.
</div>
""",
        unsafe_allow_html=True,
    )

st.markdown("---")
st.markdown(
    f"""
<div class='small-caption'>
모델 가정: 공기저항 무시, 평지, 반응 시간 동안 등속 운동, 제동 중 일정한 감속도, 노면 상태를 하나의 마찰계수 μ로 단순화.
자전거 무게 {bike_mass:.1f} kg은 탐구용 변수로 표시하지만, 이상적인 마찰 모델의 정지거리 계산에는 직접 반영하지 않음.
</div>
""",
    unsafe_allow_html=True,
)
