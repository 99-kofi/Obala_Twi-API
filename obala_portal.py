import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.title("🔑 OBALA Developer Portal")
page = st.sidebar.selectbox("Navigate", ["Signup", "Login", "Dashboard"])

if page == "Signup":
    full_name = st.text_input("Full Name")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Sign Up"):
        res = requests.post(f"{API_URL}/signup", json={
            "full_name": full_name,
            "email": email,
            "password": password
        })
        st.json(res.json())

elif page == "Login":
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        res = requests.post(f"{API_URL}/login", json={
            "email": email,
            "password": password
        })
        if res.status_code == 200:
            data = res.json()
            st.session_state["api_key"] = data["api_key"]
            st.success("Logged in! Go to Dashboard.")
        else:
            st.error(res.json()["error"])

elif page == "Dashboard":
    if "api_key" not in st.session_state:
        st.warning("Please log in first")
    else:
        st.subheader("Your API Key")
        st.code(st.session_state["api_key"])
        st.caption("Use this key with the X-API-Key header when calling the OBALA API.")
