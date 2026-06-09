import re
from datetime import datetime
from typing import Optional, Dict, Any, List

import bcrypt
import streamlit as st
from supabase import create_client, Client


# =========================
# 기본 설정
# =========================

st.set_page_config(
    page_title="회원 전용 게시판",
    page_icon="📚",
    layout="centered",
)

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{4,20}$")


# =========================
# DB 연결
# =========================

@st.cache_resource
def get_db() -> Client:
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SERVICE_ROLE_KEY"],
    )


def db() -> Client:
    return get_db()


# =========================
# 공통 유틸
# =========================

def normalize_username(username: str) -> str:
    return username.strip().lower()


def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def format_time(value: Optional[str]) -> str:
    if not value:
        return "-"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return value


def init_session_state() -> None:
    if "user" not in st.session_state:
        st.session_state.user = None


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    username = normalize_username(username)
    result = (
        db()
        .table("app_users")
        .select("*")
        .eq("username", username)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    result = (
        db()
        .table("app_users")
        .select("*")
        .eq("id", user_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def current_user() -> Optional[Dict[str, Any]]:
    user = st.session_state.get("user")
    if not user:
        return None

    fresh_user = get_user_by_id(user["id"])
    if not fresh_user or fresh_user["status"] != "approved":
        st.session_state.user = None
        return None

    st.session_state.user = fresh_user
    return fresh_user


def is_admin(user: Optional[Dict[str, Any]]) -> bool:
    return bool(user and user.get("role") == "admin" and user.get("status") == "approved")


def ensure_admin_user() -> None:
    """
    secrets.toml에 적은 관리자 계정이 DB에 없으면 자동 생성합니다.
    이미 있으면 role/status/password를 secrets 기준으로 보정합니다.
    """
    required_keys = [
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
        "ADMIN_USERNAME",
        "ADMIN_PASSWORD",
    ]

    missing = [key for key in required_keys if key not in st.secrets]
    if missing:
        st.error(f"Streamlit Secrets에 다음 값이 없습니다: {', '.join(missing)}")
        st.stop()

    admin_username = normalize_username(st.secrets["ADMIN_USERNAME"])
    admin_password = st.secrets["ADMIN_PASSWORD"]

    user = get_user_by_username(admin_username)

    if not user:
        db().table("app_users").insert(
            {
                "username": admin_username,
                "display_name": "관리자",
                "password_hash": hash_password(admin_password),
                "role": "admin",
                "status": "approved",
            }
        ).execute()
        return

    updates = {}
    if user.get("role") != "admin":
        updates["role"] = "admin"
    if user.get("status") != "approved":
        updates["status"] = "approved"
    if not verify_password(admin_password, user.get("password_hash", "")):
        updates["password_hash"] = hash_password(admin_password)

    if updates:
        db().table("app_users").update(updates).eq("id", user["id"]).execute()


# =========================
# 회원가입 / 로그인
# =========================

def page_signup() -> None:
    st.title("회원가입")
    st.caption("가입 후 관리자의 승인을 받아야 게시판을 볼 수 있습니다.")

    with st.form("signup_form", clear_on_submit=False):
        display_name = st.text_input("이름 또는 별명", max_chars=30)
        username = st.text_input("아이디", help="영문, 숫자, 밑줄(_)만 사용 / 4~20자")
        password = st.text_input("비밀번호", type="password")
        password2 = st.text_input("비밀번호 확인", type="password")
        submitted = st.form_submit_button("가입 신청")

    if not submitted:
        return

    display_name = display_name.strip()
    username = normalize_username(username)

    if not display_name:
        st.error("이름 또는 별명을 입력하세요.")
        return

    if not USERNAME_RE.fullmatch(username):
        st.error("아이디는 영문, 숫자, 밑줄(_)만 사용하여 4~20자로 입력하세요.")
        return

    if len(password) < 6:
        st.error("비밀번호는 6자 이상으로 입력하세요.")
        return

    if password != password2:
        st.error("비밀번호 확인이 일치하지 않습니다.")
        return

    if get_user_by_username(username):
        st.error("이미 사용 중인 아이디입니다.")
        return

    try:
        db().table("app_users").insert(
            {
                "username": username,
                "display_name": display_name,
                "password_hash": hash_password(password),
                "role": "member",
                "status": "pending",
            }
        ).execute()
        st.success("가입 신청이 완료되었습니다. 관리자의 승인을 기다려 주세요.")
    except Exception as e:
        st.error(f"가입 처리 중 오류가 발생했습니다: {e}")


def page_login() -> None:
    st.title("로그인")

    with st.form("login_form"):
        username = st.text_input("아이디")
        password = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("로그인")

    if not submitted:
        return

    user = get_user_by_username(username)

    if not user or not verify_password(password, user.get("password_hash", "")):
        st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
        return

    if user["status"] == "pending":
        st.warning("아직 관리자 승인이 완료되지 않았습니다.")
        return

    if user["status"] == "blocked":
        st.error("차단된 계정입니다. 관리자에게 문의하세요.")
        return

    st.session_state.user = user
    st.success(f"{user['display_name']}님, 로그인되었습니다.")
    st.rerun()


def logout() -> None:
    st.session_state.user = None
    st.rerun()


# =========================
# 게시판
# =========================

def create_post(title: str, body: str, author_id: str) -> None:
    db().table("posts").insert(
        {
            "title": title.strip(),
            "body": body.strip(),
            "author_id": author_id,
        }
    ).execute()


def list_posts() -> List[Dict[str, Any]]:
    result = (
        db()
        .table("posts")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


def delete_post(post_id: int) -> None:
    db().table("posts").delete().eq("id", post_id).execute()


def get_author_map(posts: List[Dict[str, Any]]) -> Dict[str, str]:
    author_ids = sorted({post["author_id"] for post in posts if post.get("author_id")})
    if not author_ids:
        return {}

    result = (
        db()
        .table("app_users")
        .select("id, display_name, username")
        .in_("id", author_ids)
        .execute()
    )
    users = result.data or []
    return {
        user["id"]: f"{user['display_name']} ({user['username']})"
        for user in users
    }


def page_board(user: Dict[str, Any]) -> None:
    st.title("회원 전용 게시판")
    st.caption("승인된 회원만 글을 읽고 쓸 수 있습니다.")

    write_tab, list_tab = st.tabs(["글쓰기", "게시글"])

    with write_tab:
        with st.form("post_form", clear_on_submit=True):
            title = st.text_input("제목", max_chars=80)
            body = st.text_area("내용", height=180)
            submitted = st.form_submit_button("등록")

        if submitted:
            if not title.strip():
                st.error("제목을 입력하세요.")
            elif not body.strip():
                st.error("내용을 입력하세요.")
            else:
                create_post(title, body, user["id"])
                st.success("게시글이 등록되었습니다.")
                st.rerun()

    with list_tab:
        posts = list_posts()

        if not posts:
            st.info("아직 게시글이 없습니다.")
            return

        author_map = get_author_map(posts)

        for post in posts:
            with st.container(border=True):
                st.subheader(post["title"])
                author = author_map.get(post.get("author_id"), "탈퇴한 회원")
                st.caption(f"작성자: {author} · 작성일: {format_time(post.get('created_at'))}")
                st.write(post["body"])

                if is_admin(user):
                    if st.button("게시글 삭제", key=f"delete_post_{post['id']}"):
                        delete_post(post["id"])
                        st.warning("게시글을 삭제했습니다.")
                        st.rerun()


# =========================
# 관리자 페이지
# =========================

def list_users() -> List[Dict[str, Any]]:
    result = (
        db()
        .table("app_users")
        .select("id, username, display_name, role, status, created_at")
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


def update_user(user_id: str, updates: Dict[str, Any]) -> None:
    db().table("app_users").update(updates).eq("id", user_id).execute()


def delete_user(user_id: str) -> None:
    db().table("app_users").delete().eq("id", user_id).execute()


def page_admin(user: Dict[str, Any]) -> None:
    st.title("회원 관리")
    st.caption("가입 승인, 차단, 권한 변경, 계정 삭제를 할 수 있습니다.")

    users = list_users()

    status_label = {
        "pending": "승인 대기",
        "approved": "승인됨",
        "blocked": "차단됨",
    }

    role_label = {
        "admin": "관리자",
        "member": "회원",
    }

    for target in users:
        with st.container(border=True):
            st.markdown(f"### {target['display_name']} `{target['username']}`")
            st.write(
                f"권한: **{role_label.get(target['role'], target['role'])}** / "
                f"상태: **{status_label.get(target['status'], target['status'])}** / "
                f"가입일: {format_time(target.get('created_at'))}"
            )

            if target["id"] == user["id"]:
                st.caption("현재 로그인한 관리자 계정입니다. 본인 계정은 여기서 삭제하거나 차단하지 않습니다.")

            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                if st.button("승인", key=f"approve_{target['id']}", disabled=target["status"] == "approved"):
                    update_user(target["id"], {"status": "approved"})
                    st.rerun()

            with col2:
                block_disabled = target["id"] == user["id"] or target["status"] == "blocked"
                if st.button("차단", key=f"block_{target['id']}", disabled=block_disabled):
                    update_user(target["id"], {"status": "blocked"})
                    st.rerun()

            with col3:
                if st.button("회원화", key=f"member_{target['id']}", disabled=target["role"] == "member"):
                    update_user(target["id"], {"role": "member"})
                    st.rerun()

            with col4:
                if st.button("관리자화", key=f"admin_{target['id']}", disabled=target["role"] == "admin"):
                    update_user(target["id"], {"role": "admin", "status": "approved"})
                    st.rerun()

            with col5:
                delete_disabled = target["id"] == user["id"]
                if st.button("삭제", key=f"delete_user_{target['id']}", disabled=delete_disabled):
                    delete_user(target["id"])
                    st.rerun()


# =========================
# 앱 라우팅
# =========================

def main() -> None:
    init_session_state()
    ensure_admin_user()

    user = current_user()

    st.sidebar.title("메뉴")

    if user:
        st.sidebar.success(f"{user['display_name']}님")
        st.sidebar.caption(f"권한: {user['role']}")

        menu_options = ["게시판"]
        if is_admin(user):
            menu_options.append("회원 관리")

        menu = st.sidebar.radio("이동", menu_options)

        if st.sidebar.button("로그아웃"):
            logout()

        if menu == "게시판":
            page_board(user)
        elif menu == "회원 관리":
            page_admin(user)

    else:
        menu = st.sidebar.radio("이동", ["로그인", "회원가입"])

        if menu == "로그인":
            page_login()
        elif menu == "회원가입":
            page_signup()


if __name__ == "__main__":
    main()
