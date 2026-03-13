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

    # batch_size=20: ~30k chars per Jina request — well within limits, 4× fewer
    # API calls vs batch_size=5. A 10-min video (~60 chunks) = 3 calls, not 12.
    # No sleep between batches: Jina free tier allows 500 req/min — we never get close.
    batch_size = 20
    total_batches = (len(chunks) + batch_size - 1) // batch_size

    for i in range(0, len(chunks), batch_size):
        batch_num = i // batch_size + 1
        batch = chunks[i:i + batch_size]
        print(f"[indexing] Embedding batch {batch_num}/{total_batches} ({len(batch)} chunks)...")
        for attempt in range(3):
            try:
                vector_store.add_documents(batch)
                break
            except Exception as e:
                if attempt == 2:
                    raise
                wait = 2 ** attempt
                print(f"[indexing] Batch {batch_num} failed (attempt {attempt+1}): {e}. Retrying in {wait}s...")
                time.sleep(wait)

    return len(chunks)

