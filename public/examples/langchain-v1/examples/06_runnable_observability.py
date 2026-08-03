"""Chapter 6: stream a Runnable chain and inspect its event hierarchy."""

import asyncio

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from open_deep_research.configuration import Configuration


load_dotenv()


async def main():
    settings = Configuration.from_env()
    chain = (
        ChatPromptTemplate.from_template("用一句中文解释：{question}")
        | init_chat_model(model=settings.research_model, max_tokens=100)
        | StrOutputParser()
    ).with_config(
        {
            "tags": ["learning", "langchain-runnable-events"],
            "metadata": {"lesson": "06"},
        }
    )
    event_names = []
    async for event in chain.astream_events(
        {"question": "RunnableConfig 中 tags 的作用"},
        version="v2",
    ):
        if event["event"].endswith("_start"):
            event_names.append(event["name"])
    print("启动事件: " + " -> ".join(event_names))


if __name__ == "__main__":
    asyncio.run(main())
