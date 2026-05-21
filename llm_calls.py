import json
import os
from dotenv import load_dotenv

from typing import List
from pydantic import BaseModel, Field

from mistralai.client import Mistral
from openai import OpenAI
from google import genai
from google.genai import types

load_dotenv()
llm_assessment_provider = os.environ["LLM_ASSESSMENT_PROVIDER"]
llm_assessment_model = os.environ["LLM_ASSESSMENT_MODEL"]

llm_plan_builder_provider = os.environ["LLM_PLAN_BUILDER_PROVIDER"]
llm_plan_builder_model = os.environ["LLM_PLAN_BUILDER_MODEL"]

llm_preparser_provider = os.environ["LLM_PREPARSER_PROVIDER"]
llm_parser_provider = os.environ["LLM_PARSER_PROVIDER"]

providers = [llm_assessment_provider, llm_plan_builder_provider, llm_preparser_provider, llm_parser_provider]
for provider in providers:
    match provider:
        case "mistral":
            mistral_client = Mistral(api_key=os.environ["MISTRAL_KEY"])
        case "openrouter":
            openrouter_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=os.environ["OPENROUTER_KEY"],
            )
        case "gemini":
            gemini_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        case _:
            raise ValueError(f"Unknown LLM_PROVIDER: {provider!r}")

def parse_openrouter(model_name: str, user_prompt: str, response_format, system_prompt=None, max_tokens: int = 2000):
    """Structured output via OpenAI's .parse() — returns a Pydantic instance."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    response = openrouter_client.beta.chat.completions.parse(
        model=model_name,
        messages=messages,
        response_format=response_format,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.parsed


def parse_mistral(model_name: str, user_prompt: str, response_format, system_prompt=None, max_tokens: int = 2000):
    """Structured output via Mistral's .parse() — returns a Pydantic instance."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    response = mistral_client.chat.parse(
        model=model_name,
        messages=messages,
        response_format=response_format,
        # max_tokens=max_tokens,
    )
    return response.choices[0].message.parsed

def parse_gemini(model_name: str, user_prompt: str, response_format, system_prompt=None, max_tokens: int = 2000):
    """Structured output via Gemini's response_schema — returns a Pydantic instance."""
    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=response_format,
        system_instruction=system_prompt,
        # max_output_tokens=max_tokens,
    )
    response = gemini_client.models.generate_content(
        model=model_name,
        contents=user_prompt,
        config=config,
    )
    return response_format(**json.loads(response.text))


def parse_llm(llm_provider, llm_model, user_prompt: str, response_format, system_prompt=None, max_tokens: int = 2000):
    print('in parse_llm, provider = ', provider)
    match llm_provider:
        case "gemini":
            return parse_gemini(llm_model, user_prompt, response_format, system_prompt, max_tokens)
        case "mistral":
            return parse_mistral(llm_model, user_prompt, response_format, system_prompt, max_tokens)
        case "openrouter":
            print('llm_provider = ', llm_provider)
            print('openrouter_client = ', openrouter_client)
            return parse_openrouter(llm_model, user_prompt, response_format, system_prompt, max_tokens)
        case _:
            raise ValueError(f"Unknown LLM_PROVIDER: {llm_provider!r}")


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

    system_prompt = f"""
        You are an HR in a big firm. You are assessing candidates answer to the given question.
        QUESTIONS:
        {question_text}

        Provide mark from 0: bad to 1: good and reasoning about the candidate.
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
    return parse_llm(llm_assessment_provider, llm_assessment_model, user_prompt, Feedback, system_prompt)

class ResumePlan(BaseModel):
    plan: List[int] = Field(description='List of 5 questions in appropriate order to ask based on the resume')

def question_list_builder(raw_resume: str, questions: list, user_answered= []) -> list:
    system_prompt = f"""
        You are an HR in a big firm. Make a structured plan of behavioral interview from the given resume text.
        Ask 5 questions from the list provided. Return just the questions ids.
        QUESTIONS:
        {questions}
        
        Try NOT to include already asked questions: {user_answered}
        """
    user_prompt = f""" 
        RESUME: 
        {raw_resume}
        """
    return parse_llm(llm_plan_builder_provider, llm_plan_builder_model, user_prompt, ResumePlan, system_prompt).plan