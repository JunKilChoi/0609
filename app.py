# app.py
# 중학교 2학년 과학: 연주시차, 겉보기 등급, 절대등급 탐구 앱
# 데이터 출처: ESA Gaia Archive TAP API
# 실행: streamlit run app.py

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
    page_title="별의 거리와 밝기 탐구",
    page_icon="⭐",
    layout="wide"
)

GAIA_TAP_SYNC_URL = "https://gea.esac.esa.int/tap-server/tap/sync"


# ------------------------------------------------------------
# 화면 디자인 CSS
# ------------------------------------------------------------
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 900;
        background: linear-gradient(90deg, #3b82f6, #a855f7, #ec4899);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-box {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 16px 18px;
        margin-bottom: 16px;
    }
    .key-box {
        background: #fff7ed;
        border: 1px solid #fed7aa;
        border-radius: 16px;
        padding: 16px 18px;
        margin-top: 12px;
        margin-bottom: 12px;
    }
    .result-box {
        background: #eef2ff;
        border: 1px solid #c7d2fe;
        border-radius: 16px;
        padding: 16px 18px;
        margin-top: 10px;
        margin-bottom: 10px;
    }
    .small-text {
        color: #475569;
        font-size: 0.92rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# ------------------------------------------------------------
# Gaia TAP API 요청 함수
# ------------------------------------------------------------
def make_adql_query(table_name, top_n, min_parallax, max_gmag, snr_limit, order_by):
    """
    Gaia Archive에 보낼 ADQL 쿼리를 만든다.
    - parallax: 연주시차, 단위는 mas(밀리초각)
    - phot_g_mean_mag: Gaia G밴드 겉보기 등급
    - parallax_error: 연주시차 오차
    """

    query = f"""
    SELECT TOP {top_n}
        source_id,
        ra,
        dec,
        parallax,
        parallax_error,
        phot_g_mean_mag,
        bp_rp
    FROM {table_name}
    WHERE
        parallax IS NOT NULL
        AND parallax > {min_parallax}
        AND parallax_error IS NOT NULL
        AND parallax / parallax_error > {snr_limit}
        AND phot_g_mean_mag IS NOT NULL
        AND phot_g_mean_mag <= {max_gmag}
    ORDER BY {order_by}
    """
    return query


def request_gaia_csv(adql_query):
    """
    ESA Gaia Archive TAP sync endpoint에 ADQL 쿼리를 보내고 CSV로 받는다.
    Streamlit Cloud에서 별도 인증 없이 requests만으로 작동하도록 구성했다.
    """

    payload = {
        "REQUEST": "doQuery",
        "LANG": "ADQL",
        "FORMAT": "csv",
        "QUERY": adql_query
    }

    response = requests.post(
        GAIA_TAP_SYNC_URL,
        data=payload,
        timeout=60
    )

    response.raise_for_status()
    text = response.text.strip()

    # 오류가 XML/VOTable 형태로 올 수 있으므로 간단히 감지한다.
    if text.startswith("<"):
        raise RuntimeError("Gaia Archive에서 CSV가 아닌 응답을 받았습니다. 쿼리 오류일 가능성이 있습니다.")

    df = pd.read_csv(io.StringIO(text))
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def add_derived_columns(df):
    """
    연주시차와 겉보기 등급으로부터 수업용 계산값을 추가한다.

    거리(pc) = 1000 / 연주시차(mas)
    절대등급 = 겉보기등급 - 5 log10(거리/10)
             = 겉보기등급 + 5 - 5 log10(거리)
    """

    numeric_cols = ["ra", "dec", "parallax", "parallax_error", "phot_g_mean_mag", "bp_rp"]

    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["parallax", "phot_g_mean_mag"])
    df = df[df["parallax"] > 0].copy()

    df["distance_pc"] = 1000 / df["parallax"]
    df["distance_ly"] = df["distance_pc"] * 3.26156
    df["absolute_g_mag"] = df["phot_g_mean_mag"] + 5 - 5 * np.log10(df["distance_pc"])

    # 겉보기 밝기 지수와 실제 밝기 지수
    # 등급은 숫자가 작을수록 밝으므로, 밝기 지수는 10^(-0.4 * 등급)으로 바꾼다.
    df["apparent_brightness_index"] = 10 ** (-0.4 * df["phot_g_mean_mag"])
    df["intrinsic_brightness_index"] = 10 ** (-0.4 * df["absolute_g_mag"])

    df = df.reset_index(drop=True)
    df["star_no"] = df.index + 1

    return df


