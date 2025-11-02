import streamlit as st
from services.auth import create_authenticator

authenticator = create_authenticator()

# ログインフォーム描画
authenticator.login()

if st.session_state["authentication_status"]:
    ## ログイン成功
    st.switch_page("app.py")
elif st.session_state["authentication_status"] is False:
    ## ログイン失敗
    st.error("ユーザ名またはパスワードが間違っています")