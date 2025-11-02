import streamlit as st
from services.sidebar import show_sidebar
from services.auth import create_authenticator ,is_login

# ログイン検証
is_login()

# ログイン済みの場合の表示
show_sidebar()

st.set_page_config(
  page_title="",
  page_icon="☕️"
  )

st.title("Kenchobi AI Agentへようこそ!")
st.write("好きなエージェントを選んでね!")

# ログアウトボタン
authenticator = create_authenticator()

if st.session_state.get('authentication_status'):
  authenticator.logout()



