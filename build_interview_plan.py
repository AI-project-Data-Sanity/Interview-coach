import os
import re
import sqlite3
from pathlib import Path
from mistralai.client import Mistral

from resume_parser import parse_resume_pdf

# TODO: check how to safely store a secret in a docker container
mistral_key = os.environ["mistral_key"]
model_name = "mistral-small-latest"


def main() -> None:
    # are we storing user's file somewhere?
    # use my old resume for experiments, will need some .pdf file for now
    resume_path = Path("../Chuviliaeva_resume_linkedin_old.pdf")
    # TODO: catch not-pdf opening exceptions
    parsed_text = parse_resume_pdf(resume_path)
    mistral_client = Mistral(api_key=mistral_key)

    # may become a function
    # needs the path to the db file. Will create if not exist
    conn = sqlite3.connect("../interview.db")
    cursor = conn.execute("SELECT question_id, question FROM questions")
    questions = [
        {"question_id": row[0], "question": row[1]}
        for row in cursor.fetchall()
    ]
    conn.close()

    system_prompt = f"""
    You are an HR in a big firm. Make a structured plan of behavioral interview from the given resume text.
    Ask 3-7 questions from the list. Return just questions ids.
    QUESTIONS:
    {questions}
    """
    user_prompt = f""" 
    RESUME: 
    {parsed_text}
    """

    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    response = mistral_client.chat.complete(model=model_name, messages=messages)

    print('model response = ', response)
    chosen_ids = [int(raw_id) for raw_id in re.findall(r'[1-9]+', response.choices[0].message.content)]
    print('chosen_ids = ', chosen_ids)
    chosen_questions = [questions[id] for id in chosen_ids]

    known_answers = []
    # reconnect to db - controversial
    conn = sqlite3.connect("../interview.db")
    for id in chosen_ids:
        # may become a function
        cursor = conn.execute("""
            SELECT answer_id, question_id, answer, mark, reason FROM answers
            WHERE question_id = ?""", (id,)
        )

        result = [{
            "answer_id": row[0],
            "answer": row[2],
            "mark": row[3],
            "reason": row[4],
        } for row in cursor.fetchall()]

        known_answers.append({"question_id": id, "answers": result})

    conn.close()

    print('chosen_questions = ', chosen_questions)
    print('known_answers = ', known_answers)

if __name__ == "__main__":
    main()