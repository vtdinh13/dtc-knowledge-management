import json
import re
from pathlib import Path
from pydantic import BaseModel
from typing import Literal, List, Optional


def quote_nested_square_labels(line: str) -> str:
    """Quote Mermaid square-bracket labels that contain nested brackets.

    Args:
        line: One Mermaid source line.

    Returns:
        The line with labels like `B[loc[label]]` rewritten as
        `B["loc[label]"]`.
    """
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
    """Apply deterministic label-only fixes to Mermaid source.

    Args:
        diagram: Mermaid source text.

    Returns:
        Mermaid source with labels quoted when they contain syntax-sensitive
        punctuation. This does not repair structural graph errors.
    """
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
        """Return whether a Mermaid node label should be quoted."""
        label = label.strip()

        if label.startswith('"') and label.endswith('"'):
            return False

        return any(char in label for char in ["(", ")", ",", "+", "/", ":", "?", "[", "]"])

    def quote_square_label(match: re.Match) -> str:
        """Quote a square node label when needed."""
        node_id = match.group(1)
        label = match.group(2)

        if not needs_quotes(label):
            return match.group(0)

        return f'{node_id}["{label}"]'

    def quote_brace_label(match: re.Match) -> str:
        """Quote a brace/diamond node label when needed."""
        node_id = match.group(1)
        label = match.group(2)

        if not needs_quotes(label):
            return match.group(0)

        return f'{node_id}{{"{label}"}}'

    diagram = re.sub(
        r'\b([A-Za-z_][A-Za-z0-9_]*)\[([^\]"\n]+)\]',
        quote_square_label,
        diagram,
    )

    diagram = re.sub(
        r'\b([A-Za-z_][A-Za-z0-9_]*)\{([^}"\n]+)\}',
        quote_brace_label,
        diagram,
    )

    return diagram



def print_msg_to_llm(instructions: str, transcript_string: str):

    """Build and return the message payload that would be sent to the LLM.

    This helper is useful for debugging prompt construction before making an
    API call.

    Args:
        instructions: System instructions to include in the message list.
        transcript_string: User message content.

    Returns:
        A list of message dictionaries formatted for the OpenAI Responses API.
    """

    messages = []

    if instructions:
        messages.append({
            "role": "system",
            "content": instructions
        })

    messages.append({
        "role": "user",
        "content": transcript_string
    })

    return messages

def log_to_jsonl(path_input: str, record:dict):
    path = Path(path_input)
    path.parent.mkdir(exist_ok=True, parents=True)

    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

MODEL_PRICING_PER_1M = {
    "gpt-5.4-mini": {
        "input": 0.75,
        "output": 4.50,
    },
    "gpt-5.4": {
        "input": 2.5,
        "output": 15,
    },
    "gpt-5.5": {
        "input": 5,
        "output": 30,
    }
}

def calculate_token_cost(usage, model:str) -> tuple[float,float,float]:
    """Calculate estimated API cost from token usage for a configured model.

    Args:
        usage: OpenAI response usage object with `input_tokens` and
            `output_tokens` attributes.
        model: Model name used to look up pricing in `MODEL_PRICING_PER_1M`.

    Returns:
        A tuple of `(total_cost, input_cost, output_cost)`.

    Raises:
        ValueError: If the model does not have pricing configured.
    """
    if model not in MODEL_PRICING_PER_1M:
        raise ValueError(f"No pricing configured for model: {model}")

    pricing = MODEL_PRICING_PER_1M[model]

    input_tokens = usage.input_tokens
    output_tokens = usage.output_tokens

    input_cost = (usage.input_tokens / 1000000) * pricing["input"]
    output_cost = (usage.output_tokens / 1000000) * pricing["output"]
    total_cost = input_cost + output_cost 
    return total_cost, input_cost, output_cost

def get_output_dir(title:str, base_dir:str) -> Path:
    
    title_lower = title.lower()
    
    if any(phrase in title_lower for phrase in ["launch", "pre-course"]):
        path = Path("{base_dir}/module00")
        path.parent.mkdir(exist_ok=True, parents=True)
        return path
    
    match = re.match(r"ml zoomcamp (\d+)\.", title_lower)
    if match:
        module_no = int(match.group(1))
        path = Path(f"{base_dir}/module{module_no:02d}")
        path.parent.mkdir(exist_ok=True, parents=True)
        return path

    else:
        path = Path("{base_dir}/module11")
        path.parent.mkdir(exist_ok=True, parents=True)
        return path


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