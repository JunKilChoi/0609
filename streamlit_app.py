import random
import time
import html as html_lib

import streamlit as st
import streamlit.components.v1 as components


# =========================
# 기본 설정
# =========================

st.set_page_config(
    page_title="짜잔! 발표자 뽑기",
    page_icon="🎉",
    layout="centered",
)


# =========================
# 화면 꾸미기 CSS
# =========================

st.markdown(
    """
    <style>
    .stApp {
        background: linear-gradient(135deg, #fff1f8 0%, #e0f7ff 45%, #fff8d6 100%);
    }

    .main-title {
        text-align: center;
        font-size: 48px;
        font-weight: 900;
        color: #ff4fa3;
        text-shadow: 3px 3px 0px #fff, 6px 6px 0px #ffd166;
        margin-bottom: 0px;
    }

    .sub-title {
        text-align: center;
        font-size: 20px;
        color: #555;
        margin-bottom: 30px;
    }

    .cute-box {
        background: rgba(255, 255, 255, 0.78);
        border-radius: 28px;
        padding: 25px;
        border: 4px dashed #ff9bd2;
        box-shadow: 0 12px 30px rgba(255, 100, 170, 0.25);
        margin-bottom: 25px;
    }

    .winner-card {
        background: linear-gradient(135deg, #ff5fa2, #ffc857, #69dbff);
        padding: 35px;
        border-radius: 35px;
        text-align: center;
        color: white;
        box-shadow: 0 20px 50px rgba(255, 95, 162, 0.45);
        border: 6px solid white;
        margin-top: 25px;
        animation: pop 0.55s ease-out;
    }

    .winner-label {
        font-size: 26px;
        font-weight: 800;
        margin-bottom: 8px;
    }

    .winner-name {
        font-size: 64px;
        font-weight: 1000;
        text-shadow: 3px 3px 0px rgba(0,0,0,0.18);
    }

    .winner-message {
        font-size: 22px;
        font-weight: 700;
        margin-top: 10px;
    }

    @keyframes pop {
        0% {
            transform: scale(0.3) rotate(-8deg);
            opacity: 0;
        }
        70% {
            transform: scale(1.08) rotate(3deg);
            opacity: 1;
        }
        100% {
            transform: scale(1) rotate(0deg);
        }
    }

    div.stButton > button {
        width: 100%;
        height: 70px;
        font-size: 26px;
        font-weight: 900;
        border-radius: 25px;
        border: none;
        background: linear-gradient(90deg, #ff5fa2, #ffc857, #69dbff);
        color: white;
        box-shadow: 0 10px 25px rgba(255, 95, 162, 0.35);
    }

    div.stButton > button:hover {
        transform: scale(1.02);
        border: none;
        color: white;
    }

    .small-card {
        background: rgba(255,255,255,0.75);
        padding: 16px;
        border-radius: 18px;
        border: 2px solid rgba(255,255,255,0.9);
        margin-bottom: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================
# 세션 상태
# =========================

if "history" not in st.session_state:
    st.session_state.history = []

if "last_winner" not in st.session_state:
    st.session_state.last_winner = None


# =========================
# 색종이 애니메이션
# =========================

def show_confetti():
    emojis = ["🎉", "✨", "🌈", "⭐", "💖", "🎊", "🍀", "🧡", "💛", "💙"]

    pieces = ""
    for i in range(90):
        left = random.randint(0, 100)
        delay = random.uniform(0, 1.8)
        duration = random.uniform(2.2, 4.5)
        size = random.randint(18, 34)
        emoji = random.choice(emojis)

        pieces += f"""
        <span class="confetti"
              style="
              left:{left}%;
              animation-delay:{delay}s;
              animation-duration:{duration}s;
              font-size:{size}px;
              ">
              {emoji}
        </span>
        """

    components.html(
        f"""
        <style>
        body {{
            margin: 0;
            overflow: hidden;
            background: transparent;
        }}

        .confetti-area {{
            position: relative;
            width: 100%;
            height: 220px;
            overflow: hidden;
            background: transparent;
        }}

        .confetti {{
            position: absolute;
            top: -50px;
            animation-name: fall;
            animation-timing-function: ease-in;
            animation-fill-mode: forwards;
        }}

        @keyframes fall {{
            0% {{
                transform: translateY(-60px) rotate(0deg);
                opacity: 1;
            }}
            100% {{
                transform: translateY(260px) rotate(720deg);
                opacity: 0;
            }}
        }}
        </style>

        <div class="confetti-area">
            {pieces}
        </div>
        """,
        height=230,
    )


# =========================
# 이름 처리 함수
# =========================

def parse_names(text):
    names = []
    for line in text.splitlines():
        name = line.strip()
        if name and name not in names:
            names.append(name)
    return names


# =========================
# 메인 화면
# =========================

st.markdown('<div class="main-title">🎉 짜잔! 발표자 뽑기 🎉</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">이름을 넣고 버튼을 누르면 오늘의 발표자가 화려하게 등장합니다!</div>', unsafe_allow_html=True)

st.markdown('<div class="cute-box">', unsafe_allow_html=True)

default_names = """김민수
이지우
박서준
최하윤
정도윤
한서아
윤지호
오유나"""

names_text = st.text_area(
    "학생 이름을 한 줄에 한 명씩 입력하세요.",
    value=default_names,
    height=180,
)

col1, col2 = st.columns(2)

with col1:
    exclude_picked = st.checkbox("이미 뽑힌 사람은 제외하기", value=True)

with col2:
    slow_mode = st.checkbox("두근두근 연출 켜기", value=True)

st.markdown("</div>", unsafe_allow_html=True)

names = parse_names(names_text)

pick_button = st.button("🎁 발표자 뽑기!")

if pick_button:
    if not names:
        st.error("학생 이름을 먼저 입력하세요.")
    else:
        candidates = names

        if exclude_picked:
            not_picked = [name for name in names if name not in st.session_state.history]

            if not_picked:
                candidates = not_picked
            else:
                st.session_state.history = []
                candidates = names
                st.info("모든 학생이 한 번씩 뽑혀서 기록을 초기화했습니다.")

        if slow_mode:
            countdown_area = st.empty()
            for word in ["두근...", "두근두근...", "과연 누구?", "3", "2", "1", "짜잔!"]:
                countdown_area.markdown(
                    f"""
                    <div style="
                        text-align:center;
                        font-size:42px;
                        font-weight:900;
                        color:#ff4fa3;
                        margin:25px;
                    ">
                        {word}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                time.sleep(0.45)

        winner = random.choice(candidates)
        st.session_state.last_winner = winner
        st.session_state.history.append(winner)

        st.balloons()
        show_confetti()


# =========================
# 결과 화면
# =========================

if st.session_state.last_winner:
    safe_winner = html_lib.escape(st.session_state.last_winner)

    st.markdown(
        f"""
        <div class="winner-card">
            <div class="winner-label">오늘의 발표자는...</div>
            <div class="winner-name">{safe_winner}</div>
            <div class="winner-message">👏 멋진 발표 기대합니다! 👏</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================
# 기록 관리
# =========================

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("📜 뽑힌 기록")
    if st.session_state.history:
        for i, name in enumerate(st.session_state.history, start=1):
            st.markdown(
                f"""
                <div class="small-card">
                    {i}. {html_lib.escape(name)}
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.write("아직 뽑힌 사람이 없습니다.")

with right:
    st.subheader("🧹 기록 초기화")
    st.write("다시 처음부터 뽑고 싶을 때 누르세요.")

    if st.button("기록 초기화하기"):
        st.session_state.history = []
        st.session_state.last_winner = None
        st.success("기록을 초기화했습니다.")
        st.rerun()
