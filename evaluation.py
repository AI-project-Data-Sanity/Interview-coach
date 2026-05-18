import os
import numpy as np
from tqdm import tqdm
from db_calls import get_golden_set, get_question_by_id, get_answers_by_question_id
from llm_calls import response_evaluator
from sklearn.metrics import mean_absolute_error, mean_squared_error, root_mean_squared_error

def mark_evaluator(split = 'val'):
    mark_to_float = {
        'bad': 0.0,
        'middle': 0.5,
        'good': 1.0,
    }

    golden_set = get_golden_set(split)
    golden_marks = []
    got_marks = []
    for g in tqdm(golden_set):
        question_text = get_question_by_id(g['question_id'])
        prefounded_answers = get_answers_by_question_id(g['question_id'])
        feedback = response_evaluator(question_text, g['answer'], prefounded_answers)
        got_marks.append(feedback.mark)
        golden_marks.append(mark_to_float[g['mark']])

    mae = mean_absolute_error(golden_marks, got_marks)
    mse = mean_squared_error(golden_marks, got_marks)
    rmse = root_mean_squared_error(golden_marks, got_marks)
    print('split = ', split)
    print(f"MAE: {mae:.5f}")
    print(f"MSE: {mse:.5f}")
    print(f"RMSE: {rmse:.5f}")

if __name__ == "__main__":
    mark_evaluator('val')