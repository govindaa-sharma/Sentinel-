import streamlit as st
import requests

import os
# API_URL = os.environ.get("API_URL", "http://localhost:8000")  # we'll change this to the deployed URL later
API_URL = st.secrets.get("API_URL", os.environ.get("API_URL", "http://localhost:8000"))
st.set_page_config(page_title="Rowans", layout="wide")

if "token" not in st.session_state:
    st.session_state.token = None
    st.session_state.role = None


def login():
    st.title("Sentinel")
    with st.form("login"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in")

    if submitted:
        resp = requests.post(f"{API_URL}/auth/login", data={"username": username, "password": password})
        if resp.status_code == 200:
            st.session_state.token = resp.json()["access_token"]
            # decode role from a lightweight call, or just ask the user which view they want
            st.session_state.username = username
            st.rerun()
        else:
            st.error("Login failed")


def headers():
    return {"Authorization": f"Bearer {st.session_state.token}"}


def ask_view():
    st.subheader("Ask Sentinel")
    request_text = st.text_area("What do you want to know or change?", height=100)
    if st.button("Submit"):
        with st.spinner("Thinking..."):
            resp = requests.post(f"{API_URL}/agent/ask", json={"request": request_text}, headers=headers())
        if resp.status_code == 200:
            data = resp.json()
            st.write(f"**Status:** {data['status']}")
            st.write(f"**Risk tier:** {data['risk_tier']}")
            if data["query_plan"]:
                st.code(data["query_plan"]["sql"], language="sql")
            if data["status"] == "success":
                st.dataframe(data["execution_result"]["rows"])
            elif data["status"] == "pending_approval":
                st.warning("This action requires approval before it will run.")
        else:
            st.error(resp.text)


def approvals_view():
    st.subheader("Pending Approvals")
    resp = requests.get(f"{API_URL}/approvals/pending", headers=headers())
    if resp.status_code != 200:
        st.error(resp.text)
        return

    pending = resp.json()
    if not pending:
        st.info("Nothing pending.")
        return

    for item in pending:
        with st.container(border=True):
            st.write(f"**Request:** {item['user_request']}")
            st.code(item["sql"], language="sql")
            st.caption(f"Operation: {item['operation']} | Tables: {item['tables']}")

            col1, col2 = st.columns(2)
            if col1.button("Approve", key=f"approve_{item['id']}"):
                r = requests.post(f"{API_URL}/approvals/{item['id']}/approve", headers=headers())
                if r.status_code == 200:
                    st.success("Approved and executed.")
                    st.rerun()
                else:
                    st.error(r.json().get("detail", r.text))

            if col2.button("Reject", key=f"reject_{item['id']}"):
                r = requests.post(f"{API_URL}/approvals/{item['id']}/reject", json={"reason": "Rejected via dashboard"}, headers=headers())
                if r.status_code == 200:
                    st.warning("Rejected.")
                    st.rerun()
                else:
                    st.error(r.json().get("detail", r.text))


if not st.session_state.token:
    login()
else:
    st.sidebar.write(f"Logged in as **{st.session_state.username}**")
    if st.sidebar.button("Log out"):
        st.session_state.token = None
        st.rerun()

    tab1, tab2 = st.tabs(["Ask", "Approvals"])
    with tab1:
        ask_view()
    with tab2:
        approvals_view()