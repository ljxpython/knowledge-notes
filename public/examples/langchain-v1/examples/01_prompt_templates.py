"""Chapter 1: prompt templates and message placeholders."""

import asyncio

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from open_deep_research.configuration import Configuration


load_dotenv()


async def main():
    settings = Configuration.from_env()
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "你是面向 {audience} 的 LangChain 助手。回答要 {style}。"),
            MessagesPlaceholder("history", optional=True),
            ("human", "{question}"),
        ]
    ).partial(audience="Python 初学者", style="简洁且准确")

    chain = prompt | init_chat_model(
        model=settings.research_model,
        max_tokens=120,
    ) | StrOutputParser()
    answer = await chain.ainvoke(
        {
            "history": [
                HumanMessage(content="我在学习 LangChain。"),
                AIMessage(content="好的。"),
            ],
            "question": "ChatPromptTemplate 的作用是什么？",
        }
    )
    print("模型回答: " + answer)


if __name__ == "__main__":
    asyncio.run(main())
