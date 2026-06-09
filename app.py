# app.py
# 중학교 2학년 과학: 겉보기 등급과 절대등급을 직관적으로 배우는 앱
# 핵심 활동: 별의 실제 밝기와 거리를 조작하고, 10 pc 위치로 옮겨 절대등급을 확인한다.
# 선택 활동: Gaia Archive TAP API에서 실제 별 자료를 불러와 확인한다.

import io
import math
import requests
import numpy as np
import pandas as pd
import streamlit as st


# ------------------------------------------------------------
# 기본 설정
# ------------------------------------------------------------
st.set_page_config(
    page_title="보이는 밝기와 실제 밝기",
    page_icon="⭐",
    layout="wide"
)

GAIA_TAP_SYNC_URL = "https://gea.esac.esa.int/tap-server/tap/sync"
M_SUN = 4.83  # 태양의 절대등급에 가까운 참고값. 수업용 기준값으로 사용.


# ------------------------------------------------------------
# 세션 상태 기본값
# ------------------------------------------------------------
DISTANCE_OPTIONS = [1, 2, 3, 5, 7, 10, 15, 20, 30, 50, 70, 100, 150, 200, 300, 500, 700, 1000]
LUMINOSITY_OPTIONS = [0.01, 0.03, 0.1, 0.3, 1, 3, 10, 30, 100, 300, 1000]

DEFAULTS = {
    "a_distance": 5,
    "a_luminosity": 0.3,
    "b_distance": 100,
    "b_luminosity": 100,
    "view_mode": "apparent"
}

for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ------------------------------------------------------------
# 계산 함수
# ------------------------------------------------------------
def nearest_value(options, value):
    """주어진 값과 가장 가까운 선택지 값을 반환한다."""
    return min(options, key=lambda x: abs(x - value))


def parallax_mas(distance_pc):
    """거리 pc를 연주시차 mas로 바꾼다."""
    return 1000 / distance_pc


def absolute_magnitude(luminosity):
    """
    실제 밝기 비율을 절대등급으로 바꾼다.
    luminosity = 1이면 태양과 비슷한 실제 밝기라고 생각한다.
    """
    return M_SUN - 2.5 * math.log10(luminosity)


def apparent_magnitude(abs_mag, distance_pc):
    """
    절대등급과 거리로 겉보기 등급을 계산한다.
    거리가 10 pc이면 겉보기 등급 = 절대등급이다.
    """
    return abs_mag + 5 * math.log10(distance_pc / 10)


def brightness_ratio_from_mag(mag1, mag2):
    """등급 차이를 밝기 비율로 바꾼다."""
    return 10 ** (abs(mag1 - mag2) / 2.5)


def compare_mag(mag_a, mag_b, name_a="별 A", name_b="별 B"):
    """
    등급 숫자가 작을수록 밝다.
    어느 별이 더 밝은지 설명 문장을 만든다.
    """
    if abs(mag_a - mag_b) < 0.05:
        return "거의 같음", f"{name_a}와 {name_b}의 밝기는 거의 비슷합니다."

    ratio = brightness_ratio_from_mag(mag_a, mag_b)

    if mag_a < mag_b:
        return name_a, f"{name_a}가 {name_b}보다 약 {ratio:.1f}배 밝습니다."
    else:
        return name_b, f"{name_b}가 {name_a}보다 약 {ratio:.1f}배 밝습니다."


def log_position(distance_pc):
    """
    화면에서 별의 가로 위치를 정한다.
    거리는 1~1000 pc 범위에서 로그 스케일처럼 배치한다.
    """
    distance_pc = max(1, min(1000, distance_pc))
    return 8 + 84 * (math.log10(distance_pc) / 3)


def visual_style(flux, max_flux):
    """
    밝기 값을 화면에서 보일 별 크기와 빛 번짐으로 바꾼다.
    flux가 매우 작아도 별이 완전히 사라지지 않도록 최소 크기를 둔다.
    """
    if max_flux <= 0:
        ratio = 0.1
    else:
        ratio = math.sqrt(max(flux / max_flux, 0.001))

    size = 22 + 62 * ratio
    glow = 8 + 36 * ratio
    opacity = 0.35 + 0.65 * ratio

    return size, glow, opacity


