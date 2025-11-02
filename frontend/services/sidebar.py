import streamlit as st
from services.auth import create_authenticator

authenticator = create_authenticator()

def show_sidebar() -> None:
    if st.session_state.get('authentication_status') is None:
        with st.sidebar:
            st.page_link("pages/login.py", label="Login", icon=":material/open_with:")
            st.page_link("app.py", label="Home", icon=":material/home:")
            st.page_link("pages/agent.py", label="Agent", icon=":material/apps:")
    else:
        with st.sidebar:
            st.write(f'Welcome *{st.session_state.get("name")}*')
            st.page_link("app.py", label="Home", icon=":material/home:")
            st.page_link("pages/agent.py", label="Agent", icon=":material/apps:")
            authenticator.logout('Logout','sidebar')