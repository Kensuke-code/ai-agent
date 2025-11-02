import streamlit as st
from services.auth import create_authenticator

authenticator = create_authenticator()

# ログインフォーム描画
authenticator.login()

## ログイン成功
if st.session_state["authentication_status"]:
    st.switch_page("app.py")
elif st.session_state["authentication_status"] is False:
    st.error("ユーザ名またはパスワードが間違っています")