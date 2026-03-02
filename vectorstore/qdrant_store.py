from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http import models
from core.embeddings import get_embeddings
import os

COLLECTION_NAME = 'youtube_videos'
EMBEDDING_SIZE = 768  # Jina embeddings-v2-base-en output dimension

# Cache: skip the collection check after it's been verified once per process
_collection_ready = False

def _ensure_collection(client):
    """Run once per process to verify/create the Qdrant collection."""
    global _collection_ready
    if _collection_ready:
        return

    if client.collection_exists(COLLECTION_NAME):
        # Guard against stale collection from old HuggingFace 384-dim embeddings
        collection_info = client.get_collection(COLLECTION_NAME)
        existing_size = collection_info.config.params.vectors.size
        if existing_size != EMBEDDING_SIZE:
            print(f"[vectorstore] Dimension mismatch! Collection has size={existing_size}, "
                  f"but current embeddings produce size={EMBEDDING_SIZE}. Recreating collection...")
            client.delete_collection(COLLECTION_NAME)

    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(size=EMBEDDING_SIZE, distance=models.Distance.COSINE),
        )
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name="metadata.video_id",
            field_schema=models.PayloadSchemaType.KEYWORD,
        )

    _collection_ready = True


def _make_client():
    """Create a QdrantClient with an explicit timeout to avoid hanging requests."""
    return QdrantClient(
        url=os.getenv("QDRANT_URL", "http://localhost:6333"),
        api_key=os.getenv("QDRANT_API_KEY"),
        timeout=10,  # seconds — fail fast if Qdrant Cloud is slow
    )


def get_vector_store():
    client = _make_client()

    try:
        _ensure_collection(client)
    except Exception as e:
        # Dimension check is a startup safety guard — if Qdrant is temporarily
        # slow, log and continue. The collection still works for search/upsert.
        print(f"[vectorstore] _ensure_collection skipped due to error: {e}")

    return QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=get_embeddings()
    )

def check_video_exists(video_id: str) -> bool:
    client = _make_client()
    try:
        res = client.scroll(
            collection_name=COLLECTION_NAME,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.video_id",
                        match=models.MatchValue(value=video_id)
                    )
                ]
            ),
            limit=1
        )
        return len(res[0]) > 0
    except Exception:
        return False