"""Chapter 5: assemble project tools, then run one safe real tool loop."""

import asyncio

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, ToolMessage

from open_deep_research.configuration import Configuration
from open_deep_research.utils import get_all_tools, get_api_key_for_model


load_dotenv()


configurable_model = init_chat_model(
    configurable_fields=("model", "max_tokens", "api_key"),
)


def tool_name(tool):
    return tool.name if hasattr(tool, "name") else tool.get("name", "web_search")


async def main():
    settings = Configuration.from_env()
    tool_context = Configuration.model_validate(
        {**settings.model_dump(), "search_api": "none"}
    )
    tools = await get_all_tools(tool_context)
    print("可用工具: " + ", ".join(tool_name(tool) for tool in tools))

    think_tool = next(tool for tool in tools if tool_name(tool) == "think_tool")
    model = configurable_model.with_config(
        {
            "configurable": {
                "model": settings.research_model,
                "max_tokens": 160,
                "api_key": get_api_key_for_model(settings.research_model, settings),
            },
            "tags": ["langsmith:nostream"],
        }
    ).bind_tools([think_tool])

    messages = [
        HumanMessage(
            content=(
                "请先调用 think_tool，反思学习搜索与 MCP 时最该关注的一个边界，"
                "然后用一句中文总结。"
            )
        )
    ]
    first_response = await model.ainvoke(messages)
    messages.append(first_response)
    print(f"工具调用数: {len(first_response.tool_calls)}")

    tool_outputs = []
    for tool_call in first_response.tool_calls:
        result = think_tool.invoke(tool_call["args"])
        tool_outputs.append(
            ToolMessage(
                content=result,
                name=tool_call["name"],
                tool_call_id=tool_call["id"],
            )
        )

    final_response = await model.ainvoke(messages + tool_outputs)
    print("最终答复: " + str(final_response.content))


if __name__ == "__main__":
    asyncio.run(main())
