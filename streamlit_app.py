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

TOTAL_STUDENTS = 30


# =========================
# CSS 디자인
# =========================

st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(circle at top left, #ffe1f1 0, transparent 35%),
            radial-gradient(circle at top right, #d8f4ff 0, transparent 35%),
            linear-gradient(135deg, #fff7fb 0%, #eefaff 45%, #fff7df 100%);
    }

    .main-title {
        text-align: center;
        font-size: 46px;
        font-weight: 1000;
        color: #ff4fa3;
        text-shadow: 3px 3px 0 #ffffff, 6px 6px 0 #ffd166;
        margin-top: 5px;
        margin-bottom: 2px;
    }

    .sub-title {
        text-align: center;
        font-size: 18px;
        color: #666;
        font-weight: 700;
        margin-bottom: 18px;
    }

    .stage-card {
        background: rgba(255, 255, 255, 0.84);
        border-radius: 34px;
        padding: 22px 24px 26px 24px;
        border: 5px solid rgba(255, 255, 255, 0.95);
        box-shadow: 0 18px 45px rgba(255, 91, 160, 0.25);
        margin-bottom: 18px;
    }

    .winner-label {
        text-align: center;
        font-size: 18px;
        font-weight: 900;
        color: #777;
        margin-bottom: 8px;
    }

    .winner-name {
        width: 86%;
        margin: 0 auto 13px auto;
        padding: 14px 20px;
        text-align: center;
        border-radius: 999px;
        background: linear-gradient(135deg, #ff69b4, #ff9a9e, #ffd166);
        color: white;
        font-size: 42px;
        font-weight: 1000;
        letter-spacing: -1px;
        text-shadow: 2px 2px 0 rgba(0,0,0,0.16);
        box-shadow: 0 12px 25px rgba(255, 105, 180, 0.38);
        animation: pop 0.55s ease-out;
    }

    .winner-number {
        width: 190px;
        height: 190px;
        border-radius: 50%;
        margin: 0 auto;
        background: linear-gradient(135deg, #ffffff, #fff3c4);
        border: 9px solid #ffca3a;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #ff4fa3;
        font-size: 78px;
        font-weight: 1000;
        box-shadow: 0 18px 32px rgba(255, 202, 58, 0.45);
        animation: bounce 0.7s ease-out;
    }

    .winner-number-small {
        font-size: 28px;
        margin-left: 4px;
    }

    .placeholder-name {
        width: 86%;
        margin: 0 auto 13px auto;
        padding: 14px 20px;
        text-align: center;
        border-radius: 999px;
        background: linear-gradient(135deg, #dcefff, #f5e6ff);
        color: #7b7b7b;
        font-size: 30px;
        font-weight: 900;
        border: 3px dashed #b7dfff;
    }

    .placeholder-number {
        width: 170px;
        height: 170px;
        border-radius: 50%;
        margin: 0 auto;
        background: rgba(255,255,255,0.75);
        border: 7px dashed #c7d9ff;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #9aa7c7;
        font-size: 58px;
        font-weight: 1000;
    }

    .student-card {
        background: rgba(255,255,255,0.78);
        border: 2px solid rgba(255,255,255,0.95);
        border-radius: 18px;
        padding: 10px 12px;
        margin-bottom: 8px;
        font-weight: 800;
        box-shadow: 0 8px 18px rgba(100,100,100,0.08);
    }

    .history-chip {
        display: inline-block;
        background: white;
        border: 2px solid #ffd166;
        color: #ff4fa3;
        padding: 7px 12px;
        border-radius: 999px;
        font-weight: 900;
        margin: 4px;
        box-shadow: 0 4px 10px rgba(255, 202, 58, 0.25);
    }

    div.stButton > button {
        width: 100%;
        height: 68px;
        font-size: 25px;
        font-weight: 1000;
        border-radius: 24px;
        border: none;
        color: white;
        background: linear-gradient(90deg, #ff4fa3, #ffca3a, #56ccf2);
        box-shadow: 0 12px 25px rgba(255, 79, 163, 0.35);
    }

    div.stButton > button:hover {
        transform: scale(1.015);
        color: white;
        border: none;
    }

    @keyframes pop {
        0% {
            transform: scale(0.4) rotate(-5deg);
            opacity: 0;
        }
        75% {
            transform: scale(1.06) rotate(2deg);
            opacity: 1;
        }
        100% {
            transform: scale(1) rotate(0deg);
        }
    }

    @keyframes bounce {
        0% {
            transform: scale(0.2);
            opacity: 0;
        }
        60% {
            transform: scale(1.12);
            opacity: 1;
        }
        100% {
            transform: scale(1);
        }
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

if "winner_number" not in st.session_state:
    st.session_state.winner_number = None

if "winner_name" not in st.session_state:
    st.session_state.winner_name = None


# =========================
# 함수
# =========================

def show_confetti():
    emojis = ["🎉", "✨", "🌈", "⭐", "💖", "🎊", "🍀", "🧡", "💛", "💙", "🌟"]

    pieces = ""
    for _ in range(95):
        left = random.randint(0, 100)
        delay = random.uniform(0, 1.4)
        duration = random.uniform(2.0, 4.0)
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
            height: 190px;
            overflow: hidden;
            background: transparent;
        }}

        .confetti {{
            position: absolute;
            top: -45px;
            animation-name: fall;
            animation-timing-function: ease-in;
            animation-fill-mode: forwards;
        }}

        @keyframes fall {{
            0% {{
                transform: translateY(-50px) rotate(0deg);
                opacity: 1;
            }}
            100% {{
                transform: translateY(230px) rotate(720deg);
                opacity: 0;
            }}
        }}
        </style>

        <div class="confetti-area">
            {pieces}
        </div>
        """,
        height=195,
    )


def parse_names(text):
    raw_names = [line.strip() for line in text.splitlines()]

    names = {}
    for number in range(1, TOTAL_STUDENTS + 1):
        index = number - 1

        if index < len(raw_names) and raw_names[index]:
            names[number] = raw_names[index]
        else:
            names[number] = f"{number}번"

    return names


def draw_student(exclude_picked):
    all_numbers = list(range(1, TOTAL_STUDENTS + 1))

    if exclude_picked:
        candidates = [number for number in all_numbers if number not in st.session_state.history]

        if not candidates:
            st.session_state.history = []
            candidates = all_numbers
            st.info("30명이 모두 한 번씩 뽑혀서 기록을 초기화했습니다.")
    else:
        candidates = all_numbers

    return random.choice(candidates)


def render_result():
    if st.session_state.winner_number is None:
        st.markdown(
            """
            <div class="stage-card">
                <div class="winner-label">오늘의 발표자는?</div>
                <div class="placeholder-name">버튼을 누르면 이름이 여기에!</div>
                <div class="placeholder-number">?</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        safe_name = html_lib.escape(st.session_state.winner_name)
        number = st.session_state.winner_number

        st.markdown(
            f"""
            <div class="stage-card">
                <div class="winner-label">🎊 오늘의 발표자는 🎊</div>
                <div class="winner-name">{safe_name}</div>
                <div class="winner-number">{number}<span class="winner-number-small">번</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# =========================
# 메인 화면
# =========================

st.markdown('<div class="main-title">🎉 짜잔! 발표자 뽑기 🎉</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">1번부터 30번까지 자동으로 준비되어 있어요</div>', unsafe_allow_html=True)

default_names = "\n".join([f"{i}번 학생" for i in range(1, TOTAL_STUDENTS + 1)])

names_text = st.text_area(
    "학생 이름 입력",
    value=default_names,
    height=115,
    help="위에서부터 1번, 2번, 3번 순서로 자동 연결됩니다.",
)

name_map = parse_names(names_text)

render_result()

col1, col2 = st.columns([3, 1])

with col1:
    pick_clicked = st.button("🎁 짜잔! 발표자 뽑기!")

with col2:
    reset_clicked = st.button("🧹 초기화")

exclude_picked = st.checkbox("이미 뽑힌 번호는 제외하기", value=True)

if pick_clicked:
    loading = st.empty()

    for word in ["두근...", "두근두근...", "과연 누구?", "3", "2", "1", "짜잔!"]:
        loading.markdown(
            f"""
            <div style="
                text-align:center;
                font-size:34px;
                font-weight:1000;
                color:#ff4fa3;
                margin:10px;
            ">
                {word}
            </div>
            """,
            unsafe_allow_html=True,
        )
        time.sleep(0.28)

    loading.empty()

    winner_number = draw_student(exclude_picked)
    winner_name = name_map[winner_number]

    st.session_state.winner_number = winner_number
    st.session_state.winner_name = winner_name
    st.session_state.history.append(winner_number)

    st.balloons()
    show_confetti()
    st.rerun()

if reset_clicked:
    st.session_state.history = []
    st.session_state.winner_number = None
    st.session_state.winner_name = None
    st.success("뽑기 기록을 초기화했습니다.")
    st.rerun()


# =========================
# 아래쪽 정보
# =========================

st.divider()

with st.expander("📋 1번부터 30번까지 명단 보기"):
    cols = st.columns(3)

    for number in range(1, TOTAL_STUDENTS + 1):
        col = cols[(number - 1) % 3]
        with col:
            safe_name = html_lib.escape(name_map[number])
            st.markdown(
                f"""
                <div class="student-card">
                    {number}번 · {safe_name}
                </div>
                """,
                unsafe_allow_html=True,
            )

st.subheader("📜 뽑힌 기록")

if st.session_state.history:
    history_html = ""

    for number in st.session_state.history:
        safe_name = html_lib.escape(name_map.get(number, f"{number}번"))
        history_html += f"""
        <span class="history-chip">{number}번 {safe_name}</span>
        """

    st.markdown(history_html, unsafe_allow_html=True)
else:
    st.write("아직 뽑힌 번호가 없습니다.")
