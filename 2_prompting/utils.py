import tiktoken
import json
from pathlib import Path
from os import PathLike


def count_tokens(document: str, model_name: str="gpt-5") -> int:

    """Estimates token count based on GPT-5 tokenizer"""

    encoding = tiktoken.encoding_for_model(model_name=model_name)
    token_count = len(encoding.encode(document))
    return token_count

def read_json(filepath:str| PathLike) -> str:

    """Reads a file path and returns video id and associating transcript """

    path = Path(filepath)
    
    with open(path, mode="r", encoding="utf-8") as f:
        doc_dict = json.load(f)
        video_id = doc_dict["id"]
        complete_transcript = doc_dict["complete_transcript"]
        
    return video_id, complete_transcript





# create function to interact with llm
from openai import OpenAI
import os

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

openai_client = OpenAI(api_key=OPENAI_API_KEY)

def llm(user_prompt, instructions=None, model="gpt-5.4-mini"):
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

    return response.output_text