"""Chapter 4: a tiny real ReAct loop with one bound tool."""

import asyncio

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.runtime import Runtime
from langgraph.types import Command

from open_deep_research.configuration import Configuration


load_dotenv()


@tool
def multiply_by_two(value: int) -> str:
    """Multiply the input integer by two."""
    return str(value * 2)


configurable_model = init_chat_model(
    configurable_fields=("model", "max_tokens", "api_key"),
)


async def agent(state: MessagesState, runtime: Runtime[Configuration]):
    settings = runtime.context
    model = configurable_model.with_config(
        {
            "configurable": {
                "model": settings.research_model,
                "max_tokens": 120,
            },
            "tags": ["langsmith:nostream"],
        }
    ).bind_tools([multiply_by_two])
    response = await model.ainvoke(state["messages"])
    if response.tool_calls:
        return Command(update={"messages": [response]}, goto="run_tools")
    return {"messages": [response]}


async def run_tools(state: MessagesState):
    last_message = state["messages"][-1]
    outputs = []
    for tool_call in last_message.tool_calls:
        result = multiply_by_two.invoke(tool_call["args"])
        outputs.append(
            ToolMessage(
                content=result,
                name=tool_call["name"],
                tool_call_id=tool_call["id"],
            )
        )
    return Command(update={"messages": outputs}, goto="agent")


async def main():
    graph = (
        StateGraph(MessagesState, context_schema=Configuration)
        .add_node("agent", agent)
        .add_node("run_tools", run_tools)
        .add_edge(START, "agent")
        .add_edge("run_tools", "agent")
        .compile()
    )
    result = await graph.ainvoke(
        {
            "messages": [
                HumanMessage(
                    content="请使用可用工具计算 21 的两倍，然后只用一句中文给出答案。"
                )
            ]
        },
        context=Configuration.from_env(),
    )
    print(f"消息数: {len(result['messages'])}")
    print("最终答复: " + str(result["messages"][-1].content))


if __name__ == "__main__":
    asyncio.run(main())
