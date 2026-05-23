import logging
import os
import time
from pathlib import Path
from typing import Union
import pymupdf

logger = logging.getLogger(__name__)
from dotenv import load_dotenv

from pydantic import BaseModel, Field

from mistralai.client import Mistral
from openai import OpenAI
from google import genai
from google.genai import types

from llm_calls import parse_llm

load_dotenv()
llm_preparser_provider = os.environ["LLM_PREPARSER_PROVIDER"]
llm_preparser_model = os.environ["LLM_PREPARSER_MODEL"]

llm_parser_provider = os.environ["LLM_PARSER_PROVIDER"]
llm_parser_model = os.environ["LLM_PARSER_MODEL"]

providers = [llm_preparser_provider, llm_parser_provider]
for provider in providers:
    match provider:
        case "mistral":
            mistral_client = Mistral(api_key=os.environ["MISTRAL_KEY"])
        case "openrouter":
            print('did openrouter')
            openrouter_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=os.environ["OPENROUTER_KEY"],
            )
            print('openrouter_client = ', openrouter_client)
        case "gemini":
            gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        case _:
            raise ValueError(f"Unknown LLM_PROVIDER: {provider!r}")

class ResumeChecker(BaseModel):
    is_it_resume: bool = Field(
        description="True if the text represents an IT resume suitable for behavioral interview, False otherwise"
    )

def check_resume(raw_text: str):
    system_prompt = f"""
        You are a concise resume classifier.
        Given the following resume text, answer whether it is an IT resume, that suitable for a behavioral interview.
        Be optimistic enough, people, who design, build and maintain software and networks are suitable.
        Restrict only fully irrelevant professions or not resume files.
        Return just a single boolean: True if it is an IT resume, False otherwise.
        """
    user_prompt = f"""
        RESUME TEXT:
        {raw_text}
        """
    result = parse_llm(llm_preparser_provider, llm_preparser_model, user_prompt, ResumeChecker, system_prompt).is_it_resume
    logger.info("check_resume | is_it_resume=%s", result)
    return result


class Resume(BaseModel):
    cleared_text: str = Field(
        description="Cleared text of the resume given. Keep all the imformation you could get"
    )

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
    logger.info("parse_resume_pdf | path=%s", pdf_path)
    doc = pymupdf.open(pdf_path)
    if len(doc) < 1:
        raise Exception("Not an IT resume.")
    if len(doc) > 10:
        raise Exception("Too long for a resume.")
    raw_text = '\n'.join([page.get_text() for page in doc])
    logger.debug("parse_resume_pdf | raw_text_len=%d", len(raw_text))

    if not check_resume(raw_text):
        raise Exception("Not an IT resume.")

    time.sleep(60)
    system_prompt = f"""
        You are an attentive editor. Extract as much information as you can from the raw resume text.
        Remove common contact information. Take just text from headers and tables. 
        Return just the clered text as a JSON field.
    """
    user_prompt = f"""
        RESUME TEXT: 
        {raw_text}
    """

    cleared_text = parse_llm(llm_parser_provider, llm_parser_model, user_prompt, Resume, system_prompt).cleared_text
    logger.debug("parse_resume_pdf | cleared_text_len=%d", len(cleared_text))
    return cleared_text

if __name__ == "__main__":
    pass