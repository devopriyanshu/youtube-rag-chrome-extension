import time
from langchain_text_splitters import RecursiveCharacterTextSplitter
from vectorstore.qdrant_store import get_vector_store


def index_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size = 1500,
        chunk_overlap = 300
    )

    chunks = splitter.split_documents(documents)

    vector_store = get_vector_store()
    
    # Jina AI is a cloud API with strict request size limits — keep batches small.
    # Retry with exponential backoff to handle transient connection drops.
    batch_size = 10
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        for attempt in range(3):
            try:
                vector_store.add_documents(batch)
                break
            except Exception as e:
                if attempt == 2:
                    raise
                wait = 2 ** attempt
                print(f"[indexing] Batch {i//batch_size} failed (attempt {attempt+1}): {e}. Retrying in {wait}s...")
                time.sleep(wait)

    return len(chunks)

