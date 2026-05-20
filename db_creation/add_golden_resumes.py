import os
import argparse
import sqlite3
import json
from dotenv import load_dotenv

load_dotenv()
db_path = os.path.join('..', os.environ["DB_PATH"])

def add_golden_resume(
        conn: sqlite3.Connection, filename: str, is_it_resume: bool, split: str, questions_plan: str
    ):
    conn.execute("""
        insert into resumes_golden (filename, is_it_resume, split, questions_plan) 
        values (?, ?, ?, ?);
        """, (filename, is_it_resume, split, questions_plan)
    )
    conn.commit()


if __name__ == "__main__":
    """
    Script to add golden resumes with interview plans to the database. 
    Uses plans predifined and refined by Opus 
    """
    parser = argparse.ArgumentParser(
        description="A parser to get all incoming files from search and the json with plans predictions produced by Opus")
    parser.add_argument("--golden-resumes-path",
        help="path to the directory with val/test folders with the resumes and structured jsons from Opus",
        default='../data/golden_resumes'
    )
    args = parser.parse_args()
    conn = sqlite3.connect(db_path)
    """CAREFUL: deletes resumes golden set"""
    'conn.execute("""delete from resumes_golden;""")'
    """conn.commit()"""

    for folder in ['val', 'test']:
        folder_path = os.path.join(args.golden_resumes_path, folder)
        json_path = os.path.join(folder_path, 'interview_plans.json')
        with open(json_path, 'r') as f:
            plans = json.load(f)

        resume_index = {resume['resume_file_name']: i for i, resume in enumerate(plans['resumes'])}
        for resume_file in os.listdir(folder_path):
            if not resume_file.endswith('.pdf'):
                continue
            selected_plan = None
            if resume_file in resume_index:
                selected_plan = [
                    q['question_id'] for q in plans['resumes'][resume_index[resume_file]]['selected_questions']
                ]
            add_golden_resume(conn, resume_file, selected_plan is not None, folder, json.dumps(selected_plan))

    conn.execute(
        """update resumes_golden set is_it_resume = ? where filename = ?""",
        (False, 'Senior Lecturer.pdf',)
    )

    conn.execute(
        """update resumes_golden set is_it_resume = ? where filename = ?""",
        (False, 'Marketing.pdf',)
    )
    conn.commit()
    conn.close()