"""Chapter 2: LCEL composition and Runnable data transformation."""

import asyncio

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import (
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)

from open_deep_research.configuration import Configuration


load_dotenv()


async def main():
    settings = Configuration.from_env()
    parallel = RunnableParallel(
        uppercase=RunnableLambda(lambda text: text.upper()),
        length=RunnableLambda(len),
    )
    local_result = parallel.invoke("lcel")
    print("并行本地结果: " + str(local_result))

    prepare = (
        RunnableLambda(lambda question: {"question": question.strip()})
        | RunnablePassthrough.assign(
            characters=lambda values: len(values["question"])
        )
    )
    prompt = ChatPromptTemplate.from_template(
        "用两句中文解释问题，并说明它有 {characters} 个字符：{question}"
    )
    chain = prepare | prompt | init_chat_model(
        model=settings.research_model,
        max_tokens=120,
    ) | StrOutputParser()
    answer = await chain.ainvoke("  LCEL 中 | 运算符做什么？  ")
    print("模型回答: " + answer)


if __name__ == "__main__":
    asyncio.run(main())