def make_star_data(distance, luminosity):
    """별 하나의 수업용 물리량을 딕셔너리로 정리한다."""
    M = absolute_magnitude(luminosity)
    m = apparent_magnitude(M, distance)

    return {
        "distance": distance,
        "luminosity": luminosity,
        "parallax": parallax_mas(distance),
        "absolute_mag": M,
        "apparent_mag": m,
        "apparent_flux": luminosity / (distance ** 2),
        "absolute_flux": luminosity / (10 ** 2),
    }


# ------------------------------------------------------------
# CSS 애니메이션 장면 만들기
# ------------------------------------------------------------
def render_space_scene(star_a, star_b, mode):
    """
    별이 지구에서 떨어진 위치에 있을 때와,
    두 별을 10 pc 위치로 옮겼을 때를 CSS 애니메이션으로 보여준다.
    """

    pos_a = log_position(star_a["distance"])
    pos_b = log_position(star_b["distance"])
    pos_10 = log_position(10)

    if mode == "absolute":
        flux_a = star_a["absolute_flux"]
        flux_b = star_b["absolute_flux"]
        title = "🚀 절대등급 모드: 두 별을 모두 10 pc 위치로 옮기는 중"
        sub = "거리 조건을 같게 만들면, 별 자체가 얼마나 밝은지 비교할 수 있습니다."
        animation_a = f"moveA 2.3s ease-in-out forwards"
        animation_b = f"moveB 2.3s ease-in-out forwards"
        final_label = "10 pc 기준"
    else:
        flux_a = star_a["apparent_flux"]
        flux_b = star_b["apparent_flux"]
        title = "👀 겉보기 모드: 지구에서 바라본 별"
        sub = "가까운 별은 실제로 어두워도 밝게 보일 수 있습니다."
        animation_a = "none"
        animation_b = "none"
        final_label = "현재 거리"

    max_flux = max(flux_a, flux_b)
    size_a, glow_a, opacity_a = visual_style(flux_a, max_flux)
    size_b, glow_b, opacity_b = visual_style(flux_b, max_flux)

    html = f"""
    <style>
    .space-wrap {{
        width: 100%;
        min-height: 440px;
        border-radius: 28px;
        background:
            radial-gradient(circle at 20% 20%, rgba(255,255,255,0.22), transparent 2px),
            radial-gradient(circle at 80% 25%, rgba(255,255,255,0.18), transparent 2px),
            radial-gradient(circle at 50% 70%, rgba(255,255,255,0.16), transparent 2px),
            linear-gradient(135deg, #090a2a 0%, #12194a 45%, #241145 100%);
        position: relative;
        overflow: hidden;
        box-shadow: 0 18px 45px rgba(15, 23, 42, 0.25);
        color: white;
        font-family: 'Noto Sans KR', sans-serif;
    }}

    .scene-title {{
        position: absolute;
        top: 22px;
        left: 28px;
        font-size: 24px;
        font-weight: 900;
    }}

    .scene-sub {{
        position: absolute;
        top: 60px;
        left: 30px;
        font-size: 15px;
        color: #dbeafe;
    }}

    .earth {{
        position: absolute;
        left: 4%;
        top: 53%;
        transform: translate(-50%, -50%);
        font-size: 46px;
        text-align: center;
        filter: drop-shadow(0 0 12px #60a5fa);
    }}

    .earth span {{
        display: block;
        font-size: 13px;
        margin-top: 6px;
        color: #bfdbfe;
        font-weight: 700;
    }}

    .track {{
        position: absolute;
        left: 6%;
        right: 5%;
        top: 52%;
        height: 3px;
        background: linear-gradient(90deg, rgba(147,197,253,0.65), rgba(255,255,255,0.1));
        border-radius: 999px;
    }}

    .marker10 {{
        position: absolute;
        left: {pos_10}%;
        top: 22%;
        height: 64%;
        width: 2px;
        border-left: 2px dashed rgba(251, 191, 36, 0.9);
    }}

    .marker10-label {{
        position: absolute;
        left: {pos_10}%;
        top: 18%;
        transform: translateX(-50%);
        background: rgba(251, 191, 36, 0.18);
        border: 1px solid rgba(251, 191, 36, 0.75);
        color: #fde68a;
        padding: 7px 11px;
        border-radius: 999px;
        font-size: 13px;
        font-weight: 800;
        white-space: nowrap;
    }}

    .star {{
        position: absolute;
        transform: translate(-50%, -50%);
        line-height: 1;
        font-weight: 900;
        z-index: 5;
    }}

    .star-a {{
        left: {pos_a}%;
        top: 41%;
        font-size: {size_a}px;
        color: #fef3c7;
        opacity: {opacity_a};
        text-shadow: 0 0 {glow_a}px #facc15, 0 0 {glow_a * 1.8}px #fb923c;
        animation: {animation_a};
    }}

    .star-b {{
        left: {pos_b}%;
        top: 67%;
        font-size: {size_b}px;
        color: #dbeafe;
        opacity: {opacity_b};
        text-shadow: 0 0 {glow_b}px #60a5fa, 0 0 {glow_b * 1.8}px #818cf8;
        animation: {animation_b};
    }}

    .star-label {{
        position: absolute;
        transform: translate(-50%, -50%);
        font-size: 13px;
        font-weight: 800;
        background: rgba(15,23,42,0.72);
        border: 1px solid rgba(255,255,255,0.25);
        padding: 5px 9px;
        border-radius: 999px;
        white-space: nowrap;
    }}

    .label-a {{
        left: {pos_a}%;
        top: 30%;
        animation: {"labelMoveA 2.3s ease-in-out forwards" if mode == "absolute" else "none"};
    }}

    .label-b {{
        left: {pos_b}%;
        top: 78%;
        animation: {"labelMoveB 2.3s ease-in-out forwards" if mode == "absolute" else "none"};
    }}

    .bottom-note {{
        position: absolute;
        left: 24px;
        right: 24px;
        bottom: 20px;
        background: rgba(15, 23, 42, 0.65);
        border: 1px solid rgba(255,255,255,0.16);
        border-radius: 18px;
        padding: 13px 16px;
        font-size: 15px;
        color: #e0f2fe;
    }}

    @keyframes moveA {{
        0% {{ left: {pos_a}%; transform: translate(-50%, -50%) scale(0.75); }}
        65% {{ transform: translate(-50%, -50%) scale(1.2); }}
        100% {{ left: {pos_10}%; transform: translate(-50%, -50%) scale(1); }}
    }}

    @keyframes moveB {{
        0% {{ left: {pos_b}%; transform: translate(-50%, -50%) scale(0.75); }}
        65% {{ transform: translate(-50%, -50%) scale(1.2); }}
        100% {{ left: {pos_10}%; transform: translate(-50%, -50%) scale(1); }}
    }}

    @keyframes labelMoveA {{
        0% {{ left: {pos_a}%; }}
        100% {{ left: {pos_10}%; }}
    }}

    @keyframes labelMoveB {{
        0% {{ left: {pos_b}%; }}
        100% {{ left: {pos_10}%; }}
    }}
    </style>

    <div class="space-wrap">
        <div class="scene-title">{title}</div>
        <div class="scene-sub">{sub}</div>

        <div class="track"></div>
        <div class="earth">🌍<span>지구</span></div>

        <div class="marker10"></div>
        <div class="marker10-label">10 pc 위치<br>{final_label}</div>

        <div class="star star-a">★</div>
        <div class="star star-b">★</div>

        <div class="star-label label-a">별 A</div>
        <div class="star-label label-b">별 B</div>

        <div class="bottom-note">
            겉보기 등급은 <b>지구에서 보이는 밝기</b>입니다.
            절대등급은 별을 모두 <b>10 pc 위치에 둔다고 가정했을 때의 밝기</b>입니다.
        </div>
    </div>
    """

    st.html(html)


