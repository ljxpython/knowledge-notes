"""Chapter 2: verify the message protocol without a model call."""

from langchain_core.messages import AIMessage, ToolMessage


def main() -> None:
    tool_call = {"name": "multiply", "args": {"left": 23, "right": 7}, "id": "call-1"}
    request = AIMessage(content="", tool_calls=[tool_call])
    result = ToolMessage(content="161", name="multiply", tool_call_id="call-1")

    assert request.tool_calls[0]["id"] == result.tool_call_id
    print(f"工具协议正确: {result.name} -> {result.content}")


if __name__ == "__main__":
    main()
