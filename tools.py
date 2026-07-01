import re
import subprocess
from pathlib import Path
import hashlib
from utils import log_to_jsonl
from datetime import datetime, timezone
import json
from copy import deepcopy




# class MermaidTools:
#     def __init__(
#         self,
#         output_dir: str = "rendered_mermaid",
#         render_log_path: str = "rendered_mermaid/mermaid_render_log.jsonl",
#         fix_log_path: str = "rendered_mermaid/mermaid_fix_log.jsonl",
#         save_log_path: str = "rendered_mermaid/course_notes_v2_log.jsonl",
#         timeout: int = 30,
#     ):
#         self.output_dir = output_dir
#         self.render_log_path = render_log_path
#         self.fix_log_path = fix_log_path
#         self.save_log_path = save_log_path
#         self.timeout = self.timeout



def initialize_processing_log(notes_path_input:str):
    tracker_filename = Path("file_processing_tracker.json")
    if tracker_filename.exists():
        return json.loads(tracker_filename.read_text(encoding="utf-8"))

    now = datetime.now(timezone.utc).isoformat()
    notes_path = Path(notes_path_input)

    files = []
    for notes in sorted(notes_path.glob("*.json")):
        if not notes.is_file():
            continue
        files.append(
            {
                "filename": notes.name,
                "filepath": str(notes),
                "status": "waiting", 
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        )
    
    record = {
        "version": 1,
        "created_at":now,
        "updated_at":now,
        "files": files

    }

    tracker_filename.parent.mkdir(exist_ok=True, parents=True)
    tracker_filename.write_text(
        json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return record
# 7. create update_file_status() to keep track of the progress of each file

def update_file_status(filename:str, status:str, error:str | None=None, summary: dict| None=None):
    
    STATUSES = {"waiting", "completed", "processing", "failed"}
    if status not in STATUSES:
        raise ValueError(f"Invalid status: {status}. Must be one of {STATUSES}")
    if status in {"completed", "failed"} and summary is None:
        raise ValueError(f"summary is required when status is {status}")
    
    now = datetime.now(timezone.utc).isoformat()

    tracker_filename = Path("file_processing_tracker.json")

    records = json.loads(tracker_filename.read_text(encoding="utf-8"))

    for record in records["files"]:
        if record["filename"] == filename:
            record["status"] = status
            records["updated_at"] = now
            record["summary"] = summary

            if status == "processing":
                record["started_at"] = now
                record["attempts"] = record.get("attempts", 0) + 1
                record["error"] = None
            elif status == "completed":
                record["completed_at"] = now
                record["error"] = None
            elif status == "failed":
                record["failed_at"] = now
                record["error"] = error or "Unknown error"
            
            

            tracker_filename.write_text(
                json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            return record
    raise ValueError(f"File not found in processing tracker: {filename}")

def get_next_waiting_file() -> dict | None:
    tracker_filename = Path("file_processing_tracker.json")
    records = json.loads(tracker_filename.read_text(encoding="utf-8"))

    for record in records["files"]:
        if record["status"] == "waiting":
            return update_file_status(record["filename"], "processing")

    return None






def quote_nested_square_labels(line: str) -> str:
            pattern = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\[")

            result = []
            last_index = 0

            for match in pattern.finditer(line):
                node_id = match.group(1)
                label_start = match.end()
                i = label_start
                depth = 1

                while i < len(line):
                    if line[i] == "[":
                        depth += 1
                    elif line[i] == "]":
                        depth -= 1

                        if depth == 0:
                            label = line[label_start:i]

                            if "[" in label or "]" in label:
                                result.append(line[last_index:match.start()])
                                result.append(f'{node_id}["{label}"]')
                                last_index = i + 1

                            break

                    i += 1

            result.append(line[last_index:])
            return "".join(result)

def fix_mermaid_syntax(diagram: str) -> str:
        """Apply deterministic label-only Mermaid syntax fixes.

        This helper quotes node labels that commonly break Mermaid rendering,
        especially labels with punctuation, math-like symbols, or literal newline
        markers. It does not validate the diagram or repair structural Mermaid
        syntax such as malformed arrows, invalid graph declarations, or bad
        subgraph blocks.
        """
        # Fix: Node[Label]\n(extra text)
        # Into: Node["Label<br/>(extra text)"]
        diagram = re.sub(
            r'(\b[A-Za-z_][A-Za-z0-9_]*)\[([^\]]+)\]\\n(\([^\n]+?\))',
            r'\1["\2<br/>\3"]',
            diagram,
        )
        diagram = "\n".join(
            quote_nested_square_labels(line)
            for line in diagram.splitlines()
        )
        
        def needs_quotes(label: str) -> bool:
            label = label.strip()

            if label.startswith('"') and label.endswith('"'):
                return False

            return any(char in label for char in ["(", ")", ",", "+", "/", ":", "?", "[", "]"])

        def quote_square_label(match: re.Match) -> str:
            node_id = match.group(1)
            label = match.group(2)

            if not needs_quotes(label):
                return match.group(0)

            return f'{node_id}["{label}"]'

        def quote_brace_label(match: re.Match) -> str:
            node_id = match.group(1)
            label = match.group(2)

            if not needs_quotes(label):
                return match.group(0)

            return f'{node_id}{{"{label}"}}'

        # Fix square node labels: A[Training dataset (X, y)]
        diagram = re.sub(
            r'\b([A-Za-z_][A-Za-z0-9_]*)\[([^\]"\n]+)\]',
            quote_square_label,
            diagram,
        )

        # Fix decision/diamond labels: H{If Test ok?}
        diagram = re.sub(
            r'\b([A-Za-z_][A-Za-z0-9_]*)\{([^}"\n]+)\}',
            quote_brace_label,
            diagram,
        )

        return diagram
def fix_many_mermaid_syntax(mermaid_diagrams:list) -> list:

    mermaid_diagram_corrections = []

    for m in mermaid_diagrams:
        diagram = fix_mermaid_syntax(m.get("diagram"))

        mermaid_diagram_corrections.append(
            {
                **m,
                "diagram_correct_syntax": diagram
            }
        )
    return mermaid_diagram_corrections

def find_mermaid_diagrams(course_notes: dict) -> list[dict]:
    """Find Mermaid blocks in a course-notes JSON object.

    Args:
        course_notes: Course-notes data using the expected schema
            `detailed_explanations[].blocks[]`.

    Returns:
        A list of dictionaries containing each Mermaid block's location,
        `section_index`, `block_index`, and raw `diagram` string.
    """
    diagrams = []

    for section_index, section in enumerate(course_notes.get("detailed_explanations", [])):
        for block_index, block in enumerate(section.get("blocks", [])):
            if block.get("type") != "mermaid":
                continue

            diagrams.append({
                "location": f"detailed_explanations[{section_index}].blocks[{block_index}]",
                "section_index": section_index,
                "block_index": block_index,
                "diagram": block.get("diagram", ""),
            })

    return diagrams


def test_mermaid(
    diagram: str,
    location: str,
    output_dir: str = "rendered_mermaid",
    log_path:str = "rendered_mermaid/mermaid_render_log.jsonl",
    timeout:int = 30
) -> dict:
    """Render-test one Mermaid diagram with Mermaid CLI.
 
    The diagram is written to a `.mmd` file under `output_dir`, rendered with
    `npx mmdc`, and the attempt is logged to JSONL. Renderer failures are
    returned as structured records instead of raising when possible.

    Args:
        diagram: Mermaid source text.
        location: Optional human-readable source location for audit logs.
        output_dir: Directory for generated `.mmd` and `.svg` files.
        log_path: JSONL log path for render attempts.
        timeout: Maximum seconds to allow the renderer to run.

    Returns:
        A structured result with `ok`, `status`, file paths, renderer error,
        return code, diagram hash, and timestamp.
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True, parents=True)

    diagram_hash = hashlib.sha1(diagram.encode("utf-8")).hexdigest()[:10]
    file_stem = f"{diagram_hash}"

    input_file = output_path / f"{file_stem}.mmd"
    output_file = output_path / f"{file_stem}.svg"

    input_file.write_text(diagram, encoding="utf-8")

    try:
        result = subprocess.run(
            ["npx", "mmdc", "-i", str(input_file), "-o", str(output_file)],
            capture_output=True,
            text=True,
            timeout=timeout
        )

        record = {
            "event": "mermaid_test",
            "ok": result.returncode == 0,
            "status": "rendered" if result.returncode == 0 else "failed",
            "diagram_hash": diagram_hash,
            "diagram": diagram,
            "location": location,
            "returncode": result.returncode,
            "error": None if result.returncode == 0 else result.stderr or result.stdout,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:

        record = {
            "event": "mermaid_test",
            "ok": False,
            "status": "tool_error",
            "diagram_hash": diagram_hash,
            "diagram": diagram,
            "location": location,
            "returncode": None,
            "error":str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    log_to_jsonl(log_path, record)

    # if not keep_files:
    #     Path(record["input_path"]).unlink(missing_ok=True)
    #     if record["output_path"]:
    #         Path(record["output_path"]).unlink(missing_ok=True)

    return record


# def test_and_fix_mermaid_diagram(
#     diagram: str,
#     location: str | None = None,
#     section_index: int| None=None,
#     block_index: int| None=None,
#     output_dir: str = "rendered_mermaid",
#     log_path: str = "rendered_mermaid/mermaid_fix_log.jsonl",
# ) -> dict:
#     """Test one Mermaid diagram and try one deterministic label fix if needed.

#     The first attempt renders the original diagram. If it fails, the function
#     applies `fix_mermaid_labels()` and renders the corrected candidate. The
#     final result is logged to JSONL and includes the source indexes needed by
#     `save_course_notes_v2()`.

#     Args:
#         diagram: Mermaid source text.
#         location: Optional human-readable source location for audit logs.
#         section_index: Index of the course-notes section containing the block.
#         block_index: Index of the Mermaid block inside the section.
#         output_dir: Directory for generated `.mmd` and `.svg` files.
#         log_path: JSONL log path for test/fix summaries.

#     Returns:
#         A structured result containing render status, whether the diagram
#         changed, source indexes, paths, errors, hashes, and the final diagram
#         candidate.
#     """
#     original_hash = hashlib.sha1(diagram.encode("utf-8")).hexdigest()[:10]

#     first_result = test_mermaid_diagram(
#         diagram=diagram,
#         location=location,
#         output_dir=output_dir,
#     )

#     if first_result["ok"]:
#         record = {
#             "event": "mermaid_test_and_fix",
#             "ok": True,
#             "status": "rendered",
#             "location": location,
#             "section_index": section_index,
#             "block_index": block_index,
#             "changed": False,
#             "original_hash": original_hash,
#             "final_hash": original_hash,
#             "input_path": first_result["input_path"],
#             "output_path": first_result["output_path"],
#             "error": None,
#             "timestamp": datetime.now(timezone.utc).isoformat(),
#         }

#         log_to_jsonl(log_path, record)

#         return {
#             **record,
#             "diagram": diagram,
#         }

#     first_error = first_result["error"]
#     corrected = fix_mermaid_labels(diagram)
#     corrected_hash = hashlib.sha1(corrected.encode("utf-8")).hexdigest()[:10]

#     if corrected == diagram:
#         record = {
#             "event": "mermaid_test_and_fix",
#             "ok": False,
#             "status": "failed",
#             "location": location,
#             "section_index": section_index,
#             "block_index": block_index,
#             "changed": False,
#             "original_hash": original_hash,
#             "final_hash": original_hash,
#             "input_path": first_result["input_path"],
#             "output_path": first_result["output_path"],
#             "error": first_error,
#             "timestamp": datetime.now(timezone.utc).isoformat(),
#         }

#         log_to_jsonl(log_path, record)

#         return {
#             **record,
#             "diagram": diagram,
#         }

#     retry_result = test_mermaid_diagram(
#         diagram=corrected,
#         location=location,
#         output_dir=output_dir,
#     )

#     if retry_result["ok"]:
#         record = {
#             "event": "mermaid_test_and_fix",
#             "ok": True,
#             "status": "fixed",
#             "location": location,
#             "section_index": section_index,
#             "block_index": block_index,
#             "changed": True,
#             "original_hash": original_hash,
#             "final_hash": corrected_hash,
#             "input_path": retry_result["input_path"],
#             "output_path": retry_result["output_path"],
#             "error": None,
#             "first_error": first_error,
#             "timestamp": datetime.now(timezone.utc).isoformat(),
#         }

#         log_to_jsonl(log_path, record)

#         return {
#             **record,
#             "diagram": corrected,
#         }

#     record = {
#         "event": "mermaid_test_and_fix",
#         "ok": False,
#         "status": "failed_after_fix",
#         "location": location,
#         "section_index": section_index,
#         "block_index": block_index,
#         "changed": True,
#         "original_hash": original_hash,
#         "final_hash": corrected_hash,
#         "input_path": retry_result["input_path"],
#         "output_path": retry_result["output_path"],
#         "error": retry_result["error"],
#         "first_error": first_error,
#         "timestamp": datetime.now(timezone.utc).isoformat(),
#     }

#     log_to_jsonl(log_path, record)

#     return {
#         **record,
#         "diagram": corrected,
#     }

def save_updated_course_notes_v2(
    course_notes: dict,
    source_path: str,
    output_path: str | None = None,
    log_path: str = "rendered_mermaid/course_notes_v2_log.jsonl",
) -> dict:
    source = Path(source_path)

    if output_path is None:
        output = source.with_name(f"{source.stem}_v2{source.suffix}")
    else:
        output = Path(output_path)

    output.parent.mkdir(exist_ok=True, parents=True)
    output.write_text(
        json.dumps(course_notes, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    record = {
        "event": "save_updated_course_notes_v2",
        "source_path": str(source),
        "output_path": str(output),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "ok": True,
    }

    log_to_jsonl(log_path, record)
    return record
