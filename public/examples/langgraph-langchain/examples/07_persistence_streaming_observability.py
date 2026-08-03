"""Chapter 7: persist one thread, stream events, inspect saved state."""

import asyncio

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.runtime import Runtime

from open_deep_research.configuration import Configuration


load_dotenv()


configurable_model = init_chat_model(
    configurable_fields=("model", "max_tokens", "api_key"),
)


async def reply(state: MessagesState, runtime: Runtime[Configuration]):
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
    response = await model.ainvoke(state["messages"])
    return {"messages": [response]}


memory = InMemorySaver()
graph = (
    StateGraph(MessagesState, context_schema=Configuration)
    .add_node("reply", reply)
    .add_edge(START, "reply")
    .add_edge("reply", END)
    .compile(checkpointer=memory)
)


async def count_events(input_value, config, context):
    count = 0
    stream = await graph.astream_events(
        input_value,
        config=config,
        context=context,
        version="v3",
    )
    async for _event in stream:
        count += 1
    return count


async def main():
    config = {"configurable": {"thread_id": "learning-thread-1"}}
    context = Configuration.from_env()

    first_input = {
        "messages": [HumanMessage(content="你好，我叫老李。请记住我的名字。")]
    }
    event_count = await count_events(first_input, config, context)

    second_result = await graph.ainvoke(
        {
            "messages": [HumanMessage(content="我刚才说我叫什么？只用一句中文回答。")]
        },
        config=config,
        context=context,
    )
    snapshot = graph.get_state(config)

    print(f"事件数: {event_count}")
    print("第二轮答复: " + str(second_result["messages"][-1].content))
    print(f"持久化消息数: {len(snapshot.values['messages'])}")


if __name__ == "__main__":
    asyncio.run(main())
