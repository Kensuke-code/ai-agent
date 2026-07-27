import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage, TextBlock

SESSION_FILE = "session_id.txt"

# メソッド
def save_session_id(session_id):
  with open(SESSION_FILE, "w") as f:
    f.write(session_id)


def load_session_id():
  try:
    with open(SESSION_FILE, "r") as f:
      session_id = f.read().strip()
      return session_id if session_id else None # 空文字列ならNoneにする
  except FileNotFoundError:
    print("セッションのファイルが見つかりません")
    return None

# メイン処理
async def main():

  session_id = load_session_id()

  async for message in query(
    prompt="行き方のところネット検索できない？", # 指示は都度書き直す
    options=ClaudeAgentOptions(
      allowed_tools=["Read", "Edit", "Glob", "WebSearch"],
      permission_mode="acceptEdits",
      resume=session_id
    ),
  ):
    if isinstance(message, AssistantMessage):
      for block in message.content:
        if isinstance(block, TextBlock):
          print(block.text)
    elif isinstance(message, ResultMessage):
      session_id = message.session_id
      if message.subtype == "success":
        save_session_id(session_id)
      else:
        print(f"クエリが失敗しました: subtype={message.subtype}, is_error={message.is_error}")

asyncio.run(main())