# ------------------------------------------------------------
# Gaia 자료 불러오기
# ------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def load_gaia_data():
    """
    Gaia Archive TAP API에서 실제 별 자료를 불러온다.
    이 앱에서는 개념 학습이 핵심이므로 너무 많은 자료를 가져오지 않는다.
    """

    query = """
    SELECT TOP 80
        source_id,
        ra,
        dec,
        parallax,
        parallax_error,
        phot_g_mean_mag,
        bp_rp
    FROM gaiadr3.gaia_source_lite
    WHERE
        parallax IS NOT NULL
        AND parallax > 1
        AND parallax_error IS NOT NULL
        AND parallax / parallax_error > 20
        AND phot_g_mean_mag IS NOT NULL
        AND phot_g_mean_mag < 12
    ORDER BY phot_g_mean_mag ASC
    """

    payload = {
        "REQUEST": "doQuery",
        "LANG": "ADQL",
        "FORMAT": "csv",
        "QUERY": query
    }

    response = requests.post(GAIA_TAP_SYNC_URL, data=payload, timeout=60)
    response.raise_for_status()

    text = response.text.strip()

    if text.startswith("<"):
        raise RuntimeError("Gaia Archive에서 CSV가 아닌 응답을 받았습니다.")

    df = pd.read_csv(io.StringIO(text))
    df.columns = [c.lower().strip() for c in df.columns]

    for col in ["ra", "dec", "parallax", "parallax_error", "phot_g_mean_mag", "bp_rp"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["parallax", "phot_g_mean_mag"])
    df = df[df["parallax"] > 0].copy()

    df["distance_pc"] = 1000 / df["parallax"]
    df["absolute_g_mag"] = df["phot_g_mean_mag"] + 5 - 5 * np.log10(df["distance_pc"])

    # 절대등급을 태양 기준 실제 밝기 비율로 대략 변환한다.
    df["luminosity_like"] = 10 ** ((M_SUN - df["absolute_g_mag"]) / 2.5)

    df = df.reset_index(drop=True)
    df["번호"] = df.index + 1

    return df


