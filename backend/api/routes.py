from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.rag_service import answer_question
from services.ingestion import fetch_transcript
from services.indexing import index_documents
from vectorstore.qdrant_store import check_video_exists

router = APIRouter()

@router.get("/health")
def health_check():
    return {"status": "ok"}

class AskRequest(BaseModel):
    session_id: str
    video_id: str
    question: str

class IndexRequest(BaseModel):
    video_id: str

@router.post("/index")
def index_video(payload: IndexRequest):
    if check_video_exists(payload.video_id):
        return {"message": f"Video {payload.video_id} is already indexed."}

    docs = fetch_transcript(payload.video_id)
    if not docs:
        raise HTTPException(status_code=400, detail="Could not fetch transcript or no transcript available")
    
    num_chunks = index_documents(docs)
    return {"message": f"Successfully indexed {num_chunks} chunks for video {payload.video_id}"}

@router.post("/ask")
def ask(payload: AskRequest):
    return {
        "answer": answer_question(
            session_id=payload.session_id,
            video_id=payload.video_id,
            question=payload.question
        )
    }