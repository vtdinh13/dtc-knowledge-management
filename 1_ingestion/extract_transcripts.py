from youtube_transcript_api import YouTubeTranscriptApi
import json
import re
from youtube_transcript_api._transcripts import FetchedTranscript
from utils import make_subtitles



ytt_api = YouTubeTranscriptApi()


def extract_ts_content(transcript: FetchedTranscript) -> list:

    transcript_w_ts = []
    
    subtitles = make_subtitles(transcript)    
    lines = subtitles.split("\n")

    for i in lines:
        match = re.match(r"(\d+:\d+)\s+(.*)", i)


        if match:
            timestamp = match.group(1)
            content = match.group(2)

            transcript_w_ts.append({
                "start": timestamp, 
                "content": content
                })
    return transcript_w_ts




def extract_module1_metadata(dat:list) -> list:
    module1 = []

    for i in dat:
        title = i["title"].lower().strip()

        if title.startswith("ml zoomcamp 1."):
            module1.append({
                "id": i["id"], 
                "title": i["title"],
                "duration": i["duration"]
                })
    return module1



def extract_transcript(module1:list):
    for i in module1:
        transcript = ytt_api.fetch(i["id"])

        # extract full transcript
        complete_transcript = " ".join(t.text for t in transcript)

        # extract transcript with ts
        transcript_w_ts = extract_ts_content(transcript=transcript)
        
        # add data to existing list
        i["complete_transcript"] = complete_transcript
        i["transcript_w_ts"] = transcript_w_ts

        with open (f"./module1/transcript_{i["id"]}.json", "w") as f:
            json.dump(i,f)
        
        # need to create error handling and logging
        