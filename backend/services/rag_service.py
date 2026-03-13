from services.retrieval import retrieve_context
from services.generation import generate_answer


def answer_question(session_id, video_id, question):
    docs = retrieve_context(video_id, question)
    return generate_answer(session_id, question, docs)