import os
import numpy as np
import time
from tqdm import tqdm
from dotenv import load_dotenv
from sklearn.metrics import mean_absolute_error, mean_squared_error, root_mean_squared_error
from db_calls import (
    get_golden_answers, get_golden_resumes,
    get_all_questions, get_question_by_id, get_answers_by_question_id
)
from llm_calls import response_evaluator, question_list_builder
from llm_resume_parser import parse_resume_pdf

load_dotenv()
golden_resumes_path = os.environ['GOLDEN_RESUMES_PATH']

def mark_evaluator(split = 'val'):
    mark_to_float = {
        'bad': 0.0,
        'middle': 0.5,
        'good': 1.0,
    }

    golden_set = get_golden_answers(split)
    golden_marks = []
    got_marks = []
    for g in tqdm(golden_set[0:1]):
        question_text = get_question_by_id(g['question_id'])
        prefounded_answers = get_answers_by_question_id(g['question_id'])
        for attempt in range(3):
            try:
                feedback = response_evaluator(question_text, g['answer'], prefounded_answers)
                break
            except Exception:
                if attempt == 2:
                    raise
                time.sleep(10 * (attempt + 1))
        got_marks.append(feedback.mark)
        golden_marks.append(mark_to_float[g['mark']])

    mae = mean_absolute_error(golden_marks, got_marks)
    mse = mean_squared_error(golden_marks, got_marks)
    rmse = root_mean_squared_error(golden_marks, got_marks)
    print('split = ', split)
    print(f"MAE: {mae:.5f}")
    print(f"MSE: {mse:.5f}")
    print(f"RMSE: {rmse:.5f}")

def plan_builder_evaluator(golden_resumes_path: str, split :str = 'val'):
    true_negatives = 0
    false_negatives = 0
    false_positives = 0
    tn_list, fn_list, fp_list = [], [], []
    wrong_plan_len = 0
    default_plan_len = 5
    ious = []

    golden_set = get_golden_resumes(split)
    questions = get_all_questions()
    parsed_text = ''
    for g in tqdm(golden_set):
        golden_plan = g['questions_plan']
        done = False
        for attempt in range(3):
            try:
                parsed_text = parse_resume_pdf(os.path.join(golden_resumes_path, split, g['filename']))
                break
            except Exception as e:
                print('Parser Exception:', e)
                if str(e) == "Not an IT resume." or str(e) == "Too long for a resume.":
                    done = True
                    if g['is_it_resume']:
                        false_negatives += 1
                        fn_list.append(g['filename'])
                    else:
                        true_negatives += 1
                        tn_list.append(g['filename'])
                    break
                else:
                    if attempt == 2:
                        raise
                    time.sleep(10 * (attempt + 1))

        if not done:
            for attempt in range(3):
                try:
                    plan = question_list_builder(parsed_text, questions)
                    break
                except Exception as e:
                    print('Plan builder exception', e)
                    if attempt == 2:
                        raise
                    time.sleep(10 * (attempt + 1))

            ious.append(
                len(np.intersect1d(plan, golden_plan, assume_unique=True)) / len(np.union1d(plan, golden_plan))
            )
            if len(plan) != default_plan_len:
                wrong_plan_len += 1

            if not g['is_it_resume']:
                false_positives += 1
                fp_list.append(g['filename'])


    print('split = ', split)
    print('Right qualified as not IT resume: ', true_negatives)
    print('List: ', tn_list)
    print('Wrong qualified as not IT resume: ', false_negatives)
    print('List: ', fn_list)
    print('Wrong qualified as IT resume: ', false_positives)
    print('List: ', fp_list)
    print('Wrong plan length !=', default_plan_len, ': ', wrong_plan_len)
    print(f"Mean IoU: {np.mean(ious):.5f}")

if __name__ == "__main__":
    """
    Script to evaluate the quality of the whole system
    """
    plan_builder_evaluator(golden_resumes_path, 'val')
    # mark_evaluator(split = 'val')
