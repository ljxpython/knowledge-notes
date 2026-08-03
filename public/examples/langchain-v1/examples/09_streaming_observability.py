"""Chapter 5: inspect one Agent run as updates and Runnable events."""

import asyncio

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model

from open_deep_research.configuration import Configuration


load_dotenv()


async def main() -> None:
    settings = Configuration.from_env()
    agent = create_agent(
        init_chat_model(model=settings.research_model, max_tokens=60),
        system_prompt="用一句中文回答。",
        name="learning_stream_agent",
    )
    input_value = {"messages": [("user", "什么是 Agent state？")]}
    config = {"tags": ["learning", "agent-stream"], "metadata": {"lesson": "05"}}

    updates = []
    async for update in agent.astream(input_value, config=config, stream_mode="updates"):
        updates.extend(update)
    assert "model" in updates

    model_starts = []
    async for event in agent.astream_events(input_value, config=config, version="v2"):
        if event["event"] == "on_chat_model_start":
            model_starts.append(event["name"])
    assert model_starts
    print("更新节点: " + ", ".join(updates))
    print("模型事件: " + ", ".join(model_starts))


if __name__ == "__main__":
    asyncio.run(main())
