# 必要なライブラリをインポート
from dotenv import load_dotenv
import os, boto3, json, requests
import streamlit as st

# .envファイルから環境変数をロード
load_dotenv(override=True)

# タイトルを描画
st.title("Kenchobi AI Agent")
st.write("何でも聞いてね！")

# チャットボックスを描画
if prompt := st.chat_input("メッセージを入力してね"):

    # ユーザーのプロンプトを表示
    with st.chat_message("user"):
        st.markdown(prompt)

    # エージェントの回答を表示
    with st.chat_message("assistant"):

        # AgentCoreランタイムを呼び出し
        with st.spinner("考え中…"):
            agentcore = boto3.client('bedrock-agentcore')
            response = requests.post(
                url="http://strands:8080/invocations",
                headers={"Content-Type": "application/json"},
                json={"prompt": prompt}
            )

            response_body = response.json()["result"]
            st.write(response_body)