import os
from claude_agent_sdk import (
  ToolPermissionContext,
  PermissionResultAllow,
  PermissionResultDeny
)
from typing import Any


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

def is_contains_dangerous_keyword(command: str) -> bool:
  WARNING_BASH_COMMANDS = ["sudo","chmod", "curl", "wget", "git push","git reset"]

  for keyword in WARNING_BASH_COMMANDS:
    if keyword in command:
      return True
  return False

async def handle_ask_tool_configuration(input_data: dict) -> PermissionResultAllow | PermissionResultDeny:

  command = input_data.get("command", "")

  if not command:
    return PermissionResultDeny(
      behavior="deny",
      message="Bashコマンドが指定されていません",
      interrupt=False
    )

  if is_contains_dangerous_keyword(command):
    print(f"以下のコマンドを実行しようとしていますが許可しますか？\n")
    print(f"使用コマンド: {command} \n")

    user_input_response = input("Your Input [y/N]").strip()

    if (user_input_response == "y") or (user_input_response == "Y"):
      return PermissionResultAllow(updated_input=input_data)
    else:
      return PermissionResultDeny(
        behavior="deny",
        message="ユーザーによってコマンド実行が拒否されました",
        interrupt=False
    )

  return PermissionResultAllow(updated_input=input_data)

async def handle_tool_request(
  tool_name: str,
  input_data: dict[str, Any],
  context: ToolPermissionContext
) -> PermissionResultAllow | PermissionResultDeny:

  if tool_name == "AskUserQuestion":
    return await handle_ask_user_question(input_data)

  if tool_name == "Bash":
    return await handle_ask_tool_configuration(input_data)

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
