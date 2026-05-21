import os
import re
from pathlib import Path
from typing import Union
import pymupdf
from dotenv import load_dotenv

from pydantic import BaseModel, Field

from mistralai.client import Mistral
from openai import OpenAI
from google import genai
from google.genai import types

from llm_calls import parse_llm

_NOISE_PATTERNS = [
    r"\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b",  # dates like 12/05/2024
    r"\b\+?\d[\d\s().-]{7,}\b",              # phone numbers
    r"\b\S+@\S+\.\S+\b",                     # email
    r"https?://\S+|www\.\S+",                # urls
    r"\blinkedin\.com/\S+\b",
    r"\bgithub\.com/\S+\b",
]

load_dotenv()
llm_provider = os.environ["LLM_PROVIDER"]
llm_model = os.environ["LLM_MODEL"]

match llm_provider:
    case "mistral":
        mistral_client = Mistral(api_key=os.environ["MISTRAL_KEY"])
    case "openrouter":
        openrouter_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ["OPENROUTER_KEY"],
        )
    case "gemini":
        gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    case _:
        raise ValueError(f"Unknown LLM_PROVIDER: {llm_provider!r}")

class ResumeChecker(BaseModel):
    is_it_resume: bool = Field(
        description="True if the text represents an IT resume suitable for behavioral interview, 0 otherwise"
    )

def check_resume(raw_text: str):
    system_prompt = f"""
        You are a concise resume classifier. 
        Given the following resume text, answer whether it is an IT resume, that suitable for a behavioral interview.
        Be optimistic enough, but restric irrelevant professions or not resume files.
        Return just a single number: 1 if it is an IT resume, 0 otherwise.
        """
    user_prompt = f"""
        RESUME TEXT: 
        {raw_text}
        """
    return parse_llm(user_prompt, ResumeChecker, system_prompt).is_it_resume


def parse_resume_pdf(pdf_path: Union[str, Path]) -> str:
    """
    Extract and clean text from a resume PDF.

    Keeps content such as skills and experience as full as possible while
    removing common contact/header noise.

    Parameters
    ----------
    pdf_path:
        Path to a PDF file or a file-like object containing PDF bytes.

    Returns
    -------
    str
        Cleaned resume text.
    """
    doc = pymupdf.open(pdf_path)
    if len(doc) > 10:
        raise Exception("Too long for a resume.")
    raw_text = '\n'.join([page.get_text() for page in doc])

    if not check_resume(raw_text):
        raise Exception("Not an IT resume.")

    # Normalize whitespace and line endings
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]

    cleaned_lines = []
    seen_header_block = False

    for line in lines:
        lower = line.lower()

        # Skip obvious contact/header noise
        if any(re.search(pattern, line, flags=re.IGNORECASE) for pattern in _NOISE_PATTERNS):
            continue

        # Remove lines that are mostly contact info or separators
        if re.fullmatch(r"[-_=•·| ]+", line):
            continue

        if len(cleaned_lines) < 5 and (
            re.search(r"\b(resume|curriculum vitae|cv)\b", lower)
            or re.search(r"\b(email|phone|mobile|linkedin|github|address)\b", lower)
        ):
            continue

        # Many resumes start with name/contact block; once we hit a substantive line, keep going
        if len(line.split()) <= 4 and not re.search(r"\b(skills|experience|education|projects|summary)\b", lower):
            # likely name or short header; skip only in the opening lines
            continue

        cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)
    # Remove repeated excessive blank lines if any
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text