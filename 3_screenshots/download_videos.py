from pathlib import Path
import re
import json
from yt_dlp import YoutubeDL
import time
import logging


youtube_link = "https://www.youtube.com/watch?v="

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

logger = logging.getLogger(__name__)

def write_jsonl_log(log_path_input, event):
    log_path = Path(log_path_input)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")

def download_video_iterate(llm_output_dir:str, video_outpath: str, log_path:str|None=None):
    v_path_list = [i for i in llm_output_dir.iterdir() if i.suffix == ".json"]

    logger.info("Found %s JSON files in %s", len(v_path_list), llm_output_dir)

    for i in v_path_list:
        filename = i.name
        
        match = re.match(r"^llm_response_(.+)\.json$", filename)
        video_id = match.group(1)
        
        downloaded_video_path = f"{video_outpath}/{video_id}.mp4"

        if log_path is None:
            log_path_object = Path.cwd()
        else:
            log_path_object = Path(log_path)
        
        complete_log_path = f"{log_path_object}/download_videos_log.jsonl"

        logger.info("Downloading video %s to %s", video_id, downloaded_video_path)

        start = time.perf_counter()
        try: 
            with YoutubeDL({
                "outtmpl": downloaded_video_path,
                "format": "mp4", 
                "verbose": False,
                "quiet": True, 
                "no_warnings": True,
                "ignoreerrors": True        
                        }) as ydl:
                complete_link = f"{youtube_link}{video_id}"
                ydl.download([complete_link])
        except Exception as e:
            duration = time.perf_counter() - start
            logger.exception("Failed to download video %s", video_id)

            write_jsonl_log(complete_log_path, {
                "event": "fail",
                "video_id": video_id,
                "duration_secs": round(duration,2),
                "error": str(e)
            })
            continue
        duration = time.perf_counter() - start
        logger.info("Downloaded %s in %.2f seconds", video_id, duration)
        write_jsonl_log(complete_log_path, {
            "event": "success",
            "video_id": video_id, 
            "duration_secs": round(duration,2)
        })

    



