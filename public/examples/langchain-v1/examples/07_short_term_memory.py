"""Chapter 3: retain one conversation with a checkpoint and thread id."""

import asyncio

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver

from open_deep_research.configuration import Configuration


load_dotenv()


async def main() -> None:
    settings = Configuration.from_env()
    agent = create_agent(
        init_chat_model(model=settings.research_model, max_tokens=80),
        system_prompt="回答简洁。只能根据本次对话中已知的事实回答。",
        checkpointer=InMemorySaver(),
    )
    config = {"configurable": {"thread_id": "lesson-short-memory"}}
    await agent.ainvoke(
        {"messages": [("user", "请记住：我叫小王。只回答已记住。 ")]},
        config=config,
    )
    result = await agent.ainvoke(
        {"messages": [("user", "我叫什么？只输出名字。")]}, config=config
    )
    answer = result["messages"][-1].content
    assert "小王" in str(answer), answer
    print(f"第二轮回答: {answer}")


if __name__ == "__main__":
    asyncio.run(main())
