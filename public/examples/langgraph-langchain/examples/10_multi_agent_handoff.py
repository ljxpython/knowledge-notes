"""Chapter 15: structured handoff between a coordinator and researcher subgraphs."""

import asyncio
from typing import TypedDict

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from pydantic import BaseModel, Field

from open_deep_research.configuration import Configuration


load_dotenv()


class Subtask(BaseModel):
    """A coordinator-to-researcher handoff contract."""

    topic: str = Field(description="One focused research topic in Chinese.")
    question: str = Field(description="The exact question this researcher must answer.")
    expected_evidence: str = Field(description="What evidence or explanation to return.")


class ResearchPlan(BaseModel):
    """Coordinator output that decides the subgraph inputs."""

    brief: str = Field(description="A concise restatement of the user's goal.")
    tasks: list[Subtask] = Field(
        description="Exactly two independent research tasks.", min_length=2, max_length=2
    )


class Finding(BaseModel):
    """A researcher-to-coordinator handoff contract."""

    topic: str
    answer: str = Field(description="A factual answer in at most two Chinese sentences.")
    evidence: list[str] = Field(
        description="Two concise supporting points.", min_length=2, max_length=2
    )
    limitation: str = Field(description="One uncertainty or scope limitation.")


class FinalAnswer(BaseModel):
    """The public response contract returned by the coordinator."""

    answer: str = Field(description="A concise Chinese answer for the user.")
    key_points: list[str] = Field(
        description="Exactly three user-facing key points.", min_length=3, max_length=3
    )


class UserInput(TypedDict):
    """Public graph input: only information the model needs to answer."""

    user_profile: str
    user_question: str


class CoordinatorState(UserInput):
    plan: ResearchPlan
    findings: list[Finding]
    final_answer: FinalAnswer


class ResearcherInput(TypedDict):
    """Explicit projection from coordinator state into a researcher subgraph."""

    user_profile: str
    user_question: str
    task: Subtask


class ResearcherState(ResearcherInput):
    finding: Finding


class ResearcherOutput(TypedDict):
    finding: Finding


class CoordinatorOutput(TypedDict):
    final_answer: FinalAnswer


configurable_model = init_chat_model(
    configurable_fields=("model", "max_tokens", "api_key"),
)


def model_for(settings: Configuration, max_tokens: int):
    return configurable_model.with_config(
        {
            "configurable": {
                "model": settings.research_model,
                "max_tokens": max_tokens,
            },
            "tags": ["langsmith:nostream", "learning:multi-agent-handoff"],
        }
    )


async def research_one(
    state: ResearcherState,
    runtime: Runtime[Configuration],
) -> ResearcherOutput:
    task = state["task"]
    finding = await model_for(runtime.context, 160).with_structured_output(
        Finding
    ).ainvoke(
        [
            HumanMessage(
                content=(
                    "你是研究子 agent。只完成分配给你的一个任务，不要重新规划。\n"
                    f"用户画像: {state['user_profile']}\n"
                    f"用户问题: {state['user_question']}\n"
                    f"任务主题: {task.topic}\n"
                    f"任务问题: {task.question}\n"
                    f"要求证据: {task.expected_evidence}"
                )
            )
        ]
    )
    return {"finding": finding}


researcher_graph = (
    StateGraph(
        ResearcherState,
        context_schema=Configuration,
        input_schema=ResearcherInput,
        output_schema=ResearcherOutput,
    )
    .add_node("research_one", research_one)
    .add_edge(START, "research_one")
    .add_edge("research_one", END)
    .compile()
)


async def make_plan(
    state: CoordinatorState,
    runtime: Runtime[Configuration],
):
    plan = await model_for(runtime.context, 180).with_structured_output(
        ResearchPlan
    ).ainvoke(
        [
            HumanMessage(
                content=(
                    "你是主协调 agent。把用户问题拆成两个互补、可并行的研究任务。\n"
                    f"用户画像: {state['user_profile']}\n"
                    f"用户问题: {state['user_question']}"
                )
            )
        ]
    )
    return {"plan": plan}


async def run_researchers(
    state: CoordinatorState,
    runtime: Runtime[Configuration],
):
    results = await asyncio.gather(
        *(
            researcher_graph.ainvoke(
                {
                    "user_profile": state["user_profile"],
                    "user_question": state["user_question"],
                    "task": task,
                },
                context=runtime.context,
            )
            for task in state["plan"].tasks
        )
    )
    return {"findings": [result["finding"] for result in results]}


async def write_answer(
    state: CoordinatorState,
    runtime: Runtime[Configuration],
) -> CoordinatorOutput:
    findings = "\n".join(
        finding.model_dump_json() for finding in state["findings"]
    )
    final_answer = await model_for(runtime.context, 220).with_structured_output(
        FinalAnswer
    ).ainvoke(
        [
            HumanMessage(
                content=(
                    "你是主协调 agent。仅依据下列子 agent 的结构化 finding 回答用户；"
                    "不要编造未提供的证据，并保留必要限制。\n"
                    f"用户画像: {state['user_profile']}\n"
                    f"用户问题: {state['user_question']}\n"
                    f"研究计划: {state['plan'].model_dump_json()}\n"
                    f"子 agent 结果:\n{findings}"
                )
            )
        ]
    )
    return {"final_answer": final_answer}


coordinator_graph = (
    StateGraph(
        CoordinatorState,
        context_schema=Configuration,
        input_schema=UserInput,
        output_schema=CoordinatorOutput,
    )
    .add_node("make_plan", make_plan)
    .add_node("run_researchers", run_researchers)
    .add_node("write_answer", write_answer)
    .add_edge(START, "make_plan")
    .add_edge("make_plan", "run_researchers")
    .add_edge("run_researchers", "write_answer")
    .add_edge("write_answer", END)
    .compile()
)


async def main():
    result = await coordinator_graph.ainvoke(
        {
            "user_profile": "Python 初学者，正在学习当前 open_deep_research 项目。",
            "user_question": "主 agent 和 researcher 子 agent 怎样通过结构化数据协作？",
        },
        context=Configuration.from_env(),
    )
    answer = result["final_answer"]
    print("最终回答: " + answer.answer)
    print("要点: " + " | ".join(answer.key_points))


if __name__ == "__main__":
    asyncio.run(main())
