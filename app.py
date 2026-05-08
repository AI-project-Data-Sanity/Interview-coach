import os
import re
import argparse
from pathlib import Path
from time import sleep

from mistralai.client import Mistral
from resume_parser import parse_resume_pdf
from bd_calls import get_all_questions, get_answers_by_id

def get_questions_from_llm(raw_resume: str, questions: list) -> list:
    # TODO: check how to safely store a secret in a docker container
    mistral_key = os.environ["mistral_key"]
    model_name = "mistral-small-latest"
    mistral_client = Mistral(api_key=mistral_key)
    system_prompt = f"""
        You are an HR in a big firm. Make a structured plan of behavioral interview from the given resume text.
        Ask 3-7 questions from the list. Return just questions ids.
        QUESTIONS:
        {questions}
        """
    user_prompt = f""" 
        RESUME: 
        {raw_resume}
    """
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    response = mistral_client.chat.complete(model=model_name, messages=messages)
    chosen_ids = [int(raw_id) for raw_id in re.findall(r'[1-9]+', response.choices[0].message.content)]
    return chosen_ids


def main() -> None:
    parser = argparse.ArgumentParser(description="A simple parser for a simple script")
    parser.add_argument('--input-resume', help="path to the resume pdf file",
        default="data/Chuviliaeva_resume_linkedin_old.pdf"
    )
    parser.add_argument('--db-path', help="path to the file with db",
        default="data/interview.db"
    )
    parser.add_argument('--output', help="path to the output .txt file",
        default="data/output2.txt"
    )
    args = parser.parse_args()

    # are we storing user's file somewhere?
    # use my old resume for experiments, will need some .pdf file for now
    # TODO: catch not-pdf opening exceptions
    parsed_text = parse_resume_pdf(Path(args.input_resume))
    # TODO: add models diversity
    questions = get_all_questions(args.db_path)
    question_ids = get_questions_from_llm(parsed_text, questions)

    with open(args.output, 'w+') as f:

        f.write('chosen ids: ' + str(question_ids))
        chosen_questions = [questions[id] for id in question_ids]

        known_answers = []
        for id in question_ids:
            known_answers.append({"question_id": id, "answers": get_answers_by_id(args.db_path, id)})
        f.write('chosen_questions = ' + str(chosen_questions))
        f.write('known_answers = ' + str(known_answers))

if __name__ == "__main__":
    main()