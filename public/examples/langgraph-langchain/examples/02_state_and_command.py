"""Chapter 2: state reducers and Command routing with one real model call."""

import asyncio
import operator
from typing import Annotated, Literal

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.runtime import Runtime
from langgraph.types import Command

from open_deep_research.configuration import Configuration


load_dotenv()


class LearningState(MessagesState):
    """Conversation state plus an append-only record of graph routing."""

    route_log: Annotated[list[str], operator.add]


configurable_model = init_chat_model(
    configurable_fields=("model", "max_tokens", "api_key"),
)


async def answer(
    state: LearningState,
    runtime: Runtime[Configuration],
) -> Command[Literal["finish"]]:
    """Call the real model, update state, then choose the next node."""
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
    return Command(
        update={
            "messages": [response],
            "route_log": ["answer -> finish"],
        },
        goto="finish",
    )


def finish(_: LearningState):
    """Append one local state update, then use its static edge to end."""
    return {"route_log": ["finish -> END"]}


async def main():
    graph = (
        StateGraph(LearningState, context_schema=Configuration)
        .add_node("answer", answer)
        .add_node("finish", finish)
        .add_edge(START, "answer")
        .add_edge("finish", END)
        .compile()
    )
    result = await graph.ainvoke(
        {
            "messages": [
                HumanMessage(content="只用一句中文解释状态机为什么适合 Agent。"),
            ],
            "route_log": [],
        },
        context=Configuration.from_env(),
    )
    print(f"消息数: {len(result['messages'])}")
    print("路由: " + " | ".join(result["route_log"]))
    print("答复: " + str(result["messages"][-1].content))


if __name__ == "__main__":
    asyncio.run(main())
