import streamlit as st

from support_app import db
from support_app.graph import run_support_flow
from support_app.ui_utils import stream_text


st.set_page_config(page_title="Multi-Agent Ticket Resolution", layout="wide")


def _status_badge(status: str | None) -> str:
    s = (status or "").lower()
    if s == "closed":
        return "Closed"
    if s == "in progress":
        return "In Progress"
    if s == "open":
        return "Open"
    return status or ""


if "auth_user" not in st.session_state:
    st.session_state["auth_user"] = None

if "messages" not in st.session_state:
    st.session_state["messages"] = []


def render_login():
    st.title("Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Sign in"):
        user = db.authenticate_user(username=username, password=password)
        if user is None:
            st.error("Invalid credentials")
            return
        st.session_state["auth_user"] = user
        st.session_state["messages"] = []
        st.rerun()


def render_sidebar(user_id: str):
    st.sidebar.header("Account")
    user = db.get_user_by_id(user_id)
    if user:
        st.sidebar.write(f"**Username:** {user.username}")
        st.sidebar.write(f"**Email:** {user.email or '-'}")

    st.sidebar.divider()
    st.sidebar.header("Ticket History")
    tickets = db.list_user_tickets(user_id, limit=25)
    open_tickets = [t for t in tickets if (t.status or "") != "Closed"]

    st.sidebar.subheader("Open / In Progress")
    if not open_tickets:
        st.sidebar.caption("No open tickets")
    for t in open_tickets:
        st.sidebar.markdown(f"**{t.ticket_title or '(no title)'}**")
        st.sidebar.caption(f"{_status_badge(t.status)} | Severity: {t.severity} | {t.ticket_id}")

    st.sidebar.subheader("Recent")
    for t in tickets[:10]:
        st.sidebar.markdown(f"**{t.ticket_title or '(no title)'}**")
        st.sidebar.caption(f"{_status_badge(t.status)} | {t.ticket_id}")

    st.sidebar.divider()
    if st.sidebar.button("Sign out"):
        st.session_state["auth_user"] = None
        st.session_state["messages"] = []
        st.rerun()


user = st.session_state["auth_user"]
if user is None:
    render_login()
    st.stop()

render_sidebar(user.user_id)

st.title("Support Chat")

for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Describe your login issue...")
if user_input:
    st.session_state["messages"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Working on your ticket..."):
            result = run_support_flow(user_id=user.user_id, user_message=user_input)
            assistant_text = result.get("assistant_message", "")
        st.write_stream(stream_text(assistant_text))

    st.session_state["messages"].append({"role": "assistant", "content": assistant_text})
