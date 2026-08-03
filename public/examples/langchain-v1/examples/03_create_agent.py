"""Chapter 3: the standard LangChain agent loop and structured response."""

import asyncio

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from open_deep_research.configuration import Configuration


load_dotenv()


@tool
def multiply(left: int, right: int) -> int:
    """Multiply two integers exactly."""
    return left * right


class CalculationAnswer(BaseModel):
    result: int = Field(description="The exact multiplication result.")
    explanation: str = Field(description="One concise Chinese explanation.")


async def main():
    settings = Configuration.from_env()
    model = init_chat_model(
        model=settings.research_model,
        max_tokens=160,
    )
    agent = create_agent(
        model=model,
        tools=[multiply],
        system_prompt="你是计算助手。计算时必须调用 multiply 工具。",
        response_format=CalculationAnswer,
    )
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": "请计算 23 乘以 7。"}]}
    )
    answer = result["structured_response"]
    print(f"结果: {answer.result}")
    print("说明: " + answer.explanation)


if __name__ == "__main__":
    asyncio.run(main())
