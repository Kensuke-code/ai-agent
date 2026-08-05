import asyncio
import os
from claude_agent_sdk import (
  ClaudeSDKClient,
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


def parse_response(user_input_response: str, options: list) -> str:
  try:
    selected_labels = []

    for number_str in user_input_response.split(","):
      selected_index = int(number_str.strip()) - 1
      if 0 <= selected_index < len(options):
        selected_labels.append(options[selected_index]["label"])

    return ", ".join(selected_labels) if selected_labels else user_input_response
  except ValueError:
    return user_input_response

async def handle_ask_user_question(input_data: dict) -> PermissionResultAllow:
  answers = {}

  for question in input_data.get("questions", []):
    print(f"\n{question['question']}")

    options = question["options"]

    for i, option in enumerate(options):
      print(f" {i + 1}. {option['label']} - {option['description']}")
    if question.get("multiSelect"):
      print("カンマで区切って数字を入力するか、独自の回答を入力してください。")
    else:
      print("数字を入力するか、独自の回答を入力してください。")

    user_input_response = input("Your choice: ").strip()

    answers[question["question"]] = parse_response(user_input_response, options)

  return PermissionResultAllow(
    updated_input={
      **input_data,
      "answers": answers,  # question: 選択したlabel or question: 独自の回答テキスト
    }
  )

async def handle_tool_request(
  tool_name: str,
  input_data: dict[str, Any],
  context: ToolPermissionContext
) -> PermissionResultAllow | PermissionResultDeny:

  if tool_name == "AskUserQuestion":
    return await handle_ask_user_question(input_data)

  if tool_name in ("Write", "Edit"):
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
# 複数ユーザー/アプリから同時に使う場合は、1つのClaudeSDKClientを使い回さず
# ユーザー/セッションごとに別インスタンスを持つこと
EXIT_COMMANDS = ("exit", "quit", "終了")

async def main():
  in_tool = False # ツールの呼び出し
  session_id = load_session_id()

  options = ClaudeAgentOptions(
    model="sonnet",
    resume=session_id,
    include_partial_messages=True,
    disallowed_tools=["Bash(rm *)", "Bash(sudo *)"],
    allowed_tools=["Read", "Grep", "Glob", "WebSearch"],
    permission_mode="default", # bypass_permissionsはallowed_toolsとdisallowed_toolsを素通りしてしまうため使わない
    cwd="/app",
    can_use_tool=handle_tool_request,
  )

  try:
    async with ClaudeSDKClient(options=options) as client:
      user_input = "ディズニーパークのおすすめショップについて教えて。必要であればどちらのパークがいいか聞いて" # 指示は都度書き直す

      while user_input and user_input not in EXIT_COMMANDS:
        await client.query(user_input)

        async for message in client.receive_response():
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
              save_session_id(session_id)
            else:
              print(f"クエリが失敗しました: subtype={message.subtype}, is_error={message.is_error}")

        user_input = input("\n\nYou: ").strip()

    print("\n--- Complete ---")

  except ProcessError as e:
    print(f"セッションの再開に失敗しました。次回起動時にセッションを再生成します： {e}")
    clear_session_id()

  except CLIConnectionError as e:
    print(f"Claude CLIに接続できませんでした： {e}")

asyncio.run(main())
