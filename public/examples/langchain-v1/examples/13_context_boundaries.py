"""Chapter 9: show that runtime context is not automatically model-visible state."""

from dataclasses import dataclass

from langchain.agents import create_agent
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage


@dataclass
class UserContext:
    user_id: str


def main() -> None:
    agent = create_agent(
        FakeMessagesListChatModel(responses=[AIMessage(content="ok")]),
        context_schema=UserContext,
    )
    result = agent.invoke(
        {"messages": [("user", "只回答 ok")]}, context=UserContext(user_id="private-user")
    )
    serialized_messages = str(result["messages"])
    assert "private-user" not in serialized_messages
    print("context 只供 runtime 使用，未自动写入 messages")


if __name__ == "__main__":
    main()
