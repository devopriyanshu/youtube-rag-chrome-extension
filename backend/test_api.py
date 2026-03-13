import youtube_transcript_api
print("DIR of module:")
print(dir(youtube_transcript_api))

print("\nDIR of class:")
if hasattr(youtube_transcript_api, "YouTubeTranscriptApi"):
    print(dir(youtube_transcript_api.YouTubeTranscriptApi))

print("\nHELP of class:")
help(youtube_transcript_api.YouTubeTranscriptApi)
