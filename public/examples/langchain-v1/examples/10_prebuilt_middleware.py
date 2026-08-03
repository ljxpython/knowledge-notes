"""Chapter 6: configure prebuilt safeguards around a normal Agent call."""

import asyncio

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware, SummarizationMiddleware
from langchain.chat_models import init_chat_model

from open_deep_research.configuration import Configuration


load_dotenv()


async def main() -> None:
    settings = Configuration.from_env()
    model = init_chat_model(model=settings.research_model, max_tokens=60)
    agent = create_agent(
        model,
        system_prompt="用一句中文回答。",
        middleware=[
            SummarizationMiddleware(model=model, trigger=("messages", 8), keep=("messages", 4)),
            ModelCallLimitMiddleware(run_limit=2, thread_limit=4, exit_behavior="error"),
        ],
    )
    result = await agent.ainvoke({"messages": [("user", "解释模型调用上限。 ")]})
    assert result["messages"][-1].content
    print("预制 middleware 正常路径完成")


if __name__ == "__main__":
    asyncio.run(main())
