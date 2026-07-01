import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from utils import log_to_jsonl, fix_mermaid_syntax

class MermaidCourseNotesTools:
    """Class interface for processing course-note Mermaid diagrams."""

    def __init__(
        self,
        tracker_path: str = "file_processing_tracker.json",
        render_log_path: str = "rendered_mermaid/mermaid_render_log.jsonl",
        save_log_path: str = "rendered_mermaid/course_notes_v2_log.jsonl",
    ):
        """Configure paths used by the class-based tool interface.

        Args:
            tracker_path: Path to the processing tracker JSON file.
            render_log_path: JSONL log path for Mermaid render attempts.
            save_log_path: JSONL log path for v2 save events.
        """
        self.tracker_path = Path(tracker_path)
        self.render_log_path = render_log_path
        self.save_log_path = save_log_path

    def initialize_processing_log(
        self,
        notes_path_input: str,
    ) -> dict:
        """Create or load a processing tracker for JSON course-note files.

        Args:
            notes_path_input: Folder containing course-note JSON files.

        Returns:
            The existing tracker if present, otherwise a newly created tracker with
            one waiting record per JSON file.
        """
        tracker_filename = self.tracker_path

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
                    "created_at": now,
                }
            )

        record = {
            "version": 1,
            "created_at": now,
            "updated_at": now,
            "files": files,
        }

        tracker_filename.parent.mkdir(exist_ok=True, parents=True)
        tracker_filename.write_text(
            json.dumps(record, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return record

    def get_next_waiting_file(self) -> dict | None:
        """Mark and return the next waiting file from the processing tracker.

        Returns:
            The updated file record marked as processing, or None if no waiting
            files remain.
        """
        tracker_filename = self.tracker_path
        records = json.loads(tracker_filename.read_text(encoding="utf-8"))

        for record in records["files"]:
            if record["status"] == "waiting":
                return self.update_file_status(
                    filename=record["filename"],
                    status="processing",
                )

        return None

    def update_file_status(
        self,
        filename: str,
        status: str,
        error: str | None = None,
        summary: dict | None = None,
    ) -> dict:
        """Update one file record in the processing tracker.

        Args:
            filename: File name to update, matching the tracker's `filename` field.
            status: New status. Must be waiting, processing, completed, or failed.
            error: Error text for failed files.
            summary: Required summary for completed or failed files.

        Returns:
            The updated file record.

        Raises:
            ValueError: If the status is invalid, required summary is missing, or
                the file is not present in the tracker.
        """
        statuses = {"waiting", "completed", "processing", "failed"}
        if status not in statuses:
            raise ValueError(f"Invalid status: {status}. Must be one of {statuses}")

        if status in {"completed", "failed"} and summary is None:
            raise ValueError(f"summary is required when status is {status}")

        now = datetime.now(timezone.utc).isoformat()
        tracker_filename = self.tracker_path
        records = json.loads(tracker_filename.read_text(encoding="utf-8"))

        for record in records["files"]:
            if record["filename"] == filename:
                record["status"] = status
                record["summary"] = summary
                record["updated_at"] = now
                records["updated_at"] = now

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
                    json.dumps(records, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                return record

        raise ValueError(f"File not found in processing tracker: {filename}")

    def load_course_notes(self, file_path: str) -> dict:
        """Load course notes from a JSON file.

        Args:
            file_path: Path to the course-note JSON file.

        Returns:
            Parsed course-note data.
        """
        path = Path(file_path)
        return json.loads(path.read_text(encoding="utf-8"))

    def save_updated_course_notes_v2(
        self,
        course_notes: dict,
        source_path: str,
        output_path: str | None = None,
    ) -> dict:
        """Save updated course notes as a v2 JSON file.

        Args:
            course_notes: Updated course-note data to save.
            source_path: Original course-note file path.
            output_path: Optional explicit output path.

        Returns:
            Save event metadata including the v2 output path.
        """
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
            "ok": True,
            "source_path": str(source),
            "output_path": str(output),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        log_to_jsonl(self.save_log_path, record)
        return record


    def find_mermaid_diagrams(self, course_notes: dict) -> list[dict]:
        """Find Mermaid blocks in a course-notes JSON object.

        Args:
            course_notes: Course-notes data using
                `detailed_explanations[].blocks[]`.

        Returns:
            Records containing each Mermaid block's location, indexes, and diagram.
        """
        diagrams = []

        for section_index, section in enumerate(course_notes.get("detailed_explanations", [])):
            for block_index, block in enumerate(section.get("blocks", [])):
                if block.get("type") != "mermaid":
                    continue

                diagrams.append(
                    {
                        "location": f"detailed_explanations[{section_index}].blocks[{block_index}]",
                        "section_index": section_index,
                        "block_index": block_index,
                        "diagram": block.get("diagram", ""),
                    }
                )

        return diagrams


    def fix_many_mermaid_syntax(self, mermaid_diagrams: list[dict]) -> list[dict]:
        """Apply deterministic Mermaid syntax fixes to many diagram records.

        Args:
            mermaid_diagrams: Records returned by `find_mermaid_diagrams`.

        Returns:
            Diagram records with an added `diagram_correct_syntax` field.
        """
        mermaid_diagram_corrections = []

        for m in mermaid_diagrams:
            diagram = fix_mermaid_syntax(m.get("diagram", ""))
            mermaid_diagram_corrections.append(
                {
                    **m,
                    "diagram_correct_syntax": diagram,
                }
            )

        return mermaid_diagram_corrections


    def test_mermaid(
        self,
        diagram: str,
        location: str,
        output_dir: str = "rendered_mermaid",
        timeout: int = 30,
    ) -> dict:
        """Render-test one Mermaid diagram with Mermaid CLI.

        Args:
            diagram: Mermaid source text.
            location: Human-readable source location for audit logs.
            output_dir: Directory for generated Mermaid input and SVG files.
            timeout: Maximum seconds to allow the renderer to run.

        Returns:
            A structured render result. Renderer failures are returned rather than
            raised when possible.
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True, parents=True)

        diagram_hash = hashlib.sha1(diagram.encode("utf-8")).hexdigest()[:10]
        input_file = output_path / f"{diagram_hash}.mmd"
        output_file = output_path / f"{diagram_hash}.svg"
        input_file.write_text(diagram, encoding="utf-8")

        try:
            result = subprocess.run(
                ["npx", "mmdc", "-i", str(input_file), "-o", str(output_file)],
                capture_output=True,
                text=True,
                timeout=timeout,
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
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        log_to_jsonl(self.render_log_path, record)
        return record


    def insert_mermaid_diagram(
        self,
        course_notes: dict,
        section_index: int,
        block_index: int,
        diagram: str,
    ) -> dict:
        """Insert a Mermaid diagram into an existing course-notes object.

        Args:
            course_notes: Course-notes data to mutate.
            section_index: Index in `detailed_explanations`.
            block_index: Index in the section's `blocks`.
            diagram: Validated Mermaid source to insert.

        Returns:
            The same course-notes object after mutation.

        Raises:
            ValueError: If the target block is not a Mermaid block.
        """
        block = course_notes["detailed_explanations"][section_index]["blocks"][block_index]

        if block.get("type") != "mermaid":
            raise ValueError(
                "Target block is not mermaid: "
                f"detailed_explanations[{section_index}].blocks[{block_index}]"
            )

        block["diagram"] = diagram
        return course_notes
