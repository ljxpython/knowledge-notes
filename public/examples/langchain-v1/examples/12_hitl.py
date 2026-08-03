"""Chapter 8: pause for local approval before executing an in-memory action."""

import asyncio

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from open_deep_research.configuration import Configuration


load_dotenv()

EXECUTED = []


@tool
def draft_notice(text: str) -> str:
    """Record a notice draft in local memory. This does not send anything."""
    EXECUTED.append(text)
    return "草稿已记录，未发送。"


async def main() -> None:
    settings = Configuration.from_env()
    agent = create_agent(
        init_chat_model(model=settings.research_model, max_tokens=80),
        tools=[draft_notice],
        checkpointer=InMemorySaver(),
        middleware=[HumanInTheLoopMiddleware({"draft_notice": True})],
        system_prompt="必须调用 draft_notice 记录用户提供的草稿。",
    )
    config = {"configurable": {"thread_id": "lesson-hitl"}}
    first = await agent.ainvoke(
        {"messages": [("user", "调用 draft_notice 记录：明天上午十点开会。 ")]}, config=config
    )
    assert first.get("__interrupt__"), first
    final = await agent.ainvoke(
        Command(resume={"decisions": [{"type": "approve"}]}), config=config
    )
    assert EXECUTED and "明天" in EXECUTED[0]
    print(f"审批后结果: {final['messages'][-1].content}")


if __name__ == "__main__":
    asyncio.run(main())