# ------------------------------------------------------------
# 메인 화면
# ------------------------------------------------------------
st.title("⭐ 보이는 밝기와 실제 밝기는 왜 다를까?")
st.caption("중학교 2학년 과학 · 연주시차 · 겉보기 등급 · 절대등급 탐구")

st.markdown(
    """
    이 앱은 별을 직접 움직여 보는 방식으로 구성했습니다.  
    학생은 별의 **실제 밝기**와 **거리**를 조작하고, 지구에서 보이는 밝기가 어떻게 바뀌는지 확인합니다.  
    그다음 두 별을 모두 **10 pc 위치**로 옮겨서 절대등급의 의미를 확인합니다.
    """
)

tab1, tab2, tab3 = st.tabs(["🌌 조작 실험실", "🎯 미션 활동", "🔭 실제 Gaia 자료"])


# ------------------------------------------------------------
# 탭 1: 조작 실험실
# ------------------------------------------------------------
with tab1:
    st.subheader("1. 별의 실제 밝기와 거리를 직접 조작해 보세요")

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("### 🟡 별 A")
        st.select_slider(
            "별 A의 거리(pc)",
            options=DISTANCE_OPTIONS,
            key="a_distance"
        )
        st.select_slider(
            "별 A의 실제 밝기",
            options=LUMINOSITY_OPTIONS,
            key="a_luminosity",
            help="1이면 태양과 비슷한 실제 밝기라고 생각합니다."
        )

    with col_b:
        st.markdown("### 🔵 별 B")
        st.select_slider(
            "별 B의 거리(pc)",
            options=DISTANCE_OPTIONS,
            key="b_distance"
        )
        st.select_slider(
            "별 B의 실제 밝기",
            options=LUMINOSITY_OPTIONS,
            key="b_luminosity",
            help="1이면 태양과 비슷한 실제 밝기라고 생각합니다."
        )

    star_a = make_star_data(st.session_state.a_distance, st.session_state.a_luminosity)
    star_b = make_star_data(st.session_state.b_distance, st.session_state.b_luminosity)

    st.divider()

    c1, c2, c3 = st.columns([1, 1, 2])

    with c1:
        if st.button("👀 지구에서 보기", use_container_width=True):
            st.session_state.view_mode = "apparent"

    with c2:
        if st.button("🚀 10 pc로 옮겨 보기", use_container_width=True):
            st.session_state.view_mode = "absolute"

    with c3:
        st.info(
            "먼저 지구에서 본 뒤, 10 pc로 옮겨 보세요. "
            "겉보기 등급과 절대등급의 차이가 훨씬 직관적으로 보입니다."
        )

    render_space_scene(star_a, star_b, st.session_state.view_mode)

    st.divider()

    st.subheader("2. 계산값 확인하기")

    result_col1, result_col2 = st.columns(2)

    with result_col1:
        st.markdown("### 🟡 별 A")
        st.metric("거리", f"{star_a['distance']} pc")
        st.metric("연주시차", f"{star_a['parallax']:.1f} mas")
        st.metric("겉보기 등급", f"{star_a['apparent_mag']:.2f}")
        st.metric("절대등급", f"{star_a['absolute_mag']:.2f}")

    with result_col2:
        st.markdown("### 🔵 별 B")
        st.metric("거리", f"{star_b['distance']} pc")
        st.metric("연주시차", f"{star_b['parallax']:.1f} mas")
        st.metric("겉보기 등급", f"{star_b['apparent_mag']:.2f}")
        st.metric("절대등급", f"{star_b['absolute_mag']:.2f}")

    apparent_winner, apparent_text = compare_mag(
        star_a["apparent_mag"],
        star_b["apparent_mag"],
        "별 A",
        "별 B"
    )

    absolute_winner, absolute_text = compare_mag(
        star_a["absolute_mag"],
        star_b["absolute_mag"],
        "별 A",
        "별 B"
    )

    st.divider()

    st.subheader("3. 해석하기")

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("### 👀 겉보기 등급")
        st.write(apparent_text)
        st.caption("겉보기 등급은 지구에서 보이는 밝기입니다.")

    with col_right:
        st.markdown("### 💡 절대등급")
        st.write(absolute_text)
        st.caption("절대등급은 별을 10 pc에 두었다고 생각했을 때의 등급입니다.")

    if apparent_winner != absolute_winner and apparent_winner != "거의 같음" and absolute_winner != "거의 같음":
        st.success(
            f"핵심 발견: 겉보기로는 {apparent_winner}가 더 밝지만, "
            f"10 pc에서 비교하면 {absolute_winner}가 더 밝습니다. "
            "즉, 보이는 밝기와 실제 밝기는 다를 수 있습니다."
        )
    else:
        st.warning(
            "이번 설정에서는 겉보기 밝기 순서와 실제 밝기 순서가 크게 뒤집히지 않았습니다. "
            "거리와 실제 밝기를 더 극단적으로 바꿔 보세요."
        )


