import numpy as np
import argparse
import json
from db_calls import get_all_questions

if __name__ == "__main__":
    """
    Script to choose bad-answered questions for the golden dataset. Answers are generated
    """
    parser = argparse.ArgumentParser(description="A simple parser to get data")
    parser.add_argument(
        "--db-path", help="path to the database file for creation or usage",
        default='../data/interview.db'
    )
    parser.add_argument("--save-path",
        help="path to save the file with the bad answers",
        default='../data/golden_questions_bad.json'
    )

    args = parser.parse_args()
    questions = get_all_questions(args.db_path)
    bad_questions = sorted(
        np.random.choice(questions, 50, replace=False),
        key=lambda q: q['question_id']
    )

    with open(args.save_path, 'w') as f:
        json.dump(bad_questions, f)