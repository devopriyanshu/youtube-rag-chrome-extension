from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http import models
from core.embeddings import get_embeddings
import os

COLLECTION_NAME = 'youtube_videos'

EMBEDDING_SIZE = 768  # Jina embeddings-v2-base-en output dimension

def get_vector_store():
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)

    if client.collection_exists(COLLECTION_NAME):
        # Guard against stale collection created with old HuggingFace 384-dim embeddings
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

    return QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=get_embeddings()
    )

def check_video_exists(video_id: str) -> bool:
    qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
    qdrant_api_key = os.getenv("QDRANT_API_KEY")
    client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)
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