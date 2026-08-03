"""Chapter 1: one real model call inside a minimal LangGraph agent."""

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


async def answer(state: MessagesState, runtime: Runtime[Configuration]):
    """Call the configured real model and append its reply to message state."""
    settings = runtime.context
    model = configurable_model.with_config(
        {
            "configurable": {
                "model": settings.research_model,
                "max_tokens": 80,
            },
            "tags": ["langsmith:nostream"],
        }
    )
    response = await model.ainvoke(state["messages"])
    return {"messages": [response]}


async def main():
    graph = (
        StateGraph(MessagesState, context_schema=Configuration)
        .add_node("answer", answer)
        .add_edge(START, "answer")
        .add_edge("answer", END)
        .compile()
    )
    result = await graph.ainvoke(
        {
            "messages": [
                HumanMessage(content="只用一句中文说明 LangGraph 的作用。"),
            ]
        },
        context=Configuration.from_env(),
    )
    print(result["messages"][-1].content)


if __name__ == "__main__":
    asyncio.run(main())
