"""Chapter 7: allow only one tool through a custom tool-call wrapper."""

import asyncio

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware
from langchain.chat_models import init_chat_model
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool

from open_deep_research.configuration import Configuration


load_dotenv()


@tool
def multiply(left: int, right: int) -> int:
    """Multiply two integers exactly."""
    return left * right


@tool
def blocked_action() -> str:
    """A deliberately unavailable action."""
    return "should never run"


class AllowListedTools(AgentMiddleware):
    """Reject tool calls outside the explicit list."""

    def wrap_tool_call(self, request, handler):
        if request.tool_call["name"] == "multiply":
            return handler(request)
        return ToolMessage(
            content="该工具不在本次允许列表中。",
            name=request.tool_call["name"],
            tool_call_id=request.tool_call["id"],
            status="error",
        )

    async def awrap_tool_call(self, request, handler):
        if request.tool_call["name"] == "multiply":
            return await handler(request)
        return ToolMessage(
            content="该工具不在本次允许列表中。",
            name=request.tool_call["name"],
            tool_call_id=request.tool_call["id"],
            status="error",
        )


async def main() -> None:
    settings = Configuration.from_env()
    agent = create_agent(
        init_chat_model(model=settings.research_model, max_tokens=80),
        tools=[multiply, blocked_action],
        middleware=[AllowListedTools()],
        system_prompt="计算必须调用 multiply；绝不调用 blocked_action。",
    )
    result = await agent.ainvoke({"messages": [("user", "计算 6 乘以 7。 ")]})
    assert "42" in str(result["messages"][-1].content)
    print("允许列表 middleware 已放行 multiply")


if __name__ == "__main__":
    asyncio.run(main())
