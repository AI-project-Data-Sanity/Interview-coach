import pandas as pd
import sqlite3

# Script to take the .csv file and create the database
# need the path to interview_answers.csv to run
interview_data = pd.read_csv('../interview_answers.csv')
answers = interview_data.rename(columns={'id': 'answer_id'})

answers['answer_id'] = answers['answer_id'] - 1
answers['question_id'] = answers['answer_id'] // 3
answers['answer'] = answers['answers']
answers.drop(columns='answers', inplace=True)
answers = answers.reindex(columns=['question_id', 'question',  'answer_id', 'answer', 'mark', 'reason'])

answers.to_csv('../answers_reindex.csv', index=False)
# will create if not exist
conn = sqlite3.connect("../interview.db")

'''
!!!CAREFUL!!! FULL DELETION
conn.execute("""drop table if exists questions""")
conn.execute("""drop table if exists answers""")
conn.execute("""drop table if exists users""")
'''

conn.execute("""
CREATE TABLE IF NOT EXISTS questions (
    question_id INTEGER PRIMARY KEY,
    question TEXT NOT NULL
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

# Fill questions table with unique questions
questions_df = answers[["question_id", "question"]].drop_duplicates()
questions_df.to_sql("questions", conn, if_exists="append", index=False)

# Fill answers table
answers_df = answers[["answer_id", "question_id", "answer", "mark", "reason"]].copy()
answers_df.to_sql("answers", conn, if_exists="append", index=False)

conn.commit()
conn.close()