# ------------------------------------------------------------
# 탭 2: 미션 활동
# ------------------------------------------------------------
with tab2:
    st.subheader("🎯 학생 미션")

    st.markdown(
        """
        ### 미션 1. 가까워서 밝게 보이는 별 만들기
        - 별 A의 실제 밝기를 작게 만든다.
        - 별 A의 거리를 아주 가깝게 만든다.
        - 별 A가 실제로는 어두운데도 지구에서는 밝게 보이는지 확인한다.

        ### 미션 2. 멀지만 실제로 매우 밝은 별 만들기
        - 별 B의 실제 밝기를 크게 만든다.
        - 별 B의 거리를 멀게 만든다.
        - 지구에서는 생각보다 어둡게 보일 수 있는지 확인한다.

        ### 미션 3. 밝기 순서 뒤집기
        아래 문장이 나오도록 조작해 보세요.

        > 겉보기로는 별 A가 더 밝지만, 절대등급으로는 별 B가 더 밝다.

        또는 반대로,

        > 겉보기로는 별 B가 더 밝지만, 절대등급으로는 별 A가 더 밝다.
        """
    )

    st.divider()

    st.subheader("✍️ 학생 기록 문장")

    st.markdown(
        """
        학생들에게 아래 문장을 완성하게 하면 좋습니다.

        1. 연주시차가 큰 별은 거리가 ________ 별이다.
        2. 겉보기 등급은 ________에서 보이는 밝기를 나타낸다.
        3. 절대등급은 별을 모두 ________ pc에 두었다고 생각했을 때의 밝기이다.
        4. 별이 밝게 보인다고 해서 반드시 실제로 밝은 것은 아니다. 왜냐하면 ________ 때문이다.
        """
    )

    st.info(
        "수업에서는 수식보다 먼저 화면 조작을 시키는 것이 좋습니다. "
        "학생이 먼저 '가까우면 밝게 보인다'를 발견한 뒤, 그다음 절대등급을 설명하면 이해가 훨씬 쉽습니다."
    )


