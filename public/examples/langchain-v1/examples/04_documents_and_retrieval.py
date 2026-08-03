"""Chapter 4: build a local in-memory vector retriever with real embeddings."""

from dotenv import load_dotenv

from rag_data import build_retriever


load_dotenv()


def main():
    retriever = build_retriever()
    documents = retriever.invoke("LangGraph 适合处理什么类型的流程？")
    print(f"召回数: {len(documents)}")
    for document in documents:
        print(f"来源: {document.metadata['source']}")
        print("片段: " + document.page_content)


if __name__ == "__main__":
    main()
