"""Chapter 14 example: current LangGraph runtime context API."""

import asyncio

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.runtime import Runtime

from open_deep_research.configuration import Configuration


load_dotenv()


configurable_model = init_chat_model(
    configurable_fields=("model", "max_tokens", "api_key"),
)


async def answer(
    state: MessagesState,
    runtime: Runtime[Configuration],
):
    """Read application settings from typed runtime context."""
    settings = runtime.context
    model = configurable_model.with_config(
        {
            "configurable": {
                "model": settings.research_model,
                "max_tokens": settings.research_model_max_tokens,
            },
            "tags": ["langsmith:nostream", "learning:runtime-context"],
        }
    )
    response = await model.ainvoke(state["messages"])
    return {"messages": [response]}


graph = (
    StateGraph(MessagesState, context_schema=Configuration)
    .add_node("answer", answer)
    .add_edge(START, "answer")
    .add_edge("answer", END)
    .compile()
)


async def main():
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content="用一句中文解释 Runtime context。")]},
        context=Configuration.from_env(),
        config={"tags": ["learning", "chapter-14"]},
    )
    print(result["messages"][-1].content)


if __name__ == "__main__":
    asyncio.run(main())
