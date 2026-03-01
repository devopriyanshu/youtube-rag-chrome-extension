from langchain_text_splitters import RecursiveCharacterTextSplitter
from vectorstore.qdrant_store import get_vector_store


def index_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size = 1500,
        chunk_overlap = 300
    )

    chunks = splitter.split_documents(documents)

    vector_store = get_vector_store()
    
    # HuggingFace embeddings run locally — no API rate limit, no sleep needed.
    # (Note: if you ever switch to a cloud embedding API like Gemini/OpenAI, re-add throttling here)
    batch_size = 50
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        vector_store.add_documents(batch)

    return len(chunks)

