"""Chapter 8: a compact mini deep researcher using the prior chapters."""

import asyncio
import operator
from typing import Annotated, Literal

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, MessageLikeRepresentation, ToolMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.runtime import Runtime
from langgraph.types import Command
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from open_deep_research.configuration import Configuration


load_dotenv()


class MiniPlan(BaseModel):
    """A small structured research plan."""

    research_brief: str = Field(description="One focused Chinese research brief.")
    topics: list[str] = Field(
        description="Exactly two focused Chinese subtopics.",
        min_length=2,
        max_length=2,
    )


class MiniState(MessagesState):
    research_brief: str
    topics: list[str]
    summaries: list[str]
    final_report: str
    route_log: Annotated[list[str], operator.add]


class ResearcherState(TypedDict):
    topic: str
    researcher_messages: Annotated[list[MessageLikeRepresentation], operator.add]
    summary: str


class ResearcherOutput(TypedDict):
    summary: str


configurable_model = init_chat_model(
    configurable_fields=("model", "max_tokens", "api_key"),
)


def configured_model(settings: Configuration, max_tokens: int = 180):
    return configurable_model.with_config(
        {
            "configurable": {
                "model": settings.research_model,
                "max_tokens": max_tokens,
            },
            "tags": ["langsmith:nostream"],
        }
    )


def text_content(content) -> str:
    if isinstance(content, list):
        return "".join(
            part.get("text", str(part)) if isinstance(part, dict) else str(part)
            for part in content
        )
    return str(content)


@tool
def record_learning_boundary(boundary: str) -> str:
    """Record one learning boundary before summarizing a research topic."""
    return f"已记录边界: {boundary}"


async def researcher_agent(
    state: ResearcherState,
    runtime: Runtime[Configuration],
) -> Command[Literal["researcher_tools", "__end__"]]:
    model = configured_model(runtime.context)
    has_tool_result = any(
        getattr(message, "type", None) == "tool"
        for message in state.get("researcher_messages", [])
    )
    if not has_tool_result:
        response = await model.bind_tools(
            [record_learning_boundary],
            tool_choice="record_learning_boundary",
        ).ainvoke(
            [
                HumanMessage(
                    content=(
                        f"研究主题: {state['topic']}。先调用工具记录一个学习边界。"
                    )
                )
            ]
        )
        return Command(
            update={"researcher_messages": [response]},
            goto="researcher_tools",
        )

    response = await model.ainvoke(
        state["researcher_messages"]
        + [HumanMessage(content=f"基于工具记录，用一句中文总结: {state['topic']}")]
    )
    return Command(
        update={"researcher_messages": [response], "summary": text_content(response.content)},
        goto=END,
    )


async def researcher_tools(
    state: ResearcherState,
) -> Command[Literal["researcher_agent"]]:
    last_message = state["researcher_messages"][-1]
    outputs = []
    for tool_call in last_message.tool_calls:
        outputs.append(
            ToolMessage(
                content=record_learning_boundary.invoke(tool_call["args"]),
                name=tool_call["name"],
                tool_call_id=tool_call["id"],
            )
        )
    return Command(update={"researcher_messages": outputs}, goto="researcher_agent")


researcher_graph = (
    StateGraph(
        ResearcherState,
        context_schema=Configuration,
        input_schema=ResearcherState,
        output_schema=ResearcherOutput,
    )
    .add_node("researcher_agent", researcher_agent)
    .add_node("researcher_tools", researcher_tools)
    .add_edge(START, "researcher_agent")
    .compile()
)


async def make_plan(
    state: MiniState,
    runtime: Runtime[Configuration],
) -> Command[Literal["run_researchers"]]:
    model = configured_model(runtime.context).with_structured_output(MiniPlan)
    plan = await model.ainvoke(
        state["messages"]
        + [
            HumanMessage(
                content=(
                    "把用户学习目标整理成一个 research_brief 和两个子主题，"
                    "必须聚焦当前 open_deep_research 项目。"
                )
            )
        ]
    )
    return Command(
        update={
            "research_brief": plan.research_brief,
            "topics": plan.topics,
            "route_log": ["make_plan -> run_researchers"],
        },
        goto="run_researchers",
    )


async def run_researchers(
    state: MiniState,
    runtime: Runtime[Configuration],
) -> Command[Literal["write_final"]]:
    results = await asyncio.gather(
        *(
            researcher_graph.ainvoke(
                {
                    "topic": topic,
                    "researcher_messages": [],
                    "summary": "",
                },
                context=runtime.context,
            )
            for topic in state["topics"]
        )
    )
    return Command(
        update={
            "summaries": [result["summary"] for result in results],
            "route_log": ["run_researchers -> write_final"],
        },
        goto="write_final",
    )


async def write_final(state: MiniState, runtime: Runtime[Configuration]):
    response = await configured_model(runtime.context, max_tokens=240).ainvoke(
        [
            HumanMessage(
                content=(
                    "请用三句中文写一个迷你研究报告。\n"
                    f"研究 brief: {state['research_brief']}\n"
                    f"研究摘要: {state['summaries']}"
                )
            )
        ]
    )
    return {
        "final_report": text_content(response.content),
        "messages": [response],
        "route_log": ["write_final -> END"],
    }


memory = InMemorySaver()
mini_researcher = (
    StateGraph(MiniState, context_schema=Configuration)
    .add_node("make_plan", make_plan)
    .add_node("run_researchers", run_researchers)
    .add_node("write_final", write_final)
    .add_edge(START, "make_plan")
    .add_edge("write_final", END)
    .compile(checkpointer=memory)
)


async def main():
    config = {"configurable": {"thread_id": "mini-researcher-learning"}}
    context = Configuration.from_env()
    input_value = {
        "messages": [
            HumanMessage(
                content=(
                    "我想通过 open_deep_research 学会 LangGraph 的工具循环和子图并发。"
                )
            )
        ],
        "route_log": [],
        "summaries": [],
    }

    event_count = 0
    stream = await mini_researcher.astream_events(
        input_value,
        config=config,
        context=context,
        version="v3",
    )
    async for _event in stream:
        event_count += 1

    snapshot = mini_researcher.get_state(config)
    values = snapshot.values
    print(f"事件数: {event_count}")
    print("主题: " + " | ".join(values["topics"]))
    print("路由: " + " | ".join(values["route_log"]))
    print("摘要数: " + str(len(values["summaries"])))
    print("最终报告: " + values["final_report"])
    print("持久化消息数: " + str(len(values["messages"])))


if __name__ == "__main__":
    asyncio.run(main())
