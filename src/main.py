import asyncio
from claude_agent_sdk import (
  ClaudeSDKClient,
  ClaudeAgentOptions,
  ResultMessage,
  ProcessError,
  CLIConnectionError,
  StreamEvent,
)
from session import save_session_id, load_session_id, clear_session_id
from permissions import handle_tool_request

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
    disallowed_tools=["Bash(rm *)"],
    allowed_tools=["Read", "Grep", "Glob", "WebSearch"],
    permission_mode="default", # bypass_permissionsはallowed_toolsとdisallowed_toolsを素通りしてしまうため使わない
    cwd="/app",
    can_use_tool=handle_tool_request,
  )

  try:
    async with ClaudeSDKClient(options=options) as client:
      user_input = "今日のディズニーシーのアテンダンスは？"

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
