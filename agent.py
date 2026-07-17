import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, AssistantMessage, ResultMessage

async def main():
  async for message in query(
    prompt="あいさつして", # 指示は都度書き直す
    options=ClaudeAgentOptions(
      allowed_tools=["Read", "Edit", "Glob"],
      permission_mode="acceptEdits",
    ),
  ):
    if isinstance(message, AssistantMessage):
      for block in message.content:
        if hasattr(block, "text"):
          print(block.text)
        elif hasattr(block, "name"):
          print(f"Tool: {block.name}")
    elif isinstance(message, ResultMessage):
      print(f"Done: {message.subtype}")


asyncio.run(main())