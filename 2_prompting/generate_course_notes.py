# standard libraries
import os
from os import PathLike
from pathlib import Path
from typing import List, Optional, Literal
import json
from datetime import datetime, UTC
from time import perf_counter
import argparse


# third party libraries
from openai import OpenAI

# local project imports
from utils import read_json_w_ts, llm_structured, calculate_token_cost, CourseNotes, user_instructions



def write_jsonl_log(logfile_path: str | PathLike, record: dict) -> None:
    """Append one structured log record to a JSONL file.

    The parent directory is created if it does not already exist. Each call
    writes exactly one JSON object followed by a newline, making the file easy
    to append to and later load with tools such as pandas.

    Args:
        logfile_path: Path to the JSONL log file.
        record: Dictionary containing one event record to append.

    Returns:
        None.
    """

    logfile_path = Path(logfile_path)
    logfile_path.parent.mkdir(parents=True, exist_ok=True)

    with logfile_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def extract_course_notes(
        transcript_path: str | PathLike, 
        output_path: str | PathLike,
        json_logfile_path="generate_course_notes_log.jsonl", 
        model="gpt-5-mini") -> dict:
    """Generate structured course notes for transcript JSON files.

    Reads transcript files from `transcript_path`, sends each timestamped
    transcript to the LLM, parses the response into the `CourseNotes` structured
    output schema, and writes one JSON output file per video.

    The function logs one JSONL record per transcript, tracks successes and
    failures, prints running progress to the command line, and continues
    processing remaining files when one transcript fails.

    Args:
        transcript_path: Directory containing transcript JSON files.
        output_path: Directory where generated course note JSON files are saved.
        json_logfile_path: Path to the JSONL log file used to record success and
            failure events.
        model: OpenAI model name to use for course note generation.

    Returns:
        A dictionary with two keys:
        - `succeeded`: list of success records.
        - `failed`: list of failure records.

    Raises:
        No exceptions are intentionally propagated for individual transcript
        failures. Per-file errors are captured in the returned `failed` list and
        written to the JSONL log.
    """
    # list all paths
    transcript_path = Path(transcript_path)
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    
    transcript_path_list = [t for t in transcript_path.iterdir()]

    success_count = 0
    failure_count = 0
    total_files = len(transcript_path_list)

    # track successes and failures
    results = {
        "succeeded": [],
        "failed": []
    }

    # read transcripts
    for i in transcript_path_list:
        video_id = None
        total_cost = None
        input_cost = None
        output_cost = None
        # start time
        start = perf_counter()
        try: 
            video_id, transcript = read_json_w_ts(i)
            
            if not transcript.strip():
                raise ValueError("Transcript is empty.")

            # pass all info to llm
            llm_response = llm_structured(
                user_prompt=transcript,
                output_type=CourseNotes,
                instructions=user_instructions,
                model=model
            )
            
            # end time
            end = perf_counter()
            
            # cost
            total_cost, input_cost, output_cost = calculate_token_cost(usage=llm_response.usage, model=model)

            # convert response to json + write file to folder
            response_json = llm_response.output_parsed.model_dump_json(indent=2)

            outpath = output_path/f"llm_response_{video_id}.json"
            outpath.write_text(
                response_json, encoding="utf-8"
            )

            record = {
                "status": "succeeded",
                "video_id": video_id,
                "duration_secs": round(end-start,2),
                "input_file": str(i),
                "output_file": f"{str(output_path)}/{str(i.name)}",
                "model": model,
                "total cost": total_cost,
                "input_cost": input_cost,
                "output_cost": output_cost   
                                  }
 #
            success_count += 1
            processed_count = success_count + failure_count

            print(
            f"[{processed_count}/{total_files}] "
            f"successes={success_count} failures={failure_count} | "
            f"SUCCESS video_id={video_id} |"
            f"Est_total_cost:{total_cost}, input_cost: {input_cost}, output_cost: {output_cost}"
        )
            results["succeeded"].append(record)

            # write to log
            write_jsonl_log(json_logfile_path, record)
            
        except Exception as e:
            end = perf_counter()
            failure_count += 1
            processed_count = success_count + failure_count
            record = {
                "status": "failed",
                "video_id": video_id,
                "duration_secs": round(end-start,2),
                "input_file": str(i),
                "error_type": type(e).__name__,
                "error_message": str(e),
                "model": model,
                "total cost": total_cost,
                "input_cost": input_cost,
                "output_cost": output_cost 
            }

            print(
            f"[{processed_count}/{total_files}] "
            f"successes={success_count} failures={failure_count} | "
            f"FAILED video_id={video_id} | "
            f"{type(e).__name__}: {e}",
            f"Est_total_cost:{total_cost}, input_cost: {input_cost}, output_cost: {output_cost}"

        )
            results["failed"].append(record)
            write_jsonl_log(json_logfile_path, record)

    return results

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate structured course notes from transcript JSON files."
    )

    parser.add_argument(
        "--transcript-path",
        required=True,
        help="Folder containing transcript JSON files.",
    )

    parser.add_argument(
        "--output-path",
        required=True,
        help="Folder where generated course note JSON files will be saved.",
    )

    parser.add_argument(
        "--logfile-path",
        default="generate_course_notes_log.jsonl",
        help="Path to JSONL log file.",
    )

    parser.add_argument(
        "--model",
        default="gpt-5-mini",
        help="OpenAI model to use.",
    )

    args = parser.parse_args()

    results = extract_course_notes(
        transcript_path=args.transcript_path,
        output_path=args.output_path,
        json_logfile_path=args.logfile_path,
        model=args.model,
    )