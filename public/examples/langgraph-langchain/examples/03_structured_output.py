"""Chapter 3: one real structured-output call inside a minimal graph."""

import asyncio

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.runtime import Runtime
from pydantic import BaseModel, Field

from open_deep_research.configuration import Configuration


load_dotenv()


class TopicBrief(BaseModel):
    """A tiny schema for learning structured output."""

    title: str = Field(description="A short Chinese title.")
    research_question: str = Field(description="One focused Chinese research question.")
    needs_tools: bool = Field(description="Whether external search/tools are needed.")


configurable_model = init_chat_model(
    configurable_fields=("model", "max_tokens", "api_key"),
)


async def make_brief(state: MessagesState, runtime: Runtime[Configuration]):
    settings = runtime.context
    model = configurable_model.with_config(
        {
            "configurable": {
                "model": settings.research_model,
                "max_tokens": 160,
            },
            "tags": ["langsmith:nostream"],
        }
    )
    structured_model = model.with_structured_output(TopicBrief)
    brief = await structured_model.ainvoke(state["messages"])
    return {"messages": [AIMessage(content=brief.model_dump_json(ensure_ascii=False))]}


async def main():
    graph = (
        StateGraph(MessagesState, context_schema=Configuration)
        .add_node("make_brief", make_brief)
        .add_edge(START, "make_brief")
        .add_edge("make_brief", END)
        .compile()
    )
    result = await graph.ainvoke(
        {
            "messages": [
                HumanMessage(content="我想研究 LangGraph 的状态管理。"),
            ]
        },
        context=Configuration.from_env(),
    )
    print(result["messages"][-1].content)


if __name__ == "__main__":
    asyncio.run(main())
