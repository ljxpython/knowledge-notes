"""Chapter 6: invoke two compiled subgraphs concurrently with real models."""

import asyncio
from typing import TypedDict

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime

from open_deep_research.configuration import Configuration


load_dotenv()


class ResearcherState(TypedDict):
    topic: str
    summary: str


class ResearcherOutput(TypedDict):
    summary: str


class ParentState(TypedDict):
    topics: list[str]
    summaries: list[str]


configurable_model = init_chat_model(
    configurable_fields=("model", "max_tokens", "api_key"),
)


async def summarize_topic(
    state: ResearcherState,
    runtime: Runtime[Configuration],
):
    settings = runtime.context
    model = configurable_model.with_config(
        {
            "configurable": {
                "model": settings.research_model,
                "max_tokens": 120,
            },
            "tags": ["langsmith:nostream"],
        }
    )
    response = await model.ainvoke(
        [
            HumanMessage(
                content=f"只用一句中文概括这个 LangGraph 学习主题: {state['topic']}"
            )
        ]
    )
    return {"summary": str(response.content)}


researcher_graph = (
    StateGraph(
        ResearcherState,
        context_schema=Configuration,
        input_schema=ResearcherState,
        output_schema=ResearcherOutput,
    )
    .add_node("summarize_topic", summarize_topic)
    .add_edge(START, "summarize_topic")
    .add_edge("summarize_topic", END)
    .compile()
)


async def run_researchers(
    state: ParentState,
    runtime: Runtime[Configuration],
):
    results = await asyncio.gather(
        *(
            researcher_graph.ainvoke(
                {"topic": topic},
                context=runtime.context,
            )
            for topic in state["topics"]
        )
    )
    return {"summaries": [result["summary"] for result in results]}


async def main():
    parent_graph = (
        StateGraph(ParentState, context_schema=Configuration)
        .add_node("run_researchers", run_researchers)
        .add_edge(START, "run_researchers")
        .add_edge("run_researchers", END)
        .compile()
    )
    result = await parent_graph.ainvoke(
        {
            "topics": ["子图隔离状态", "asyncio.gather 并发调用"],
            "summaries": [],
        },
        context=Configuration.from_env(),
    )
    print(f"子图数: {len(result['summaries'])}")
    for summary in result["summaries"]:
        print("- " + summary)


if __name__ == "__main__":
    asyncio.run(main())