def fallback_demo_data():
    """
    API 연결이 실패했을 때 앱 구조를 확인할 수 있도록 넣어둔 예시 자료.
    실제 Gaia 자료가 아니므로 화면에 경고를 띄운다.
    """

    demo = pd.DataFrame(
        [
            {
                "source_id": "DEMO_NEAR_DIM",
                "ra": 10.0,
                "dec": 5.0,
                "parallax": 200.0,
                "parallax_error": 1.0,
                "phot_g_mean_mag": 9.5,
                "bp_rp": 1.8
            },
            {
                "source_id": "DEMO_FAR_BRIGHT",
                "ra": 120.0,
                "dec": -20.0,
                "parallax": 5.0,
                "parallax_error": 0.1,
                "phot_g_mean_mag": 4.0,
                "bp_rp": 0.1
            },
            {
                "source_id": "DEMO_MIDDLE",
                "ra": 240.0,
                "dec": 40.0,
                "parallax": 25.0,
                "parallax_error": 0.5,
                "phot_g_mean_mag": 7.0,
                "bp_rp": 0.9
            },
        ]
    )

    return add_derived_columns(demo)


@st.cache_data(ttl=3600, show_spinner=False)
def load_gaia_data(top_n, min_parallax, max_gmag, snr_limit, order_kind):
    """
    Gaia 자료를 불러온다.
    먼저 빠른 조회용 gaia_source_lite를 시도하고,
    실패하면 기본 gaia_source 테이블을 다시 시도한다.
    """

    top_n = int(top_n)
    min_parallax = float(min_parallax)
    max_gmag = float(max_gmag)
    snr_limit = float(snr_limit)

    order_map = {
        "겉보기로 밝은 별 우선": "phot_g_mean_mag ASC",
        "가까운 별 우선": "parallax DESC",
        "연주시차가 비슷하지 않게 보기": "parallax ASC"
    }
    order_by = order_map.get(order_kind, "phot_g_mean_mag ASC")

    candidate_tables = [
        "gaiadr3.gaia_source_lite",
        "gaiadr3.gaia_source"
    ]

    last_error = None

    for table_name in candidate_tables:
        try:
            query = make_adql_query(
                table_name=table_name,
                top_n=top_n,
                min_parallax=min_parallax,
                max_gmag=max_gmag,
                snr_limit=snr_limit,
                order_by=order_by
            )
            raw_df = request_gaia_csv(query)
            df = add_derived_columns(raw_df)

            if len(df) >= 2:
                return df, False, table_name

        except Exception as e:
            last_error = e

    # 여기까지 오면 API 조회에 실패한 것
    demo_df = fallback_demo_data()
    return demo_df, True, f"API 조회 실패: {last_error}"


# ------------------------------------------------------------
# 비교 계산 함수
# ------------------------------------------------------------
def magnitude_ratio(mag1, mag2):
    """
    등급 차이로 밝기 비율을 계산한다.
    등급 차이가 1이면 밝기는 약 2.512배 차이난다.
    """

    return 10 ** (abs(mag1 - mag2) / 2.5)


def compare_magnitude(mag_a, mag_b, label_a="별 A", label_b="별 B"):
    """
    등급은 숫자가 작을수록 밝다.
    두 별 중 어느 쪽이 밝은지와 몇 배 밝은지를 반환한다.
    """

    ratio = magnitude_ratio(mag_a, mag_b)

    if abs(mag_a - mag_b) < 0.01:
        return "거의 같음", 1.0, "두 별의 밝기는 거의 비슷합니다."

    if mag_a < mag_b:
        return label_a, ratio, f"{label_a}가 {label_b}보다 약 {ratio:.2f}배 밝습니다."
    else:
        return label_b, ratio, f"{label_b}가 {label_a}보다 약 {ratio:.2f}배 밝습니다."


