import re
import json
from pathlib import Path

from youtube_transcript_api._transcripts import FetchedTranscript


def log_to_jsonl(path_input: str, record:dict):
    path = Path(path_input)
    path.parent.mkdir(exist_ok=True, parents=True)

    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
