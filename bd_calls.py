import sqlite3

def get_all_questions(db_path: str)->list:
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

def get_answers_by_id(db_path: str, id: int)->list:
    """
    Function to get all answers associated with a question by the question id.
    Now there are always 3 generated answers for 1 question. It may become diverse.
    Uses a list to store the answers as dicts with keys: answer_id, answer, mark, reason
    """
    conn = sqlite3.connect(db_path)
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
    conn.close()
    return result
