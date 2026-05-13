import pandas as pd
import argparse
import sqlite3

def drop_tables(conn: sqlite3.Connection):
    """ !!!CAREFUL!!! FULL DELETION. Call ONLY to start the bd from scratch """
    conn.execute("""drop table if exists questions""")
    conn.execute("""drop table if exists answers""")
    conn.execute("""drop table if exists users""")
    conn.execute("""drop table if exists answers_golden""")
    conn.execute("""drop table if exists resume_golden""")
    conn.commit()


def create_tables(conn: sqlite3.Connection):
    conn.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        question_id INTEGER PRIMARY KEY,
        question TEXT NOT NULL,
        split TEXT CHECK(split IN ('test', 'val', 'no'))
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS answers (
        answer_id INTEGER PRIMARY KEY,
        question_id INTEGER NOT NULL,
        answer TEXT NOT NULL,
        mark TEXT CHECK(mark IN ('bad', 'middle', 'good')),
        reason TEXT,
        FOREIGN KEY (question_id) REFERENCES questions(question_id)
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_name TEXT NOT NULL,
        resume_text TEXT,
        asked_questions TEXT,
        dialog_text TEXT
    )
    """)
    # may do a separate table for questions asked and answers

    conn.execute("""
    CREATE TABLE IF NOT EXISTS answers_golden (
    golden_answer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    golden_answer TEXT NOT NULL,
    question_id INTEGER NOT NULL,
    mark TEXT CHECK(mark IN ('bad', 'good')),
    FOREIGN KEY (question_id) REFERENCES questions(question_id)
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS resume_golden (
    resume_id INTEGER PRIMARY KEY,
    filename TEXT NOT NULL,
    is_resume BOOLEAN NOT NULL,
    is_it_resume BOOLEAN NOT NULL
    )
    """)
    conn.commit()

def fill_questions(conn: sqlite3.Connection, answers: pd.DataFrame):
    # Fill questions table with unique questions
    questions_df = answers[["question_id", "question", "split"]].drop_duplicates()
    questions_df.to_sql("questions", conn, if_exists="append", index=False)
    conn.commit()

def fill_answers(conn: sqlite3.Connection, answers: pd.DataFrame):
    # Fill answers table
    answers_df = answers[["answer_id", "question_id", "answer", "mark", "reason"]].copy()
    answers_df.to_sql("answers", conn, if_exists="append", index=False)
    conn.commit()

if __name__ == "__main__":
    """Script to take the .csv file and create the database"""
    parser = argparse.ArgumentParser(description="A simple parser to get supporting resources for the db")
    parser.add_argument(
        "--data-path", help="path to the structured .csv input file",
        default='../data/interview_answers.csv'
    )
    parser.add_argument(
        "--db-path", help="path to the database file for creation or usage",
        default='../data/interview.db'
    )
    parser.add_argument("--new-data-path", help="path to the reindex .csv",
        default='../data/interview_answers_reindex.csv'
    )
    args = parser.parse_args()

    interview_data = pd.read_csv(args.data_path)
    answers = interview_data.rename(columns={'id': 'answer_id'})
    answers['answer_id'] = answers['answer_id'] - 1
    answers['question_id'] = answers['answer_id'] // 3
    answers['answer'] = answers['answers']
    answers.drop(columns='answers', inplace=True)
    answers = answers.reindex(columns=['question_id', 'question', 'answer_id', 'answer', 'mark', 'reason'])
    answers['split'] = ['no'] * len(answers)
    answers.to_csv(args.new_data_path, index=False)
    # will create if not exist
    conn = sqlite3.connect(args.db_path)
    drop_tables(conn)
    create_tables(conn)
    fill_questions(conn, answers)
    fill_answers(conn, answers)
    conn.close()