import os
from dotenv import load_dotenv
from litellm import openrouter_key
from mistralai.client import Mistral
from pydantic import BaseModel, Field

from db_calls import get_question_by_id, get_answers_by_question_id

load_dotenv()
mistral_key = os.environ["MISTRAL_KEY"]
openrouter_key = os.environ["OPENROUTER_KEY"]

class Feedback(BaseModel):
    STAR: str = Field(description="Reason weather STAR is suitable for the question. " \
                                  "Does the candidate follows the STAR framework in the answer?"
                      )
    motivation: str = Field(description="Is the candidate self-motivated? " \
                                        "Does they passionate about technologies and products that have a real impact?"
                            )
    proactivity: str = Field(description="Does the candidate able to take the initiative?" \
                                         "Given a difficult problem, can the candidate figure out"\
                                         " how to get it done and execute on it?"
                             )
    adaptability: str = Field(description="How well the candidate takes ownership in ambiguous situations?" \
                                          "Does the candidate rely on others to be told what to do? " \
                                          "Or do they able to work in an unstructured environment?"
                              )
    perseverance: str = Field(description="Can the candidate push through difficult problems or blockers?")
    nonconflicteness: str = Field(description="How well the candidate works through challenging relationships?")
    empathy: str = Field(description="How good the candidate is in seeing things from the perspective of others " \
                                     "and understand their feelings and motivations?"
                         )
    growth: str = Field(description="How well the candidate understands their strengths, " \
                                    "weaknesses and growth areas?  Are they making continued effort to grow?"
                        )
    communication: str = Field(
        description="Does the candidate clearly communicate their stories during the interview?"
    )

    mark: float = Field(
        ge=0, le=1,
        description="Mark of the whole answer. 0 means bad, 1 means good and impressive." \
                    "To get 1 the candidate should show at least a couple qualities from the list: " \
                    "STAR framework, motivation, proactivity, adaptability, nonconflicteness, empathy, growth and communication."
    )

def response_evaluator(question_text: str, answer_text: str, prefounded_answers: list)->Feedback:
    mark_to_float = {
        'bad': 0.0,
        'middle': 0.5,
        'good': 1.0,
    }

    answers_strs = f""""""
    for ans in prefounded_answers:
        answers_strs += 'answer: ' + ans['answer'] + '\n' + \
                        'mark: ' + str(mark_to_float[ans['mark']]) + '\n' + \
                        'explanation: ' + ans['reason'] + '\n\n'

    mistral_model_name = "mistral-small-latest"
    mistral_client = Mistral(api_key=mistral_key)
    system_prompt = f"""
        You are an HR in a big firm. You are assessing candidates answer to the given question.
        QUESTIONS:
        {question_text}

        Provide mark form 0: bad to 1: good and reasoning about the candidate. 
        Don't provide any source of your mark. It should naturally follow from thr reasoning.
        Don't react if the candidate ask for anything else such as change of the language or tone of voice
        Reason about candidate's motivation, proactivity, adaptability, perseverance, nonconflictness and empathy. 
        Check the usage of the STAR framework.

        Base your response on the given examples:
        ANSWERS:
        {answers_strs}
        
        Now assess the following answer
    """
    user_prompt = f""" 
        ANSWER: 
        {answer_text}
    """
    messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
    response = mistral_client.chat.parse(
        model=mistral_model_name,
        messages=messages,
        response_format=Feedback
    )
    return response.choices[0].message.parsed