def make_star_label(row):
    """
    선택 상자에 표시할 별 이름을 만든다.
    Gaia에는 일상적인 별 이름이 없는 경우가 많으므로 source_id를 사용한다.
    """

    source_id = str(row["source_id"])
    return (
        f"{int(row['star_no'])}번 | Gaia {source_id} | "
        f"연주시차 {row['parallax']:.2f} mas | "
        f"거리 {row['distance_pc']:.1f} pc | "
        f"G {row['phot_g_mean_mag']:.2f}"
    )


def show_star_metrics(row, title):
    """
    별 하나의 핵심 관측값과 계산값을 보여준다.
    """

    st.markdown(f"### {title}")
    st.metric("연주시차", f"{row['parallax']:.2f} mas")
    st.metric("거리", f"{row['distance_pc']:.1f} pc")
    st.metric("겉보기 등급 G", f"{row['phot_g_mean_mag']:.2f}")
    st.metric("절대등급 M_G", f"{row['absolute_g_mag']:.2f}")


# ------------------------------------------------------------
# 사이드바 입력
# ------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Gaia 자료 설정")

    order_kind = st.selectbox(
        "별 후보 정렬 방식",
        ["겉보기로 밝은 별 우선", "가까운 별 우선", "연주시차가 비슷하지 않게 보기"]
    )

    top_n = st.slider(
        "가져올 별 후보 수",
        min_value=50,
        max_value=500,
        value=200,
        step=50
    )

    min_parallax = st.slider(
        "최소 연주시차(mas)",
        min_value=1.0,
        max_value=50.0,
        value=5.0,
        step=1.0
    )

    max_gmag = st.slider(
        "가장 어두운 겉보기 등급 G",
        min_value=5.0,
        max_value=15.0,
        value=12.0,
        step=0.5
    )

    snr_limit = st.slider(
        "연주시차 신뢰도 기준",
        min_value=5,
        max_value=50,
        value=20,
        step=5,
        help="값이 클수록 연주시차 오차가 작은 별만 고릅니다."
    )

    if st.button("🔄 Gaia 자료 새로 불러오기"):
        st.cache_data.clear()
        st.rerun()


# ------------------------------------------------------------
# 메인 화면
# ------------------------------------------------------------
st.markdown('<div class="main-title">⭐ 별의 거리와 밝기 탐구 앱</div>', unsafe_allow_html=True)

st.markdown(
    """
    <div class="sub-box">
    <b>탐구 목표</b><br>
    별 두 개를 고른 뒤, 연주시차로 거리를 계산하고 겉보기 등급과 절대등급을 비교합니다.
    이를 통해 <b>우리 눈에 밝게 보이는 별</b>과 <b>실제로 밝은 별</b>이 다를 수 있음을 확인합니다.
    </div>
    """,
    unsafe_allow_html=True
)

with st.spinner("Gaia Archive에서 별 자료를 불러오는 중입니다..."):
    stars, is_fallback, data_source = load_gaia_data(
        top_n=top_n,
        min_parallax=min_parallax,
        max_gmag=max_gmag,
        snr_limit=snr_limit,
        order_kind=order_kind
    )

if is_fallback:
    st.warning(
        "Gaia API 연결에 실패하여 예시 자료로 실행 중입니다. "
        "앱 구조 확인용 자료이며 실제 Gaia 관측값이 아닙니다."
    )
else:
    st.success(f"Gaia Archive에서 {len(stars)}개의 별 후보를 불러왔습니다. 사용 테이블: {data_source}")

tab1, tab2, tab3 = st.tabs(["🔭 별 두 개 비교하기", "📘 개념 정리", "📊 Gaia 데이터 보기"])


