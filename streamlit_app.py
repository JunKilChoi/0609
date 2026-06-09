import sqlite3
import bcrypt
import streamlit as st
from datetime import datetime


# =========================
# 기본 관리자 계정
# =========================
# 수업용 빠른 버전입니다.
# GitHub 저장소가 Public이면 이 비밀번호가 노출됩니다.
# 가능하면 Private 저장소에서 사용하세요.

ADMIN_USERNAME = "teacher"
ADMIN_PASSWORD = "1234"


# =========================
# 기본 설정
# =========================

st.set_page_config(
    page_title="회원 전용 게시판",
    page_icon="📚",
    layout="centered",
)

DB_PATH = "app.db"


# =========================
# DB 함수
# =========================

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        create table if not exists users (
            id integer primary key autoincrement,
            username text unique not null,
            display_name text not null,
            password_hash text not null,
            role text not null default 'member',
            status text not null default 'pending',
            created_at text not null
        )
    """)

    cur.execute("""
        create table if not exists posts (
            id integer primary key autoincrement,
            title text not null,
            body text not null,
            author_id integer,
            created_at text not null,
            foreign key(author_id) references users(id)
        )
    """)

    conn.commit()
    conn.close()


def hash_password(password):
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password, password_hash):
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def get_user_by_username(username):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("select * from users where username = ?", (username,))
    user = cur.fetchone()
    conn.close()
    return dict(user) if user else None


def get_user_by_id(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("select * from users where id = ?", (user_id,))
    user = cur.fetchone()
    conn.close()
    return dict(user) if user else None


def create_user(username, display_name, password, role="member", status="pending"):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        insert into users
        (username, display_name, password_hash, role, status, created_at)
        values (?, ?, ?, ?, ?, ?)
        """,
        (
            username,
            display_name,
            hash_password(password),
            role,
            status,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    conn.commit()
    conn.close()


def ensure_admin():
    admin = get_user_by_username(ADMIN_USERNAME)

    if admin is None:
        create_user(
            username=ADMIN_USERNAME,
            display_name="관리자",
            password=ADMIN_PASSWORD,
            role="admin",
            status="approved",
        )


def update_user_status(user_id, status):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("update users set status = ? where id = ?", (status, user_id))
    conn.commit()
    conn.close()


def update_user_role(user_id, role):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("update users set role = ? where id = ?", (role, user_id))
    conn.commit()
    conn.close()


def delete_user(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("delete from users where id = ?", (user_id,))
    conn.commit()
    conn.close()


def list_users():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("select * from users order by created_at desc")
    users = cur.fetchall()
    conn.close()
    return [dict(user) for user in users]


def create_post(title, body, author_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        insert into posts
        (title, body, author_id, created_at)
        values (?, ?, ?, ?)
        """,
        (
            title,
            body,
            author_id,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    conn.commit()
    conn.close()


def list_posts():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        select
            posts.id,
            posts.title,
            posts.body,
            posts.created_at,
            users.display_name,
            users.username
        from posts
        left join users on posts.author_id = users.id
        order by posts.created_at desc
        """
    )
    posts = cur.fetchall()
    conn.close()
    return [dict(post) for post in posts]


def delete_post(post_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("delete from posts where id = ?", (post_id,))
    conn.commit()
    conn.close()


# =========================
# 세션
# =========================

def init_session():
    if "user_id" not in st.session_state:
        st.session_state.user_id = None


def current_user():
    if st.session_state.user_id is None:
        return None

    user = get_user_by_id(st.session_state.user_id)

    if user is None:
        st.session_state.user_id = None
        return None

    if user["status"] != "approved":
        st.session_state.user_id = None
        return None

    return user


def logout():
    st.session_state.user_id = None
    st.rerun()


# =========================
# 화면: 회원가입
# =========================

def page_signup():
    st.title("회원가입")
    st.write("가입 후 관리자가 승인해야 게시판을 이용할 수 있습니다.")

    with st.form("signup_form"):
        display_name = st.text_input("이름 또는 별명")
        username = st.text_input("아이디")
        password = st.text_input("비밀번호", type="password")
        password2 = st.text_input("비밀번호 확인", type="password")
        submitted = st.form_submit_button("가입 신청")

    if submitted:
        username = username.strip().lower()
        display_name = display_name.strip()

        if not display_name:
            st.error("이름 또는 별명을 입력하세요.")
            return

        if len(username) < 4:
            st.error("아이디는 4자 이상으로 입력하세요.")
            return

        if len(password) < 4:
            st.error("수업용 간이 버전에서는 비밀번호를 4자 이상으로 입력하세요.")
            return

        if password != password2:
            st.error("비밀번호가 서로 다릅니다.")
            return

        if get_user_by_username(username):
            st.error("이미 사용 중인 아이디입니다.")
            return

        create_user(username, display_name, password)
        st.success("가입 신청이 완료되었습니다. 관리자의 승인을 기다려 주세요.")


# =========================
# 화면: 로그인
# =========================

def page_login():
    st.title("로그인")

    with st.form("login_form"):
        username = st.text_input("아이디")
        password = st.text_input("비밀번호", type="password")
        submitted = st.form_submit_button("로그인")

    if submitted:
        username = username.strip().lower()
        user = get_user_by_username(username)

        if user is None:
            st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
            return

        if not verify_password(password, user["password_hash"]):
            st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
            return

        if user["status"] == "pending":
            st.warning("아직 관리자 승인이 완료되지 않았습니다.")
            return

        if user["status"] == "blocked":
            st.error("차단된 계정입니다.")
            return

        st.session_state.user_id = user["id"]
        st.success(f"{user['display_name']}님, 로그인되었습니다.")
        st.rerun()


# =========================
# 화면: 게시판
# =========================

def page_board(user):
    st.title("회원 전용 게시판")

    tab_write, tab_list = st.tabs(["글쓰기", "게시글 보기"])

    with tab_write:
        with st.form("post_form"):
            title = st.text_input("제목")
            body = st.text_area("내용", height=180)
            submitted = st.form_submit_button("등록")

        if submitted:
            if not title.strip():
                st.error("제목을 입력하세요.")
                return

            if not body.strip():
                st.error("내용을 입력하세요.")
                return

            create_post(title.strip(), body.strip(), user["id"])
            st.success("게시글이 등록되었습니다.")
            st.rerun()

    with tab_list:
        posts = list_posts()

        if not posts:
            st.info("아직 게시글이 없습니다.")
            return

        for post in posts:
            with st.container(border=True):
                st.subheader(post["title"])

                writer = post["display_name"] or "알 수 없음"
                username = post["username"] or "unknown"

                st.caption(
                    f"작성자: {writer} ({username}) · 작성일: {post['created_at']}"
                )

                st.write(post["body"])

                if user["role"] == "admin":
                    if st.button("게시글 삭제", key=f"delete_post_{post['id']}"):
                        delete_post(post["id"])
                        st.warning("게시글을 삭제했습니다.")
                        st.rerun()


# =========================
# 화면: 회원 관리
# =========================

def page_admin(user):
    st.title("회원 관리")

    users = list_users()

    for target in users:
        with st.container(border=True):
            st.markdown(f"### {target['display_name']} / `{target['username']}`")
            st.write(f"상태: **{target['status']}**")
            st.write(f"권한: **{target['role']}**")
            st.caption(f"가입일: {target['created_at']}")

            col1, col2, col3, col4, col5 = st.columns(5)

            with col1:
                if st.button("승인", key=f"approve_{target['id']}"):
                    update_user_status(target["id"], "approved")
                    st.rerun()

            with col2:
                if st.button("차단", key=f"block_{target['id']}"):
                    if target["id"] == user["id"]:
                        st.error("자기 자신은 차단할 수 없습니다.")
                    else:
                        update_user_status(target["id"], "blocked")
                        st.rerun()

            with col3:
                if st.button("회원화", key=f"member_{target['id']}"):
                    update_user_role(target["id"], "member")
                    st.rerun()

            with col4:
                if st.button("관리자화", key=f"admin_{target['id']}"):
                    update_user_role(target["id"], "admin")
                    update_user_status(target["id"], "approved")
                    st.rerun()

            with col5:
                if st.button("삭제", key=f"delete_user_{target['id']}"):
                    if target["id"] == user["id"]:
                        st.error("자기 자신은 삭제할 수 없습니다.")
                    else:
                        delete_user(target["id"])
                        st.rerun()


# =========================
# 메인
# =========================

def main():
    init_db()
    ensure_admin()
    init_session()

    user = current_user()

    st.sidebar.title("메뉴")

    if user is None:
        menu = st.sidebar.radio("이동", ["로그인", "회원가입"])

        if menu == "로그인":
            page_login()
        else:
            page_signup()

    else:
        st.sidebar.success(f"{user['display_name']}님")
        st.sidebar.write(f"권한: {user['role']}")

        menu_options = ["게시판"]

        if user["role"] == "admin":
            menu_options.append("회원 관리")

        menu = st.sidebar.radio("이동", menu_options)

        if st.sidebar.button("로그아웃"):
            logout()

        if menu == "게시판":
            page_board(user)

        elif menu == "회원 관리":
            page_admin(user)


if __name__ == "__main__":
    main()
