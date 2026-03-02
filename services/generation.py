from langchain_core.messages import SystemMessage, HumanMessage
from core.llm import get_llm
from memory.session_memory import get_history, add_message


SYSTEM_PROMPT = """
You are an expert YouTube video assistant. Answer questions based EXCLUSIVELY on the provided transcript context.

**Response Formatting Rules (follow strictly):**
1. Start with a short 1-2 sentence direct answer or summary.
2. Use bullet points (`-`) for lists, steps, features, or multiple points — never write dense walls of text.
3. Use **bold** to highlight key terms, names, tools, or important concepts.
4. Group related timestamps together at the end of each bullet or paragraph like this: `[MM:SS-MM:SS]`.
5. For complex questions, use a short heading (e.g., `## Key Points`) to section your response.
6. Keep each bullet concise — 1–2 sentences max.
7. If the topic is NOT in the transcript, say so clearly — do NOT hallucinate.
"""


def format_context(docs):
    formatted = []
    for d in docs:
        try:
            start = int(float(d.metadata.get("start", 0)))
            duration = int(float(d.metadata.get("duration", 0)))
            end = start + duration
        except (ValueError, TypeError):
            continue

        start_m, start_s = divmod(start, 60)
        end_m, end_s = divmod(end, 60)

        timestamp = f"{start_m:02d}:{start_s:02d}-{end_m:02d}:{end_s:02d}"
        formatted.append(f"[{timestamp}] {d.page_content}")

    return "\n".join(formatted)


def format_metadata(docs):
    if not docs:
        return ""
    d = docs[0]
    title = d.metadata.get("title", "")
    channel = d.metadata.get("channel", "")
    views = d.metadata.get("views", "")
    published_at = d.metadata.get("published_at", "")
    description = d.metadata.get("description", "")
    
    meta_lines = []
    if title: meta_lines.append(f"Video Title: {title}")
    if channel: meta_lines.append(f"Channel: {channel}")
    if views: meta_lines.append(f"Views: {views}")
    if published_at: meta_lines.append(f"Published At: {published_at}")
    if description: meta_lines.append(f"Description:\n{description}")
    
    if meta_lines:
        return "\n".join(meta_lines) + "\n\n"
    return ""


def generate_answer(session_id, question, docs):

    llm = get_llm()

    def get_start_time(d):
        try:
            return float(d.metadata.get("start", 0))
        except (ValueError, TypeError):
            return 0.0

    # Sort documents chronologically by their start time
    sorted_docs = sorted(docs, key=get_start_time)
    video_metadata_str = format_metadata(sorted_docs)
    context = format_context(sorted_docs)
    chat_history = get_history(session_id)

    # Format chat history as a plain text block rather than appending raw
    # HumanMessage/AIMessage objects — langchain-google-genai 4.x serializes
    # those as Gemini `Content` objects which triggers Pydantic warnings.
    history_block = ""
    if chat_history:
        lines = []
        for msg in chat_history:
            prefix = "User" if msg["role"] == "user" else "Assistant"
            lines.append(f"{prefix}: {msg['content']}")
        history_block = "\n\nConversation History:\n" + "\n".join(lines)

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        SystemMessage(
            content=(
                f"Video Metadata:\n{video_metadata_str}"
                f"Transcript Context:\n{context}"
                f"{history_block}"
            )
        ),
        HumanMessage(content=question),
    ]

    response = llm.invoke(messages)

    add_message(session_id, "user", question)
    add_message(session_id, "assistant", response.content)

    return response.content