from pathlib import Path
import json
import time
from time import perf_counter
from typing import Literal, List, Optional
import logging
import argparse

from prompts import user_instructions
from utils import calculate_token_cost, log_to_jsonl

from pydantic import BaseModel
from openai import OpenAI

logger = logging.getLogger(__name__)

openai_client = OpenAI()

class TextBlock(BaseModel):
    type: Literal["text"] = "text"
    content: str

class BulletListBlock(BaseModel):
    type: Literal["bullet_list"] = "bullet_list"
    items: List[str]

class CodeBlock(BaseModel):
    type: Literal["code"] = "code"
    language: str = "python"
    code: str

class MermaidBlock(BaseModel):
    type: Literal["mermaid"] = "mermaid"
    title: str
    diagram: str

ContentBlock = TextBlock | BulletListBlock | CodeBlock | MermaidBlock

class TimestampReference(BaseModel):
    start_time: str
    end_time: str
    concept: str
    learning_value: str
    screenshot_recommended: bool
    visual_to_capture: str
    screenshot_reason: str
    suggested_notes_location: str
    suggested_caption: str

class ConceptSection(BaseModel):
    title: str
    blocks: List[ContentBlock]

class KeyConcept(BaseModel):
    title:str
    description: Optional[str] = None
    bullet_points: List[str]

class CourseNotes(BaseModel):
    title: str
    overview: str
    key_concepts: List[KeyConcept]
    detailed_explanations: List[ConceptSection]
    key_takeaway: List[str]
    project_ideas: List[str]
    timestamps: List[TimestampReference]

def llm_structured(
        user_prompt:str,
        output_type:str,
        instructions=None,
        model:str="gpt-5.4",
    ):

    """Send a prompt to the OpenAI Responses API and parse structured output.

    Args:
        user_prompt: User message content sent to the model.
        output_type: Pydantic model or structured output type used for parsing.
        instructions: Optional system instructions to prepend to the request.
        model: Model name to use for generation.

    Returns:
        The full parsed OpenAI response object. Access parsed structured output
        with `response.output_parsed`.
    """
    messages = []

    if instructions:
        messages.append({
            "role": "system",
            "content": instructions
        })

    messages.append({
        "role": "user",
        "content": user_prompt
    })

    response = openai_client.responses.parse(
        model=model,
        input=messages,
        text_format=output_type
    )

    return response

def llm_structured_with_retries(
    transcript: str,
    model: str,
    max_attempts: int = 3,
    delay_in_secs: float = 2.0,
):
    for attempt in range(1, max_attempts + 1):
        try:
            llm_response = llm_structured(
                user_prompt=transcript,
                output_type=CourseNotes,
                instructions=user_instructions,
                model=model,
            )
            return llm_response, attempt
        except Exception as e:
            if attempt == max_attempts:
                raise

            delay = delay_in_secs * (2 ** (attempt - 1))
            logger.warning(
                "LLM call failed; retrying attempt %s/%s after %.1fs",
                attempt + 1,
                max_attempts,
                delay,
                exc_info=True,
            )
            time.sleep(delay)




def read_json_w_ts(filepath:str) -> tuple[str,str]:
    """Read a JSON file and return transcript with timestamps.
    The JSON file is expected to contain the keys `id` and `transcript_w_ts`.
    Each transcript item in `transcript_w_ts` should contain `start` and
    `content` fields. The returned transcript is formatted as one line per
    transcript segment.

    Args:
        filepath: Path to the transcript JSON file.

    Returns:
        A tuple containing the video ID and timestamped transcript.
    """
    path = Path(filepath)
    with open(path, "r", encoding="utf-8") as f:
        doc = json.load(f)
        video_id = doc["id"]
        dict_w_ts = doc["transcript_w_ts"]
        doc_w_ts = "\n".join(f"{i['start']} {i['content']}" for i in dict_w_ts)
    return video_id, doc_w_ts


def extract_course_notes(
        transcript_path: str, 
        output_path: str,
        json_logfile_path:str="generate_course_notes.jsonl", 
        model:str="gpt-5.4") -> None:
    
    """
    Generate structured course notes for transcript JSON files.

    Reads transcript JSON files from `transcript_path`, sends each timestamped
    transcript to the LLM, parses the response into the `CourseNotes` structured
    output schema, and writes one JSON output file per video.

    The function writes one JSONL record per transcript, logs success and failure
    events, and continues processing remaining files when one transcript fails.

    Args:
        transcript_path: Directory containing transcript JSON files.
        output_path: Directory where generated course note JSON files are saved.
        json_logfile_path: Path to the JSONL log file used to record success and
            failure events.
        model: OpenAI model name to use for course note generation.

    Returns:
        None.

    Raises:
        No exceptions are intentionally propagated for individual transcript
        failures. Per-file errors are written to the JSONL log.
    """
    # list all paths
    transcript_path = Path(transcript_path)
    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    
    transcript_path_list = sorted(transcript_path.glob("*.json"))

    

    # read transcripts
    for t in transcript_path_list:
        attempts = 0
        video_id = None
        total_cost = None
        input_cost = None
        output_cost = None
        # start time
        start = perf_counter()
        try: 
            video_id, transcript = read_json_w_ts(t)
            
            if not transcript.strip():
                raise ValueError("Transcript is empty.")

            # pass all info to llm
            llm_response, attempts = llm_structured_with_retries(
                transcript=transcript,
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
                response_json, 
                encoding="utf-8"
            )

            record = {
                "status": "succeeded",
                "video_id": video_id,
                "llm_attempts": attempts,
                "llm_retried": attempts > 1,
                "duration_secs": round(end-start,2),
                "input_file": str(t),
                "output_file": str(outpath),
                "model": model,
                "total cost": total_cost,
                "input_cost": input_cost,
                "output_cost": output_cost   
                                  }


            logger.info(
            "SUCCESS video_id=%s | "
            "Est_total_cost:%s, input_cost: %s, output_cost: %s",
            video_id,
            total_cost,
            input_cost,
            output_cost,
        )
            
            log_to_jsonl(json_logfile_path, record)
        except Exception as e:
            end = perf_counter()
            record = {
                "status": "failed",
                "video_id": video_id,
                "duration_secs": round(end-start,2),
                "input_file": str(t),
                "error_type": type(e).__name__,
                "error_message": str(e),
                "model": model,
                "total cost": total_cost,
                "input_cost": input_cost,
                "output_cost": output_cost 
            }

            logger.exception(
            "FAILED video_id=%s | "
            "%s: %s | Est_total_cost:%s, input_cost: %s, output_cost: %s",
            video_id,
            type(e).__name__,
            e,
            total_cost,
            input_cost,
            output_cost,
        )
            log_to_jsonl(json_logfile_path, record)

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Generate structured course notes from transcript JSON files."
    )

    parser.add_argument(
        "--transcript-path",
        required=True,
        help="Directory containing transcript JSON files.",
    )

    parser.add_argument(
        "--output-path",
        required=True,
        help="Directory where generated course note JSON files will be saved.",
    )

    parser.add_argument(
        "--logfile-path",
        default="generate_course_notes.jsonl",
        help="Path to the JSONL log file.",
    )

    parser.add_argument(
        "--model",
        default="gpt-5.4",
        help="OpenAI model to use.",
    )

    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level.",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    extract_course_notes(
        transcript_path=args.transcript_path,
        output_path=args.output_path,
        json_logfile_path=args.logfile_path,
        model=args.model,
    )