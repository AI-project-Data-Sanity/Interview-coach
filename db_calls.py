import os
import json
import sqlite3
from dotenv import load_dotenv

load_dotenv()
db_path = os.environ["DB_PATH"]

def get_all_questions()->list:
    """
    Function to get all questions from database.
    Returns a list of dicts. Every dict has strictly 2 keys: question_id, question
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT question_id, question FROM questions")
    questions = [
        {"question_id": row[0], "question": row[1]}
        for row in cursor.fetchall()
    ]
    conn.close()
    return questions

def get_question_by_id(question_id: int)->str:
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("""
        select question from questions where question_id = ?""",
        (question_id,)
    )
    question = cursor.fetchall()[0][0]
    conn.close()
    return question

def get_answers_by_question_id(id: int)->list:
    """
    Function to get all answers associated with a question by the question id.
    Now there are always 3 generated answers for 1 question. It may become diverse.
    Uses a list to store the answers as dicts with keys: answer_id, answer, mark, reason
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        """SELECT answer_id, question_id, answer, mark, reason FROM answers
        WHERE question_id = ?""",
        (id,)
    )
    result = [{
        "answer_id": row[0],
        "answer": row[2],
        "mark": row[3],
        "reason": row[4],
    } for row in cursor.fetchall()]
    conn.close()
    return result

def add_user(user_id: int, username: str):
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        """select user_id, user_name from users where user_id = ?""",
        (user_id,)
    )
    res = cursor.fetchall()
    if not res:
        conn.execute(
            """
            insert into users (user_id, user_name, resume_text, asked_questions, dialog_text) values (?, ?, ?, ?, ?)
            """,
            (user_id, username, '', json.dumps([]), '')
        )
    else:
        if res[0][1] != username:
            conn.execute(
                """update users set user_name = ? where user_id = ?""",
                (username, user_id)
            )
    conn.commit()
    conn.close()

def save_resume_db(user_id: int, parsed_text: str):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """update users set resume_text = ? where user_id = ?""",
        (parsed_text, user_id)
    )
    conn.commit()
    conn.close()

def get_resume_db(user_id: int):
    conn = sqlite3.connect(db_path)
    cursor = conn.execute(
        """select resume_text from users where user_id = ?""",
        (user_id,)
    )
    res = cursor.fetchall()[0][0]
    conn.close()
    return res

def get_user_answered(user_id: int):
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("""
        select asked_questions from users where user_id = ?""",
        (user_id,)
    )
    asked_questions = json.loads(cursor.fetchall()[0][0])
    conn.close()
    return asked_questions

def save_user_answered(user_id: int, question_id: int, ):
    asked_questions = get_user_answered(user_id)
    asked_questions.append(question_id)
    asked_questions = list(set(asked_questions))
    conn = sqlite3.connect(db_path)
    conn.execute(
        """update users set asked_questions = ? where user_id = ?""",
        (json.dumps(asked_questions), user_id)
    )
    conn.commit()
    conn.close()

def get_golden_answers(split = 'val'):
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("""
        select golden_answer, question_id, mark, split from answers_golden
        where split = ?
        """, (split,)
    )

    res = [ {
        "answer": row[0],
        "question_id": row[1],
        "mark": row[2]
    } for row in cursor.fetchall()]
    conn.close()
    return res

def get_golden_resumes(split = 'val'):
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("""
        select resume_id, filename, is_it_resume, questions_plan from resumes_golden
        where split = ?
        """,(split,)
    )
    res = [{
        "filename": row[1],
        "is_it_resume": row[2],
        "questions_plan": row[3],
    } for row in cursor.fetchall()]
    conn.close()
    return res


if __name__ == '__main__':
    pass