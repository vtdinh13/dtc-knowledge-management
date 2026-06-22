import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


LOG_PATH = Path("tool_calls.jsonl")


def log_tool_call(
    tool_name: str,
    success: bool,
    notes_path: str | None = None,
    error: str | None = None,
) -> None:
    
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tool_name": tool_name,
        "success": success,
        "json_path": notes_path,
        "error": error,
    }

    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

def load_course_notes(notes_path: str) -> dict[str, Any]:

    try:
        path = Path(notes_path)

        if not path.exists():
            raise FileNotFoundError(f"File does not exist: {notes_path}")
        
        notes = json.loads(notes_path.read_text(encoding="utf-8"))

        log_tool_call(
            tool_name="load_course_notes",
            success=True,
            notes_path=str(path),
        )
        return notes
    
    except Exception as e:
        log_tool_call(
            tool_name="load_course_notes",
            success=False,
            notes_path=str(path),
            error=str(e)
        )
        raise


def list_candidate_images_by_video(candidate_images_folder:str):

    candidate_images_per_video = {}
    video_list = sorted([i for i in Path(candidate_images_folder).iterdir() if i.name !=".DS_Store"])

    for video in video_list:
        video_id = video.name
        candidate_images = sorted(
            image_path for image_path in video.iterdir() if image_path.is_file() and image_path.name !=".DS_Store"
            )
        candidate_images_per_video[video_id] = candidate_images
    return candidate_images_per_video

    
    