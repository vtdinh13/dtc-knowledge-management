import json
import re
import time
import random
from pathlib import Path
from datetime import datetime, timezone
import logging

from utils import log_to_jsonl

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._transcripts import FetchedTranscript

logger = logging.getLogger(__name__)
ytt_api = YouTubeTranscriptApi()


def format_timestamp(seconds: float) -> str:
    """Convert seconds to H:MM:SS if > 1 hour, else M:SS"""
    total_seconds = int(seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours > 0:
        return f"{hours}:{minutes:02}:{secs:02}"
    else:
        return f"{minutes}:{secs:02}"

def make_subtitles(transcript) -> str:
    lines = []

    for entry in transcript:
        ts = format_timestamp(entry.start)
        text = entry.text.replace('\n', ' ')
        lines.append(ts + ' ' + text)

    return '\n'.join(lines)


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

def fetch_transcript(
    video_id:str, 
    out_dir_input:str, 
    log_path_input:str = "transcript_downloads.jsonl"):
    
    # declare all paths
    out_dir_path = Path(out_dir_input) / f"{video_id}.json"
    log_path = Path(log_path_input)

    try:
        transcript_obj = ytt_api.fetch(video_id)
        transcript_ts = extract_ts_content(transcript_obj)
        

        out_dir_path.write_text(
            json.dumps(transcript_ts, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        log_to_jsonl(
            log_path,
            {
                "status": "success",
                "video_id": video_id,
                "output_path": str(out_dir_path),
                "error": None,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        return True

    except Exception as e:
        log_to_jsonl(
            log_path,
            {
                "status": "failed",
                "video_id": video_id,
                "output_path": str(out_dir_path),
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()

            }
        )

        return False


def get_output_dir(title:str):
    if any(phrase in title for phrase in ["launch", "pre-course"]):
        path = Path("transcripts/module00")
        path.parent.mkdir(exist_ok=True, parents=True)
        return path
    
    match = re.match(r"ml zoomcamp (\d+)\.", title)
    if match:
        module_no = int(match.group(1))
        path = Path(f"transcripts/module{module_no:02d}")
        path.parent.mkdir(exist_ok=True, parents=True)
        return path

    else:
        path = Path("transcripts/module11")
        path.parent.mkdir(exist_ok=True, parents=True)
        return path
    
    
    
def fetch_transcript_w_retries(
    video_id:str, 
    out_dir_input:str, 
    log_path_input:str = "transcript_downloads.jsonl",
    max_retries: int=3,
    delay:int=5
    ):
    
    # declare all paths
    out_dir_path = Path(out_dir_input) / f"{video_id}.json"
    log_path = Path(log_path_input)

    logger.info("Starting transcript fetch: video_id=%s output=%s", video_id, out_dir_path)


    # skip duplicates
    if out_dir_path.exists():
        logger.info("Skipping existing transcript: video_id=%s output=%s", video_id, out_dir_path)

        log_to_jsonl(log_path, {
            "status": "skipped_exists",
            "video_id": video_id,
            "output_path": str(out_dir_path),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return True

    out_dir_path.parent.mkdir(exist_ok=True, parents=True)

    for attempt in range(1, max_retries+1):
        try:
            logger.info(
                "Fetching transcript: video_id=%s attempt=%s/%s",
                video_id,
                attempt,
                max_retries,
            )
            transcript_obj = ytt_api.fetch(video_id)
            transcript_ts = extract_ts_content(transcript_obj)
            

            out_dir_path.write_text(
                json.dumps(transcript_ts, indent=2, ensure_ascii=False), encoding="utf-8"
            )

            logger.info("Downloaded transcript: video_id=%s output=%s", video_id, out_dir_path)

            log_to_jsonl(
                log_path,
                {
                    "status": "success",
                    "video_id": video_id,
                    "output_path": str(out_dir_path),
                    "error": None,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            )
            return True

        except Exception as e:
            e_text = str(e)
            is_rate_limited = "429" in e_text or "Too Many Requests" in e_text

            logger.warning(
                "Transcript fetch failed: video_id=%s attempt=%s/%s rate_limited=%s error=%s",
                video_id,
                attempt,
                max_retries,
                is_rate_limited,
                e_text,
            )

            log_to_jsonl(
                log_path,
                {
                    "status": "failed_attempt",
                    "video_id": video_id,
                    "output_path": str(out_dir_path),
                    "attempt": attempt,
                    "error": str(e),
                    "rate_limited": is_rate_limited,
                    "timestamp": datetime.now(timezone.utc).isoformat()

                }
            )

            if is_rate_limited:
                sleep_seconds = 60*attempt
            else:
                sleep_seconds = delay*(2**(attempt-1))
            
            sleep_seconds += random.uniform(0,30)

            logger.info(
                "Sleeping before retry: video_id=%s seconds=%.2f",
                video_id,
                sleep_seconds,
            )

            time.sleep(sleep_seconds)
    logger.error("Transcript fetch failed permanently: video_id=%s output=%s", video_id, out_dir_path)

    log_to_jsonl(
                log_path,
                {
                    "status": "failed_final",
                    "video_id": video_id,
                    "output_path": str(out_dir_path),
                    
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                )     

    return False