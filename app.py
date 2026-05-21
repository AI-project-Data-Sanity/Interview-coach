import os
import re
import argparse
from dotenv import load_dotenv
from pathlib import Path
from typing import Union

from mistralai.client import Mistral

from llm_calls import response_evaluator, question_list_builder
from resume_parser import parse_resume_pdf
from db_calls import (
    add_user, save_resume_db, get_resume_db,
    get_all_questions, get_question_by_id, get_answers_by_question_id, save_user_answered,
    save_user_answered, get_user_answered
)

load_dotenv()
mistral_key = os.environ["MISTRAL_KEY"]

def register_user(user_id: int, username: str):
    add_user(user_id, username)

def save_resume(user_id: int, pdf_path: Union[str, Path]):
    parsed_text = parse_resume_pdf(pdf_path)
    save_resume_db(user_id, parsed_text)

def get_question_list(user_id: int) -> Union[list, None]:
    user_answered = get_user_answered(user_id)
    parsed_text = get_resume_db(user_id)
    questions = get_all_questions()
    return question_list_builder(parsed_text, questions, user_answered)

def get_question_text_by_id(question_id: int)->str:
    return get_question_by_id(question_id)

def get_llm_feedback(user_id: int, question_id: int, answer:str) -> Union[str, None]:
    save_user_answered(user_id, question_id)
    question_text = get_question_by_id(question_id)
    prefounded_answers = get_answers_by_question_id(question_id)
    assessment = response_evaluator(question_text, answer, prefounded_answers)

    result = f"**Mark**: {assessment.mark}\n"
    result += f"**STAR usage**: {assessment.STAR}\n"
    result += f"**Motivation**: {assessment.motivation}\n"
    result += f"**Proactivity**: {assessment.proactivity}\n"
    result += f"**Adaptability**:  {assessment.adaptability}\n"
    result += f"**Perseverance**: {assessment.perseverance}\n"
    result += f"**Nonconflicteness**: {assessment.nonconflicteness}\n"
    result += f"**Empathy**: {assessment.empathy}\n"
    result += f"**Growth**: {assessment.growth}\n"
    result += f"**Communication**: {assessment.communication}\n"

    # log in the DB???
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A simple parser for a simple script")
    parser.add_argument('--input-resume', help="path to the resume pdf file",
        default="val/Chuviliaeva_resume_linkedin_old.pdf"
    )
    parser.add_argument('--db-path', help="path to the file with db",
        default="val/interview.db"
    )
    parser.add_argument('--output', help="path to the output .txt file",
        default="val/output2.txt"
    )
    args = parser.parse_args()

    register_user(user_id=1234567, username='@mira_bl')
    save_resume(user_id=1234567, pdf_path=args.input_resume)
    question_ids = get_question_list(user_id=1234567)
    with open(args.output, 'w+') as f:
        for q_id in question_ids:
            f.write("######question:" + get_question_text_by_id(q_id))
            f.write(get_llm_feedback(user_id=1234567, question_id=q_id, answer="I don't know"))