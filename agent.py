import asyncio
import os
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage, ProcessError, CLIConnectionError, StreamEvent

SESSION_FILE = "session_id.txt"

###############
# メソッド
###############
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

def clear_session_id():
  if os.path.exists(SESSION_FILE):
    os.remove(SESSION_FILE)


###############
# メイン処理
###############
async def main():
  in_tool = False

  try:
    session_id = load_session_id()

    async for message in query(
      prompt="浦安市のおすすめスポットを紹介して", # 指示は都度書き直す

      options=ClaudeAgentOptions(
        allowed_tools=["Read", "Edit", "Glob", "WebSearch"],
        permission_mode="acceptEdits",
        resume=session_id,
        include_partial_messages=True
      ),
    ):
      if isinstance(message, StreamEvent):
        event = message.event
        event_type = event.get("type")

        if event_type == "content_block_start":
          content_block = event.get("content_block", {})
          if content_block.get("type") == "tool_use":
            tool_name = content_block.get("name")
            print(f"\n[Using Tool: {tool_name}]...  ", end="", flush=True)
            in_tool = True

        elif event_type == "content_block_delta":
          delta = event.get("delta", {})
          if delta.get("type") == "text_delta" and not in_tool:
            print(delta.get("text", ""), end="", flush=True)

        elif event_type == "content_block_stop":
          if in_tool:
            print("Done", flush=True)
            in_tool = False

      elif isinstance(message, ResultMessage):
        session_id = message.session_id

        if message.subtype == "success":
          print("\n\n--- Complete ---")
          save_session_id(session_id)
        else:
          print(f"クエリが失敗しました: subtype={message.subtype}, is_error={message.is_error}")

  except ProcessError as e:
    print(f"セッションの再開に失敗しました。次回起動時にセッションを再生成します： {e}")
    clear_session_id()

  except CLIConnectionError as e:
    print(f"Claude CLIに接続できませんでした： {e}")

asyncio.run(main())
