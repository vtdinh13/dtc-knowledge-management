import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import re

from download_videos import download_one_video, write_jsonl_log
from utils import screenshots_in_range

logger = logging.getLogger(__name__)

def timestamp_to_seconds(timestamp):
    dt = datetime.strptime(timestamp, "%M:%S")
    return dt.minute * 60 + dt.second

def start_time_from_end(end_time, seconds_before=12):
    end_dt = datetime.strptime(end_time, "%M:%S")
    start_dt = end_dt - timedelta(seconds=seconds_before)
    return start_dt.strftime("%M:%S")

def process_timestamps(llm_output_input:str):
    llm_output = Path(llm_output_input)

    timestamps_list = []

    try:
        llm_response_content = json.loads(llm_output.read_text())
    except json.JSONDecodeError:
        logger.exception("Failed to parse JSON in %s", llm_output)
        

    timestamps = llm_response_content.get("timestamps", [])
    if not timestamps:
        logger.warning("No timestamps found in %s", llm_output.name)
        

    for timestamp in timestamps:
        if timestamp.get("screenshot_recommended") is not True:
            continue

        endtime = timestamp["end_time"]
        starttime = start_time_from_end(timestamp["end_time"], seconds_before=12)

        timestamps_list.append((starttime, endtime))

    return timestamps_list

def take_screenshots(llm_output_dir:str, ss_output_dir:str):
    
    # 0. Specify paths
    llm_output_path = Path(llm_output_dir)
    
    # 1. grab LLM output
    v_path_list = sorted([p.name for p in llm_output_path.iterdir() if p.suffix == ".json"])

    logger.info("Found %s LLM output JSON files in %s", len(v_path_list), llm_output_dir)
    
    # 2. download one video from a list of llm output then iterate
    for llm_output in v_path_list:

        # 2.0 - grab video id
        match = re.match(r"^llm_response_(.+)\.json$", llm_output)
        video_id = match.group(1)

        # 2.1 - download one video
        try:
            video_path = download_one_video(llm_output)
        except Exception:
            logger.exception("Video download failed for %s", llm_output)
            continue

        # 2.2 - load timestamps from llm output
        llm_json_file_path = f"{llm_output_dir}/{llm_output}"
        timestamp_list = process_timestamps(llm_json_file_path)

        #2.3 - capture images

        all_screenshot_paths = []
        screenshots_successful = True

        for st, et in timestamp_list:
            try:
                screenshot_paths = screenshots_in_range(
                    video_path_input=video_path,
                    video_id=video_id,
                    start_time=st,
                    end_time=et,
                    interval_seconds=6,
                    output_dir_input=ss_output_dir,
                )
                all_screenshot_paths.extend(screenshot_paths)

            except Exception as e:
                screenshots_successful = False

                logger.exception(
                    "Failed to capture screenshots for %s from %s to %s",
                    llm_output.name,
                    st,
                    et,
                )

                write_jsonl_log("screenshotting_log.jsonl", {
                "event": "screenshot_failed",
                "video_id": video_id,
                "start_time": st,
                "end_time": et,
                "error": str(e),
            })

        # 2.4 - remove video if screenshots were successful
        video_path_obj = Path(video_path)

        if screenshots_successful and all_screenshot_paths:
            video_path_obj.unlink(missing_ok=True)

            logger.info("Deleted video %s after successful screenshots", video_path)

            write_jsonl_log("screenshotting_log.jsonl", {
                "event": "video_deleted",
                "video_id": video_id,
                "video_path": str(video_path_obj),
                "screenshot_count": len(all_screenshot_paths),
            })

        else:
            logger.warning("Keeping video %s because screenshots were not fully successful", video_path)

            write_jsonl_log("screenshotting_log.jsonl", {
                "event": "video_kept",
                "video_id": video_id,
                "video_path": str(video_path_obj),
                "screenshot_count": len(all_screenshot_paths),
                "screenshots_successful": screenshots_successful,
            })

                




