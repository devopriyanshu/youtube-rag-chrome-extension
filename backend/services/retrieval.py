from vectorstore.qdrant_store import get_vector_store
from core.llm import get_llm
from dotenv import load_dotenv
from qdrant_client.http import models

load_dotenv()

def rewrite_query(query):
    llm = get_llm()
    prompt = f"""
    You are an expert search query rewriter. 
    Rewrite the following user request into a concise, semantic search query for a vector database.
    Focus on extracting keywords and core intent. DO NOT include any conversational filler (e.g. "Sure, here is the query").
    Only output the rewritten query text.
    
    User Request: {query}
    Rewritten Search Query:
    """
    return llm.invoke(prompt).content.strip()

def retrieve_context(video_id, query):
    improved_query = rewrite_query(query)
    vector_store = get_vector_store()
    
    retriever = vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={
            "k": 25,
            "filter": models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.video_id",
                        match=models.MatchValue(value=video_id)
                    )
                ]
            )
        }
    )
    return retriever.invoke(improved_query)