import os
from youtube_transcript_api import YouTubeTranscriptApi
from langchain_core.documents import Document
from googleapiclient.discovery import build

def fetch_transcript(video_id: str):
    try:
        # Fetch video metadata using YouTube Data API
        api_key = os.environ.get("YOUTUBE_API_KEY")
        title, description, channel, published_at, tags, views = "", "", "", "", [], ""
        if api_key:
            try:
                youtube = build("youtube", "v3", developerKey=api_key)
                request = youtube.videos().list(
                    part="snippet,contentDetails,statistics",
                    id=video_id
                )
                response = request.execute()
                if "items" in response and len(response["items"]) > 0:
                    video_data = response["items"][0]
                    title = video_data["snippet"].get("title", "")
                    description = video_data["snippet"].get("description", "")
                    channel = video_data["snippet"].get("channelTitle", "")
                    published_at = video_data["snippet"].get("publishedAt", "")
                    tags = video_data["snippet"].get("tags", [])
                    views = video_data["statistics"].get("viewCount", "")
            except Exception as meta_e:
                print(f"Error fetching video metadata: {meta_e}")

        # youtube-transcript-api v1.x: instantiate the class first, then call .list()
        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.list(video_id)
        fetched_transcript = transcript_list.find_transcript(['en']).fetch()

        documents = []

        # fetched_transcript is a list of dicts like {'text': '...', 'start': 0.0, 'duration': ...}
        # In case the old code used fetched_transcript.snippets or similar:
        # Based on typical python youtube-transcript-api, it's a list.
        for snippet in fetched_transcript:
            # Handle both list of dicts and list of objects just in case
            text = snippet['text'] if isinstance(snippet, dict) else snippet.text
            start = snippet['start'] if isinstance(snippet, dict) else snippet.start
            duration = snippet['duration'] if isinstance(snippet, dict) else snippet.duration

            documents.append(
                Document(
                    page_content=text,
                    metadata={
                        "video_id": video_id,
                        "start": start,
                        "duration": duration,
                        "title": title,
                        "description": description,
                        "channel": channel,
                        "published_at": published_at,
                        "tags": tags,
                        "views": views
                    }
                )
            )

        return documents

    except Exception as e:
        print(f"Error fetching transcript: {e}")
        return []