# 必要なライブラリをインポート
from dotenv import load_dotenv
import os, boto3, json, requests
import streamlit as st

# .envファイルから環境変数をロード
load_dotenv(override=True)

# タイトルを描画
st.title("Kenchobi AI Agent")
st.write("何でも聞いてね！")

# チャットログを保存したセッション情報を初期化
if "chat_log" not in st.session_state:
    st.session_state.chat_log = []

# チャットボックスを描画
if prompt := st.chat_input("メッセージを入力してね"):

    # 以前のチャットログを表示
    for chat in st.session_state.chat_log:
        with st.chat_message(chat["name"]):
            st.write(chat["msg"])

    # ユーザーのプロンプトを表示
    with st.chat_message("user"):
        st.markdown(prompt)


    # AgentCoreランタイムを呼び出し
    with st.spinner("考え中…"):
        agentcore = boto3.client('bedrock-agentcore')
        response = requests.post(
            url="http://strands:8080/invocations",
            headers={"Content-Type": "application/json"},
            json={"prompt": prompt}
        )

        result = response.json()["result"]

        # エージェントの回答を表示
        with st.chat_message("assistant"):
          st.write(result)

    # セッションにチャットログを追加
    st.session_state.chat_log.append({"name": "user", "msg": prompt})
    st.session_state.chat_log.append({"name": "assistant", "msg": result})