"""Chapter 10: pass a narrow Pydantic task/result contract through a subgraph."""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field


class TaskContract(BaseModel):
    topic: str = Field(min_length=3)
    constraints: list[str] = Field(default_factory=list)


class ResultContract(BaseModel):
    summary: str
    uncertainty: str


class ChildState(TypedDict):
    task: TaskContract
    result: ResultContract


def research_task(state: ChildState) -> dict:
    task = state["task"]
    return {"result": ResultContract(summary=f"已处理：{task.topic}", uncertainty="未调用外部来源")}


child = StateGraph(ChildState)
child.add_node("research", research_task)
child.add_edge(START, "research")
child.add_edge("research", END)
compiled_child = child.compile()


def main() -> None:
    result = compiled_child.invoke({"task": TaskContract(topic="LangGraph 状态", constraints=["中文"])} )
    assert result["result"].summary == "已处理：LangGraph 状态"
    print(result["result"].model_dump_json())


if __name__ == "__main__":
    main()
