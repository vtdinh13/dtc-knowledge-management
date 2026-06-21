import ffmpeg
import json
from pathlib import Path

def load_completed_video_ids(log_path):
    log_path = Path(log_path)

    if not log_path.exists():
        return set()

    completed = set()

    with log_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue

            event = json.loads(line)

            if event.get("event") == "screenshots_complete":
                completed.add(event["video_id"])

    return completed

def time_to_seconds(t: str) -> float:
    """
    Convert HH:MM:SS.mmm or MM:SS or seconds string to seconds.
    """
    parts = t.split(":")
    parts = [float(p) for p in parts]

    if len(parts) == 3:
        h, m, s = parts
        return h * 3600 + m * 60 + s
    elif len(parts) == 2:
        m, s = parts
        return m * 60 + s
    elif len(parts) == 1:
        return parts[0]
    else:
        raise ValueError(f"Invalid timestamp: {t}")


def seconds_to_timestamp(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def screenshots_in_range(
    video_path_input: str,
    video_id: str,
    start_time: str,
    end_time: str,
    interval_seconds: int,
    output_dir_input: str,
) -> list[str]:
    """
    Take screenshots every interval_seconds between start_time and end_time.
    """

    video_path = Path(video_path_input)

    output_dir = Path(output_dir_input)
    output_dir.mkdir(parents=True, exist_ok=True)

    start = time_to_seconds(start_time)
    end = time_to_seconds(end_time)

    if end <= start:
        raise ValueError("end_time must be after start_time")

    output_paths = []
    current = start

    while current <= end:
        timestamp = seconds_to_timestamp(current)
        safe_name = timestamp.replace(":", "-").replace(".", "_")
        output_path = output_dir / f"ss_{video_id}_{safe_name}.png"

        try:
            (
                ffmpeg
                .input(Path(video_path), ss=timestamp)
                .output(str(output_path), vframes=1)
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
        except ffmpeg.Error as e:
            print("FFmpeg stdout:")
            print(e.stdout.decode("utf-8", errors="replace") if e.stdout else "")

            print("FFmpeg stderr:")
            print(e.stderr.decode("utf-8", errors="replace") if e.stderr else "")

            raise
        output_paths.append(str(output_path))
        current += interval_seconds

    return output_paths