# ------------------------------------------------------------
# 탭 1: 별 두 개 비교하기
# ------------------------------------------------------------
with tab1:
    st.subheader("1. 비교할 별 두 개를 고르세요")

    label_list = [make_star_label(row) for _, row in stars.iterrows()]
    label_to_index = {label: i for i, label in enumerate(label_list)}

    col_select_a, col_select_b = st.columns(2)

    with col_select_a:
        selected_a = st.selectbox(
            "별 A",
            label_list,
            index=0
        )

    with col_select_b:
        selected_b = st.selectbox(
            "별 B",
            label_list,
            index=1 if len(label_list) > 1 else 0
        )

    idx_a = label_to_index[selected_a]
    idx_b = label_to_index[selected_b]

    star_a = stars.iloc[idx_a]
    star_b = stars.iloc[idx_b]

    if idx_a == idx_b:
        st.warning("서로 다른 별 두 개를 골라야 비교가 더 의미 있습니다.")

    st.divider()

    st.subheader("2. 연주시차로 거리 확인하기")

    col_a, col_b = st.columns(2)

    with col_a:
        show_star_metrics(star_a, "별 A")

    with col_b:
        show_star_metrics(star_b, "별 B")

    st.markdown(
        """
        <div class="key-box">
        <b>핵심 개념 ① 연주시차</b><br>
        연주시차가 클수록 별은 더 가깝습니다.<br>
        이 앱에서는 거리(pc)를 <b>1000 ÷ 연주시차(mas)</b>로 계산합니다.
        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    st.subheader("3. 겉보기 밝기와 실제 밝기 비교하기")

    apparent_winner, apparent_ratio, apparent_text = compare_magnitude(
        star_a["phot_g_mean_mag"],
        star_b["phot_g_mean_mag"],
        "별 A",
        "별 B"
    )

    intrinsic_winner, intrinsic_ratio, intrinsic_text = compare_magnitude(
        star_a["absolute_g_mag"],
        star_b["absolute_g_mag"],
        "별 A",
        "별 B"
    )

    col_result_1, col_result_2 = st.columns(2)

    with col_result_1:
        st.markdown("#### 👀 겉보기 등급 비교")
        st.write(f"별 A의 겉보기 등급 G: **{star_a['phot_g_mean_mag']:.2f}**")
        st.write(f"별 B의 겉보기 등급 G: **{star_b['phot_g_mean_mag']:.2f}**")
        st.info(apparent_text)

    with col_result_2:
        st.markdown("#### 💡 절대등급 비교")
        st.write(f"별 A의 절대등급 M_G: **{star_a['absolute_g_mag']:.2f}**")
        st.write(f"별 B의 절대등급 M_G: **{star_b['absolute_g_mag']:.2f}**")
        st.info(intrinsic_text)

    # 밝기 지수 시각화
    chart_df = pd.DataFrame(
        {
            "보이는 밝기 지수": [
                star_a["apparent_brightness_index"],
                star_b["apparent_brightness_index"]
            ],
            "10 pc에서의 밝기 지수": [
                star_a["intrinsic_brightness_index"],
                star_b["intrinsic_brightness_index"]
            ]
        },
        index=["별 A", "별 B"]
    )

    # 값의 크기가 너무 작으므로 각 항목별 최대값을 1로 맞추어 비교한다.
    chart_df["보이는 밝기 지수"] = chart_df["보이는 밝기 지수"] / chart_df["보이는 밝기 지수"].max()
    chart_df["10 pc에서의 밝기 지수"] = chart_df["10 pc에서의 밝기 지수"] / chart_df["10 pc에서의 밝기 지수"].max()

    st.markdown("#### 📊 밝기 지수 비교")
    st.caption("각 항목에서 더 밝은 별을 1로 맞춘 상대 비교 그래프입니다.")
    st.bar_chart(chart_df)

    st.divider()

    st.subheader("4. 결론 만들기")

    if apparent_winner != intrinsic_winner and apparent_winner != "거의 같음" and intrinsic_winner != "거의 같음":
        st.markdown(
            f"""
            <div class="result-box">
            <b>핵심 발견</b><br>
            겉보기로는 <b>{apparent_winner}</b>가 더 밝지만,
            절대등급으로 비교하면 <b>{intrinsic_winner}</b>가 더 밝습니다.<br><br>
            즉, <b>가깝기 때문에 밝게 보이는 별</b>과
            <b>실제로 많은 빛을 내는 별</b>은 다를 수 있습니다.
            </div>
            """,
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"""
            <div class="result-box">
            <b>이번 비교의 해석</b><br>
            이번에 고른 두 별은 겉보기 등급과 절대등급의 밝기 순서가 크게 뒤바뀌지는 않았습니다.<br>
            하지만 두 비교는 의미가 다릅니다.<br><br>
            <b>겉보기 등급</b>은 지구에서 보이는 밝기이고,
            <b>절대등급</b>은 별을 모두 같은 거리인 10 pc에 두었다고 생각했을 때의 밝기입니다.
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown("#### ✍️ 학생 탐구 질문")
    st.write("1. 연주시차가 큰 별은 왜 더 가까운 별이라고 할 수 있을까?")
    st.write("2. 겉보기 등급의 숫자가 작다는 것은 무슨 뜻일까?")
    st.write("3. 절대등급은 왜 별을 10 pc에 둔다고 가정할까?")
    st.write("4. 가까워서 밝게 보이는 별과 실제로 밝은 별을 어떻게 구별할 수 있을까?")


# ------------------------------------------------------------
# 탭 2: 개념 정리
# ------------------------------------------------------------
with tab2:
    st.subheader("📘 핵심 개념 정리")

    st.markdown(
        """
        ### 1. 연주시차

        지구가 태양 주위를 공전하기 때문에, 가까운 별은 6개월 간격으로 보았을 때
        배경의 먼 별들에 비해 위치가 아주 조금 달라져 보입니다.

        이때 생기는 작은 각도를 **연주시차**라고 합니다.

        - 연주시차가 크다 → 별이 가깝다
        - 연주시차가 작다 → 별이 멀다

        이 앱에서는 Gaia 자료의 연주시차 단위가 mas이므로 다음처럼 계산합니다.

        **거리(pc) = 1000 ÷ 연주시차(mas)**

        ---
        ### 2. 겉보기 등급

        **겉보기 등급**은 지구에서 보이는 별의 밝기를 등급으로 나타낸 값입니다.

        중요한 점은 등급 숫자가 작을수록 더 밝다는 것입니다.

        - G = 3인 별은 G = 8인 별보다 밝게 보입니다.
        - 별이 실제로 밝아서 밝게 보일 수도 있고,
        - 단순히 가까워서 밝게 보일 수도 있습니다.

        ---
        ### 3. 절대등급

        **절대등급**은 별을 모두 같은 거리인 10 pc에 두었다고 생각했을 때의 등급입니다.

        그래서 절대등급은 별 자체가 얼마나 밝은지 비교할 때 사용합니다.

        - 절대등급 숫자가 작다 → 실제로 더 밝은 별
        - 절대등급 숫자가 크다 → 실제로 더 어두운 별

        ---
        ### 4. 이 앱의 핵심 문장

        **보이는 밝기와 실제 밝기는 다를 수 있다.**

        어떤 별은 실제로는 어둡지만 가까워서 밝게 보일 수 있습니다.  
        반대로 어떤 별은 실제로는 매우 밝지만 멀리 있어서 어둡게 보일 수 있습니다.
        """
    )


# ------------------------------------------------------------
# 탭 3: Gaia 데이터 보기
# ------------------------------------------------------------
with tab3:
    st.subheader("📊 불러온 Gaia 별 후보 데이터")

    display_df = stars[
        [
            "star_no",
            "source_id",
            "ra",
            "dec",
            "parallax",
            "parallax_error",
            "distance_pc",
            "distance_ly",
            "phot_g_mean_mag",
            "absolute_g_mag",
            "bp_rp"
        ]
    ].copy()

    display_df = display_df.rename(
        columns={
            "star_no": "번호",
            "source_id": "Gaia source_id",
            "ra": "적경 RA",
            "dec": "적위 Dec",
            "parallax": "연주시차(mas)",
            "parallax_error": "연주시차 오차",
            "distance_pc": "거리(pc)",
            "distance_ly": "거리(광년)",
            "phot_g_mean_mag": "겉보기 등급 G",
            "absolute_g_mag": "절대등급 M_G",
            "bp_rp": "색지수 BP-RP"
        }
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )

    st.markdown(
        """
        <div class="sub-box">
        <b>수업 활용 팁</b><br>
        학생들에게 먼저 겉보기 등급만 보고 더 밝은 별을 고르게 한 뒤,
        연주시차로 거리를 계산하고 절대등급을 비교하게 하면 좋습니다.<br>
        마지막에는 “처음 예상이 바뀌었는가?”를 쓰게 하면 탐구 흐름이 자연스럽습니다.
        </div>
        """,
        unsafe_allow_html=True
    )
