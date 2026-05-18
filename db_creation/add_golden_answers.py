import os
import pandas as pd
import argparse
import sqlite3
import json
from sklearn.model_selection import train_test_split
from dotenv import load_dotenv

load_dotenv()
db_path = os.path.join('..', os.environ["DB_PATH"])

def add_golden_answer(
        conn: sqlite3.Connection, golden_answer: str,
        question_id: int, question: str, mark: str, split: str
    ):
    conn.execute("""
        update questions set question = ? where question_id = ?
        """, (question, question_id)
    )
    conn.execute("""
        insert into answers_golden (golden_answer, question_id, mark, split) 
        values (?, ?, ?, ?);
        """, (golden_answer, question_id, mark, split)
    )
    conn.commit()

def fill_answers(
        conn: sqlite3.Connection, common_list: list[dict], matches: dict,
        train_size: float, mark: str
    ):
    nums = sorted(matches.keys())
    nums_test, nums_val = train_test_split(nums, train_size=train_size)

    for question_num in nums_test:
        question = common_list[question_num]
        add_golden_answer(
            conn, question['answer'],
            matches[question_num], question['question'], mark, 'test'
        )
    conn.commit()

    for question_num in nums_val:
        question = common_list[question_num]
        add_golden_answer(
            conn, question['answer'],
            matches[question_num], question['question'], mark, 'val'
        )
    conn.commit()

if __name__ == "__main__":
    """
    Script to add golden answers to the database. 
    Uses answers from awesome-behavioral as golden good
    Uses the matches file to find all the questions from awesome-behavioral in the db
    """
    parser = argparse.ArgumentParser(description="A simple parser to get all supporting files")
    parser.add_argument("--matches-path",
        help="path to the file with id matches for the old questions and questions from the awesome-behavioral repo",
        default='../data/matches.json'
    )
    parser.add_argument("--awesome-questions-path",
        help="path to the file with the questions scraped from the awesome-behavioral repo",
        default='../data/questions_awesome.json'
    )
    parser.add_argument("--bad-answers-path",
        help="path to the file with the pregenerated bad answers for the golden dataset",
        default='../data/golden_answers_bad.json'
    )

    args = parser.parse_args()

    with open(args.matches_path) as f:
        matches = json.load(f)

    with open(args.awesome_questions_path) as f:
        awesome_questions = json.load(f)

    with open(args.bad_answers_path) as f:
        golden_bad = json.load(f)

    conn = sqlite3.connect(db_path)

    """CAREFUL: deletes golden set"""
    ''' conn.execute("""delete from answers_golden;""") '''
    """ conn.commit() """

    # recounting matches to make unique and easy access
    new_matches = {}
    index_start = 90
    for new_key in range(len(awesome_questions)):
        if str(new_key) in matches:
            new_val = (int(matches[str(new_key)][0]) - 1) // 3
            if new_val not in new_matches.values():
                new_matches[new_key] = new_val
        else:
            new_matches[new_key] = index_start
            index_start += 1

    fill_answers(conn, awesome_questions, new_matches, 0.5, 'good')
    bad_matches = {i: bad_ans['question_id'] for i, bad_ans in enumerate(golden_bad)}
    fill_answers(conn, golden_bad, bad_matches, 0.5, 'bad')

    conn.close()