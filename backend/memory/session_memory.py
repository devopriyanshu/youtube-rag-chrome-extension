from cachetools import TTLCache

# max 10k sessions, expire after 1 hour
_sessions = TTLCache(maxsize=10000, ttl=3600)

MAX_HISTORY = 6


def get_history(session_id):
    return _sessions.get(session_id, [])


def add_message(session_id, role, content):
    history = _sessions.get(session_id, [])
    history.append({"role": role, "content": content})

    # limit memory
    history = history[-MAX_HISTORY:]

    _sessions[session_id] = history