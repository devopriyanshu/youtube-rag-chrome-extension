from langchain_community.embeddings import JinaEmbeddings
import os

def get_embeddings():
    return JinaEmbeddings(
        jina_api_key=os.getenv("JINA_API_KEY"),
        model_name="jina-embeddings-v2-base-en"
    )