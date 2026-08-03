"""Chapter 5: let a standard agent use a local retriever as a tool."""

import asyncio

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool

from open_deep_research.configuration import Configuration
from rag_data import build_retriever


load_dotenv()


async def main():
    settings = Configuration.from_env()
    retriever = build_retriever()

    @tool
    def search_learning_notes(query: str) -> str:
        """Search the local LangChain and LangGraph learning notes."""
        documents = retriever.invoke(query)
        return "\n\n".join(
            f"[{document.metadata['source']}] {document.page_content}"
            for document in documents
        )

    agent = create_agent(
        model=init_chat_model(model=settings.research_model, max_tokens=180),
        tools=[search_learning_notes],
        system_prompt=(
            "你是学习资料问答助手。回答知识库问题前必须调用 "
            "search_learning_notes；只依据工具返回内容回答。"
        ),
    )
    result = await agent.ainvoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": "LangChain 和 LangGraph 在这个知识库中如何分工？",
                }
            ]
        }
    )
    print("最终回答: " + str(result["messages"][-1].content))


if __name__ == "__main__":
    asyncio.run(main())
