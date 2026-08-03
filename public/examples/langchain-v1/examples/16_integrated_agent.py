"""Chapter 11: combine context, memory, middleware, HITL, streaming, and schema output."""

import asyncio
from dataclasses import dataclass
from typing import Annotated

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware, ModelCallLimitMiddleware
from langchain.chat_models import init_chat_model
from langchain.tools import ToolRuntime, tool
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.types import Command
from typing_extensions import TypedDict

from open_deep_research.configuration import Configuration


load_dotenv()


@dataclass
class UserContext:
    user_id: str


class AssistantReply(TypedDict):
    language: Annotated[str, "The user's saved response language."]
    message: Annotated[str, "A concise Chinese confirmation."]


@tool
def save_language(language: str, runtime: ToolRuntime[UserContext]) -> str:
    """Save the authenticated user's preferred response language in local memory."""
    runtime.store.put(("preferences", runtime.context.user_id), "profile", {"language": language})
    return f"已保存偏好：{language}"


@tool
def get_language(runtime: ToolRuntime[UserContext]) -> str:
    """Read the authenticated user's preferred response language from local memory."""
    item = runtime.store.get(("preferences", runtime.context.user_id), "profile")
    return str(item.value if item else {"language": "未设置"})


async def main() -> None:
    settings = Configuration.from_env()
    agent = create_agent(
        init_chat_model(model=settings.research_model, max_tokens=180),
        tools=[save_language, get_language],
        context_schema=UserContext,
        response_format=AssistantReply,
        checkpointer=InMemorySaver(),
        store=InMemoryStore(),
        middleware=[
            ModelCallLimitMiddleware(run_limit=5, exit_behavior="error"),
            HumanInTheLoopMiddleware({"save_language": True}),
        ],
        system_prompt=(
            "当用户要求设置语言时，必须先调用 save_language；随后调用 get_language。"
            "最终按结构化响应给出确认。"
        ),
    )
    config = {
        "configurable": {"thread_id": "lesson-integrated"},
        "tags": ["learning", "integrated-agent"],
        "metadata": {"lesson": "11"},
    }
    context = UserContext(user_id="lesson-user")
    first = await agent.ainvoke(
        {"messages": [("user", "把我的回答语言设置为中文，然后确认。 ")]},
        config=config,
        context=context,
    )
    assert first.get("__interrupt__"), first

    updates = []
    async for update in agent.astream(
        Command(resume={"decisions": [{"type": "approve"}]}),
        config=config,
        context=context,
        stream_mode="updates",
    ):
        updates.extend(update)
    state = await agent.aget_state(config)
    reply = state.values["structured_response"]
    assert reply["language"] == "中文"
    assert updates
    print(reply)
    print("恢复后的更新节点: " + ", ".join(updates))


if __name__ == "__main__":
    asyncio.run(main())
