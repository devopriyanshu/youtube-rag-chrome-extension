import functools
from langchain_community.embeddings import JinaEmbeddings
import os

JINA_REQUEST_TIMEOUT = 60  # seconds — Jina responds <10s normally; 60s = generous headroom

def get_embeddings():
    emb = JinaEmbeddings(
        jina_api_key=os.getenv("JINA_API_KEY"),
        model_name="jina-embeddings-v2-base-en"
    )
    # JinaEmbeddings uses requests.Session with no timeout — inject one.
    # This intercepts every session.post() call made by _embed().
    emb.session.request = functools.partial(
        emb.session.request, timeout=JINA_REQUEST_TIMEOUT
    )
    return emb