# ------------------------------------------------------------
# 탭 3: 실제 Gaia 자료
# ------------------------------------------------------------
with tab3:
    st.subheader("🔭 실제 Gaia 자료로 확인하기")

    st.markdown(
        """
        이 탭은 실제 별 자료를 확인하는 보조 활동입니다.  
        처음부터 실제 데이터로 들어가면 개념이 흐려질 수 있으므로, 먼저 조작 실험실에서 개념을 잡은 뒤 사용하세요.
        """
    )

    try:
        with st.spinner("Gaia Archive에서 별 자료를 불러오는 중입니다..."):
            gaia_df = load_gaia_data()

        st.success(f"Gaia 실제 별 자료 {len(gaia_df)}개를 불러왔습니다.")

        def gaia_label(row):
            return (
                f"{int(row['번호'])}번 | Gaia {int(row['source_id'])} | "
                f"거리 {row['distance_pc']:.1f} pc | "
                f"겉보기 G {row['phot_g_mean_mag']:.2f} | "
                f"절대 G {row['absolute_g_mag']:.2f}"
            )

        labels = [gaia_label(row) for _, row in gaia_df.iterrows()]
        label_to_idx = {label: i for i, label in enumerate(labels)}

        gcol1, gcol2 = st.columns(2)

        with gcol1:
            selected_gaia_a = st.selectbox("실제 별 A", labels, index=0)

        with gcol2:
            selected_gaia_b = st.selectbox("실제 별 B", labels, index=1)

        gaia_a = gaia_df.iloc[label_to_idx[selected_gaia_a]]
        gaia_b = gaia_df.iloc[label_to_idx[selected_gaia_b]]

        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "구분": "실제 별 A",
                        "Gaia source_id": int(gaia_a["source_id"]),
                        "연주시차(mas)": round(gaia_a["parallax"], 3),
                        "거리(pc)": round(gaia_a["distance_pc"], 2),
                        "겉보기 등급 G": round(gaia_a["phot_g_mean_mag"], 2),
                        "절대등급 G": round(gaia_a["absolute_g_mag"], 2),
                    },
                    {
                        "구분": "실제 별 B",
                        "Gaia source_id": int(gaia_b["source_id"]),
                        "연주시차(mas)": round(gaia_b["parallax"], 3),
                        "거리(pc)": round(gaia_b["distance_pc"], 2),
                        "겉보기 등급 G": round(gaia_b["phot_g_mean_mag"], 2),
                        "절대등급 G": round(gaia_b["absolute_g_mag"], 2),
                    }
                ]
            ),
            use_container_width=True,
            hide_index=True
        )

        gaia_app_winner, gaia_app_text = compare_mag(
            gaia_a["phot_g_mean_mag"],
            gaia_b["phot_g_mean_mag"],
            "실제 별 A",
            "실제 별 B"
        )

        gaia_abs_winner, gaia_abs_text = compare_mag(
            gaia_a["absolute_g_mag"],
            gaia_b["absolute_g_mag"],
            "실제 별 A",
            "실제 별 B"
        )

        st.write("👀 겉보기 등급 비교:", gaia_app_text)
        st.write("💡 절대등급 비교:", gaia_abs_text)

        if st.button("선택한 Gaia 별을 조작 실험실로 가져오기"):
            st.session_state.a_distance = nearest_value(DISTANCE_OPTIONS, float(gaia_a["distance_pc"]))
            st.session_state.b_distance = nearest_value(DISTANCE_OPTIONS, float(gaia_b["distance_pc"]))

            st.session_state.a_luminosity = nearest_value(
                LUMINOSITY_OPTIONS,
                float(gaia_a["luminosity_like"])
            )
            st.session_state.b_luminosity = nearest_value(
                LUMINOSITY_OPTIONS,
                float(gaia_b["luminosity_like"])
            )

            st.session_state.view_mode = "apparent"
            st.rerun()

    except Exception as e:
        st.error("Gaia Archive 자료를 불러오지 못했습니다.")
        st.code(str(e))
        st.info(
            "인터넷 연결 또는 Gaia 서버 상태에 따라 일시적으로 실패할 수 있습니다. "
            "그래도 조작 실험실 탭은 Gaia 연결 없이 사용할 수 있습니다."
        )
