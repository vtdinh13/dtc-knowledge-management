import tiktoken
import json
from pathlib import Path
from os import PathLike

from pydantic import BaseModel
from typing import Literal, List, Optional


# user instructions
user_instructions = """
# Role
You are a senior technical educator and curriculum designer specializing in Python and machine learning.

# Objective
Transform the provided transcript into high-quality educational course notes that are clear, technically accurate, well-structured, and optimized for learning and later review.

# Audience
The audience consists of beginner-to-intermediate learners with some technical background who want practical understanding, implementation knowledge, and conceptual clarity.

# Course Note Structure
Generate notes using the following structure:
<OUTPUT>
1. Title
2. Overview
3. Key Concepts
4. Detailed Explanations and Examples
5. Key Takeaway
6. Project Ideas
7. Time stamps
</OUTPUT>

# Core Responsibilities
You must:
- Extract the most important concepts, methods, examples, and implementation details from the transcript.
- Organize the material into coherent sections with clear headings and logical progression.
- Preserve all meaningful technical insights, engineering reasoning, tradeoffs, and practical details.
- Remove filler speech, repetition, false starts, and conversational noise.
- Rewrite spoken explanations into clear, concise, learner-friendly written explanations.
- Explain concepts accurately, including what they are, why they matter, how they work, and when to use them.
- Include Mermaid diagrams when a diagram would improve understanding of a concept, workflow, architecture, process, or relationship.
- Include relevant video timestamps when revisiting that moment would help the learner understand an important concept, example, code walkthrough, or visual explanation.
- For each timestamp, explain why that moment is useful for learning. Avoid summaries.
- Preserve important code-related discussion, implementation steps, and practical engineering considerations.
- Do not merely summarize. Produce complete course notes that can serve as study material and long-term reference.

# Formatting Requirements
- Use clear section headers
- Use bullet points where appropriate
- Use concise paragraphs
- Keep explanations dense with value but easy to scan

# Technical Explanation Guidelines
For each major concept:
- Define the concept clearly
- Explain why it matters, how it works, when to use it
- Explain tradeoffs or limitations when relevant
- Include mermaid diagrams where it will enhance understanding

Each screenshot recommendation should identify a specific visual moment that would improve the course notes.
For each recommended screenshot, describe:
- What visual element should be captured
- Why that visual element helps the learner
- Where the screenshot should be placed in the notes
- What caption should accompany it

Do not describe the entire video segment generally. Focus only on the visual artifact worth capturing.
Bad:
"This segment explains feature extraction and how emails are converted into features."
Good:
"Capture the slide/table showing email attributes converted into binary feature values. Place it under `Detailed Explanations and Examples > Feature extraction` because learners can visually connect each email attribute to the numeric model input."

Each timestamp reference must include:
- `start_time`: the beginning of the useful segment
- `concept`: the concept or moment being referenced
- `visual_to_capture`: the specific visual element to screenshot, such as a slide, code cell, diagram, chart, table, UI state, or worked example. Do not summarize the segment.
- `screenshot_reason`: explain why this visual artifact helps learning. Do not restate the transcript content.
- `suggested_caption`: a short caption describing the screenshot itself, not a summary of the lesson segment.

# Screenshot Guidance

Recommend screenshots only when the video likely contains a visual artifact that would improve the written notes.

A screenshot is useful when it captures:
- A diagram, chart, table, or slide
- A UI demonstration
- A workflow or architecture view
- A concrete worked example
- A before/after comparison

Bad `visual_to_capture`:
"The instructor explains how machine learning works."

Good `visual_to_capture`:
"The diagram showing data and labels flowing into a machine learning algorithm to produce a model."

Bad `screenshot_reason`:
"This is useful because it explains machine learning."

Good `screenshot_reason`:
"The diagram makes the difference between rule-based programming and model training visually explicit."

# Important Constraints
- DO NOT SUMMARIZE
- Do not include conversational filler
- Do not mention the existence of the transcript
- Use only timestamps that appear in the transcript as anchors. Do not invent unrelated timestamps.
- Do not repeat the same information
- Do not oversimplify technical concepts
- Do not hallucinate libraries, APIs, or implementation details
- Preserve technical accuracy over simplification

When code appears in the transcript or discussed conceptually:
- Preserve all meaningful code examples
- Code is a critical component of the course notes. Provide code where it will enhance understanding.
- Correct obvious syntax issues caused by transcription errors
- Reformat code using clean and professional Python styling
- Add short explanatory comments when useful
- Explain:
  - what the code does
  - why it matters
  - common pitfalls
  - practical use cases
- Separate conceptual explanations from implementation details
- Stay grounded in the transcript content
- Do NOT invent large systems or unsupported implementation details

# Quality Standard
The final output should resemble polished technical course material. DO NOT PROVIDE A SUMMARY.

The notes should:
- help learners study efficiently
- serve as long-term reference material
- provide implementation clarity
- preserve engineering intuition
- balance theory and practice

# Transcript
{transcript}
""".strip()




# structured output
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



def count_tokens(document: str, model_name: str="gpt-5") -> int:
    """Estimates the number of tokens in a document for a given model.
    Args:
        document: Text to tokenize.
        model_name: Model name used to select the tokenizer.

    Returns:
        Estimated token count for the input document.
    """

    encoding = tiktoken.encoding_for_model(model_name=model_name)
    token_count = len(encoding.encode(document))
    return token_count

def read_json(filepath:str| PathLike) -> tuple[str,str]:

    """Reads a JSON file and return video ID and transcript text.
    The JSON file is expected to contain the keys `id` and
    `complete_transcript`.

    Args:
        filepath: Path to the transcript JSON file.

    Returns:
        A tuple containing the video ID and complete transcript.
    """

    path = Path(filepath)
    
    with open(path, mode="r", encoding="utf-8") as f:
        doc_dict = json.load(f)
        video_id = doc_dict["id"]
        complete_transcript = doc_dict["complete_transcript"]
        
    return video_id, complete_transcript

def read_json_w_ts(filepath:str| PathLike) -> tuple[str,str]:
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


# create function to interact with llm
from openai import OpenAI
import os

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

openai_client = OpenAI(api_key=OPENAI_API_KEY)

def llm(user_prompt, instructions=None, model="gpt-5.4-mini"):
    """Send a plain text prompt to the OpenAI Responses API.

    Args:
        user_prompt: User message content sent to the model.
        instructions: Optional system instructions to prepend to the request.
        model: Model name to use for generation.

    Returns:
        The full OpenAI response object. Access llm response text with `response.output_text`.
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

    response = openai_client.responses.create(
        model=model,
        input=messages
    )

    return response

def llm_structured(
        user_prompt,
        output_type,
        instructions=None,
        model="gpt-5.4-mini",
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