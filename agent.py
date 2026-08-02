import asyncio
import os
from claude_agent_sdk import (
  query,
  ClaudeAgentOptions,
  ResultMessage,
  ProcessError,
  CLIConnectionError,
  StreamEvent,
  ToolPermissionContext,
  PermissionResultAllow,
  PermissionResultDeny
)
from typing import Any

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


# streaming input mode: https://code.claude.com/docs/en/agent-sdk/python
# yieldは1つだけなので、2回目の呼び出しでStopAsyncIterationになり入力ストリームが終了する
# (複数ターン送りたい場合はyieldを複数書く)
async def build_prompt_stream(text: str):
  yield {
    "type": "user",
    "message": {"role": "user", "content": text},
  }

async def handle_tool_request(
  tool_name: str,
  input_data: dict[str, Any],
  context: ToolPermissionContext
) -> PermissionResultAllow | PermissionResultDeny:
  if tool_name not in ("Write", "Edit"):
    return PermissionResultAllow(updated_input=input_data)

  file_path = input_data.get("file_path", "")
  if not file_path:
    return PermissionResultDeny(
      behavior="deny",
      message="file_pathが指定されていません",
      interrupt=False
    )

  path = os.path.realpath(file_path)

  if path.startswith(("/etc/", "/root/")) or "/.ssh/" in path:
    return PermissionResultDeny(
      behavior="deny",
      message=f"機密領域への書き込みのため、タスクを中断しました: {path}",
      interrupt=True
    )

  if not path.startswith("/app/"):
    return PermissionResultDeny(
      behavior="deny",
      message=f"書き込みは /app/ 配下のみ許可されています: {path}",
      interrupt=False
    )

  return PermissionResultAllow(updated_input=input_data)

###############
# メイン処理
###############
# 複数ユーザー/アプリから同時に呼ばれ、ユーザーごとに接続を張りっぱなしにして
# 連続会話やinterrupt()が必要になったらquery()からClaudeSDKClientに差し替える
# (その場合はユーザーごとに別インスタンスを持つ設計にする)
async def main():
  in_tool = False # ツールの呼び出し

  try:
    session_id = load_session_id()

    async for message in query(
      prompt=build_prompt_stream("このプロジェクトのtest.pyを削除して"), # 指示は都度書き直す

      options=ClaudeAgentOptions(
        model="sonnet",
        resume=session_id,
        include_partial_messages=True,
        disallowed_tools=["Bash(rm *)", "Bash(sudo *)"],
        allowed_tools=["Read", "Grep", "Glob", "WebSearch"], # TODO: AskUserQuestionを追加する
        permission_mode="default", # bypass_permissionsはallowed_toolsとdisallowed_toolsを素通りしてしまうため使わない
        cwd="/app",
        can_use_tool=handle_tool_request
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
