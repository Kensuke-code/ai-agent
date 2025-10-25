# 必要なライブラリをインポート
import os
from dotenv import load_dotenv
from strands import Agent
from strands.tools import tool
from tavily import TavilyClient
from bedrock_agentcore.runtime import BedrockAgentCoreApp
import datetime
from zoneinfo import ZoneInfo

# .envファイルから環境変数をロード
load_dotenv()

# Define a tool to search the web
@tool
def search_tavily(query: str):
    client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))
    return client.search(query)

# 今日の日付を正しく回答できるようにするため
@tool
def calender():
    return datetime.datetime.now(ZoneInfo("Asia/Tokyo"))

# Strandsでエージェントを作成
agent = Agent(
    "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
    system_prompt="聞かれたことに対して根拠となる情報リソースを提示しながら回答すること。今日の日付は常に最新の日付を確認して返答すること",
    tools=[search_tavily,calender]
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
