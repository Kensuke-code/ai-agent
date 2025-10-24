# 必要なライブラリをインポート
import os
from dotenv import load_dotenv
from strands import Agent
from strands.tools import tool
from tavily import TavilyClient
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# .envファイルから環境変数をロード
load_dotenv()

# Define a tool to search the web
@tool
def search_tavily(query: str):
    client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))
    return client.search(query)

# Strandsでエージェントを作成
agent = Agent(
    "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
    system_prompt="You are a helpful assistant that can search the web.",
    tools=[search_tavily]
)

# AgentCoreのサーバーを作成
app = BedrockAgentCoreApp()

# エージェント呼び出し関数を、AgentCoreの開始点に設定
@app.entrypoint
def invoke_agent(payload, context):
    # リクエストのペイロード（中身）からプロンプトを取得
    prompt = payload.get("prompt")
    
    # エージェントを呼び出してレスポンスを返却
    result = agent(prompt)

    print(result.message["content"][0]["text"])
    return {"result": result.message["content"][0]["text"]}

# AgentCoreサーバーを起動
app.run()
