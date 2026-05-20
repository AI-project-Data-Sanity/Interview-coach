import os
import numpy as np
import time
import argparse
from tqdm import tqdm
from db_calls import (
    get_golden_answers, get_golden_resumes,
    get_all_questions, get_question_by_id, get_answers_by_question_id
)
from llm_calls import response_evaluator
from app import get_questions_from_llm
from resume_parser import parse_resume_pdf
from sklearn.metrics import mean_absolute_error, mean_squared_error, root_mean_squared_error

def mark_evaluator(split = 'val'):
    mark_to_float = {
        'bad': 0.0,
        'middle': 0.5,
        'good': 1.0,
    }

    golden_set = get_golden_answers(split)
    golden_marks = []
    got_marks = []
    for g in tqdm(golden_set):
        question_text = get_question_by_id(g['question_id'])
        prefounded_answers = get_answers_by_question_id(g['question_id'])
        feedback = response_evaluator(question_text, g['answer'], prefounded_answers)
        got_marks.append(feedback.mark)
        golden_marks.append(mark_to_float[g['mark']])
        time.sleep(15)

    mae = mean_absolute_error(golden_marks, got_marks)
    mse = mean_squared_error(golden_marks, got_marks)
    rmse = root_mean_squared_error(golden_marks, got_marks)
    print('split = ', split)
    print(f"MAE: {mae:.5f}")
    print(f"MSE: {mse:.5f}")
    print(f"RMSE: {rmse:.5f}")

def plan_builder_evaluator(golden_resumes_path: str, split :str = 'val'):
    false_negatives = 0
    false_positives = 0
    fn_list, fp_list = [], []
    wrong_plan_len = 0
    default_plan_len = 5
    ious = []

    golden_set = get_golden_resumes(split)
    questions = get_all_questions()
    for g in tqdm(golden_set):
        golden_plan = g['questions_plan']
        try:
            parsed_text = parse_resume_pdf(os.path.join(golden_resumes_path, split, g['filename']))
            plan = get_questions_from_llm(parsed_text, questions)
            ious.append(
                len(np.intersect1d(plan, golden_plan, assume_unique=True)) / len(np.union1d(plan, golden_plan))
            )
            if len(plan) != default_plan_len:
                wrong_plan_len += 1
            time.sleep(10)
        except Exception as e:
            print('e = ', e)
            if g['is_it_resume']:
                false_positives += 1
                fp_list.append(g['filename'])
            else:
                false_negatives += 1
                fn_list.append(g['filename'])

    print('split = ', split)
    print('Right qualified as not IT resume: ', false_negatives)
    print('List: ', fn_list)
    print('Wrong qualified as not IT resume: ', false_positives)
    print('List: ', fp_list)
    print('Wrong plan length !=', default_plan_len, ': ', wrong_plan_len)
    print(f"Mean IoU: {np.mean(ious):.5f}")

if __name__ == "__main__":
    """
    Script to evaluate the quality of the whole system
    """
    parser = argparse.ArgumentParser(
        description="A parser to get all incoming files from search and the json with plans predictions produced by Opus")
    parser.add_argument("--golden-resumes-path",
        help="path to the directory with val/test folders with the resumes",
        default='data/golden_resumes'
    )
    args = parser.parse_args()
    # plan_builder_evaluator(args.golden_resumes_path, 'val')
    mark_evaluator('val')
