"""Small local corpus shared by the RAG learning examples."""

from langchain.embeddings import init_embeddings
from langchain_core.documents import Document
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_text_splitters import RecursiveCharacterTextSplitter


def build_retriever():
    documents = [
        Document(
            page_content=(
                "LangChain 提供模型、提示词、工具、Agent、检索器等组件的统一接口。"
                "LCEL 使用 Runnable 将这些组件串成可调用数据流。"
            ),
            metadata={"source": "langchain-overview", "topic": "components"},
        ),
        Document(
            page_content=(
                "LangGraph 负责带 state、节点和边的长流程编排。"
                "当需要 supervisor、子图、持久化或人工中断时，StateGraph 提供更明确的控制。"
            ),
            metadata={"source": "langgraph-overview", "topic": "orchestration"},
        ),
        Document(
            page_content=(
                "RAG 先把文档切成 chunks，再用 embedding 转为向量并存入 vector store。"
                "retriever 接收自然语言查询，返回最相关的 Document 列表供模型回答。"
            ),
            metadata={"source": "rag-overview", "topic": "retrieval"},
        ),
    ]
    chunks = RecursiveCharacterTextSplitter(
        chunk_size=100,
        chunk_overlap=20,
    ).split_documents(documents)
    embeddings = init_embeddings("openai:text-embedding-3-small")
    store = InMemoryVectorStore.from_documents(chunks, embeddings)
    return store.as_retriever(search_kwargs={"k": 2})
