"""Chapter 4: store a user preference across two different threads."""

import asyncio
from dataclasses import dataclass

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import ToolRuntime, tool
from langgraph.store.memory import InMemoryStore

from open_deep_research.configuration import Configuration


load_dotenv()


@dataclass
class UserContext:
    user_id: str


@tool
def save_language(language: str, runtime: ToolRuntime[UserContext]) -> str:
    """Save the current user's preferred response language."""
    runtime.store.put(("preferences", runtime.context.user_id), "profile", {"language": language})
    return f"已保存语言偏好：{language}"


@tool
def get_language(runtime: ToolRuntime[UserContext]) -> str:
    """Read the current user's preferred response language."""
    item = runtime.store.get(("preferences", runtime.context.user_id), "profile")
    return str(item.value if item else {"language": "未设置"})


async def main() -> None:
    settings = Configuration.from_env()
    store = InMemoryStore()
    agent = create_agent(
        init_chat_model(model=settings.research_model, max_tokens=100),
        tools=[save_language, get_language],
        context_schema=UserContext,
        store=store,
        system_prompt="必须调用合适的偏好工具。不要猜测工具返回值。",
    )
    user = UserContext(user_id="lesson-user-a")
    await agent.ainvoke(
        {"messages": [("user", "调用 save_language，把我的偏好保存为中文。")]},
        context=user,
        config={"configurable": {"thread_id": "write-preference"}},
    )
    result = await agent.ainvoke(
        {"messages": [("user", "调用 get_language，告诉我我的语言偏好。")]},
        context=user,
        config={"configurable": {"thread_id": "read-preference"}},
    )
    other = store.get(("preferences", "lesson-user-b"), "profile")
    assert other is None
    assert "中文" in str(result["messages"][-1].content)
    print("跨 thread 偏好: 中文；其他用户不可见")


if __name__ == "__main__":
    asyncio.run(main())
