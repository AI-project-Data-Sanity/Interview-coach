import json
import pytest
from unittest.mock import patch, MagicMock

import llm_calls
from llm_calls import Feedback, ResumePlan, response_evaluator, question_list_builder


def _make_feedback(**overrides) -> Feedback:
    defaults = dict(
        STAR="Used STAR well",
        motivation="Very motivated",
        proactivity="Shows initiative",
        adaptability="Adapts quickly",
        perseverance="Pushes through",
        nonconflicteness="Works well with others",
        empathy="Understands others",
        growth="Continuous learner",
        communication="Clear communicator",
        mark=0.8,
    )
    defaults.update(overrides)
    return Feedback(**defaults)


class TestFeedbackModel:
    def test_mark_bounds_zero(self):
        fb = _make_feedback(mark=0.0)
        assert fb.mark == 0.0

    def test_mark_bounds_one(self):
        fb = _make_feedback(mark=1.0)
        assert fb.mark == 1.0

    def test_mark_below_zero_raises(self):
        with pytest.raises(Exception):
            _make_feedback(mark=-0.1)

    def test_mark_above_one_raises(self):
        with pytest.raises(Exception):
            _make_feedback(mark=1.1)


class TestResponseEvaluator:
    def _capture(self, question="Question?", answer="Answer.", prefounded=None):
        """Call response_evaluator and return the parse_llm call_args."""
        with patch("llm_calls.parse_llm", return_value=_make_feedback()) as mock_parse:
            response_evaluator(question, answer, prefounded or [])
            return mock_parse.call_args

    def test_answer_in_user_prompt(self):
        call_args = self._capture(answer="I led the database migration single-handedly.")
        user_prompt = call_args.args[0]
        assert "I led the database migration single-handedly." in user_prompt

    def test_question_in_system_prompt(self):
        call_args = self._capture(question="Describe a conflict you resolved.")
        system_prompt = call_args.args[2]
        assert "Describe a conflict you resolved." in system_prompt

    def test_response_format_is_feedback(self):
        call_args = self._capture()
        assert call_args.args[1] is Feedback

    def test_prefounded_answer_text_in_system_prompt(self):
        prefounded = [{"answer": "UniqueAnswerXYZ123", "mark": "good", "reason": "Clear STAR"}]
        call_args = self._capture(prefounded=prefounded)
        assert "UniqueAnswerXYZ123" in call_args.args[2]

    def test_bad_mark_converted_to_zero_in_prompt(self):
        prefounded = [{"answer": "Gave up.", "mark": "bad", "reason": "No effort"}]
        call_args = self._capture(prefounded=prefounded)
        assert "0.0" in call_args.args[2]

    def test_middle_mark_converted_to_half_in_prompt(self):
        prefounded = [{"answer": "Did okay.", "mark": "middle", "reason": "Adequate"}]
        call_args = self._capture(prefounded=prefounded)
        assert "0.5" in call_args.args[2]

    def test_good_mark_converted_to_one_in_prompt(self):
        prefounded = [{"answer": "Excellent.", "mark": "good", "reason": "Outstanding"}]
        call_args = self._capture(prefounded=prefounded)
        assert "1.0" in call_args.args[2]

    def test_prefounded_reason_in_system_prompt(self):
        prefounded = [{"answer": "Some answer", "mark": "good", "reason": "UniqueReasonABC456"}]
        call_args = self._capture(prefounded=prefounded)
        assert "UniqueReasonABC456" in call_args.args[2]


class TestQuestionListBuilder:
    def _capture(self, resume="resume text", questions=None, user_answered=None):
        mock_plan = ResumePlan(plan=[1, 2])
        with patch("llm_calls.parse_llm", return_value=mock_plan) as mock_parse:
            question_list_builder(resume, questions or [], user_answered or [])
            return mock_parse.call_args

    def test_resume_text_in_user_prompt(self):
        call_args = self._capture(resume="Senior Python engineer at a fintech startup")
        assert "Senior Python engineer at a fintech startup" in call_args.args[0]

    def test_response_format_is_resume_plan(self):
        call_args = self._capture()
        assert call_args.args[1] is ResumePlan

    def test_questions_appear_in_system_prompt(self):
        questions = [{"question_id": 7, "question": "UniqueQuestionTextQQQ"}]
        call_args = self._capture(questions=questions)
        assert "UniqueQuestionTextQQQ" in call_args.args[2]

    def test_user_answered_list_in_system_prompt(self):
        call_args = self._capture(user_answered=[3, 7])
        assert "[3, 7]" in call_args.args[2]

    def test_empty_user_answered_in_prompt(self):
        call_args = self._capture(user_answered=[])
        assert "[]" in call_args.args[2]

    def test_returns_plan_ids(self):
        mock_plan = ResumePlan(plan=[2, 5, 8, 1, 4])
        with patch("llm_calls.parse_llm", return_value=mock_plan):
            result = question_list_builder("resume", [])
            assert result == [2, 5, 8, 1, 4]


def _make_mistral_mock(parsed_obj):
    mock_client = MagicMock()
    mock_client.chat.parse.return_value.choices[0].message.parsed = parsed_obj
    return mock_client


def _make_openrouter_mock(parsed_obj):
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse.return_value.choices[0].message.parsed = parsed_obj
    return mock_client


def _make_gemini_mock(parsed_obj):
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value.text = parsed_obj.model_dump_json()
    return mock_client


class TestParseMistral:
    def test_returns_parsed_object(self):
        expected = _make_feedback(mark=0.6)
        with patch("llm_calls.mistral_client", _make_mistral_mock(expected)):
            result = llm_calls.parse_mistral("mistral-small", "user prompt", Feedback)
        assert result is expected

    def test_user_prompt_in_messages(self):
        mock_client = _make_mistral_mock(_make_feedback())
        with patch("llm_calls.mistral_client", mock_client):
            llm_calls.parse_mistral("model", "my user prompt", Feedback)
        messages = mock_client.chat.parse.call_args.kwargs["messages"]
        assert any(m["role"] == "user" and "my user prompt" in m["content"] for m in messages)

    def test_system_prompt_added_when_given(self):
        mock_client = _make_mistral_mock(_make_feedback())
        with patch("llm_calls.mistral_client", mock_client):
            llm_calls.parse_mistral("model", "user", Feedback, system_prompt="You are HR")
        messages = mock_client.chat.parse.call_args.kwargs["messages"]
        assert any(m["role"] == "system" and "You are HR" in m["content"] for m in messages)

    def test_no_system_message_when_not_given(self):
        mock_client = _make_mistral_mock(_make_feedback())
        with patch("llm_calls.mistral_client", mock_client):
            llm_calls.parse_mistral("model", "user", Feedback)
        messages = mock_client.chat.parse.call_args.kwargs["messages"]
        assert not any(m["role"] == "system" for m in messages)

    def test_response_format_passed_to_client(self):
        mock_client = _make_mistral_mock(_make_feedback())
        with patch("llm_calls.mistral_client", mock_client):
            llm_calls.parse_mistral("model", "user", Feedback)
        assert mock_client.chat.parse.call_args.kwargs["response_format"] is Feedback

    def test_model_name_passed_to_client(self):
        mock_client = _make_mistral_mock(_make_feedback())
        with patch("llm_calls.mistral_client", mock_client):
            llm_calls.parse_mistral("mistral-large", "user", Feedback)
        assert mock_client.chat.parse.call_args.kwargs["model"] == "mistral-large"


class TestParseOpenrouter:
    def test_returns_parsed_object(self):
        expected = _make_feedback(mark=0.4)
        with patch("llm_calls.openrouter_client", _make_openrouter_mock(expected), create=True):
            result = llm_calls.parse_openrouter("deepseek/v3", "user prompt", Feedback)
        assert result is expected

    def test_user_prompt_in_messages(self):
        mock_client = _make_openrouter_mock(_make_feedback())
        with patch("llm_calls.openrouter_client", mock_client, create=True):
            llm_calls.parse_openrouter("model", "my user prompt", Feedback)
        messages = mock_client.beta.chat.completions.parse.call_args.kwargs["messages"]
        assert any(m["role"] == "user" and "my user prompt" in m["content"] for m in messages)

    def test_system_prompt_added_when_given(self):
        mock_client = _make_openrouter_mock(_make_feedback())
        with patch("llm_calls.openrouter_client", mock_client, create=True):
            llm_calls.parse_openrouter("model", "user", Feedback, system_prompt="You are HR")
        messages = mock_client.beta.chat.completions.parse.call_args.kwargs["messages"]
        assert any(m["role"] == "system" and "You are HR" in m["content"] for m in messages)

    def test_no_system_message_when_not_given(self):
        mock_client = _make_openrouter_mock(_make_feedback())
        with patch("llm_calls.openrouter_client", mock_client, create=True):
            llm_calls.parse_openrouter("model", "user", Feedback)
        messages = mock_client.beta.chat.completions.parse.call_args.kwargs["messages"]
        assert not any(m["role"] == "system" for m in messages)

    def test_model_name_passed_to_client(self):
        mock_client = _make_openrouter_mock(_make_feedback())
        with patch("llm_calls.openrouter_client", mock_client, create=True):
            llm_calls.parse_openrouter("deepseek/v3-flash", "user", Feedback)
        assert mock_client.beta.chat.completions.parse.call_args.kwargs["model"] == "deepseek/v3-flash"


class TestParseGemini:
    def test_returns_parsed_object(self):
        expected = _make_feedback(mark=0.3)
        with patch("llm_calls.gemini_client", _make_gemini_mock(expected), create=True):
            result = llm_calls.parse_gemini("gemini-flash", "user prompt", Feedback)
        assert result == expected

    def test_user_prompt_passed_as_contents(self):
        mock_client = _make_gemini_mock(_make_feedback())
        with patch("llm_calls.gemini_client", mock_client, create=True):
            llm_calls.parse_gemini("model", "my user prompt", Feedback)
        assert mock_client.models.generate_content.call_args.kwargs["contents"] == "my user prompt"

    def test_model_name_passed_to_client(self):
        mock_client = _make_gemini_mock(_make_feedback())
        with patch("llm_calls.gemini_client", mock_client, create=True):
            llm_calls.parse_gemini("gemini-2.0-flash", "user", Feedback)
        assert mock_client.models.generate_content.call_args.kwargs["model"] == "gemini-2.0-flash"

    def test_system_instruction_passed_in_config(self):
        mock_client = _make_gemini_mock(_make_feedback())
        with patch("llm_calls.gemini_client", mock_client, create=True):
            llm_calls.parse_gemini("model", "user", Feedback, system_prompt="You are HR")
        config = mock_client.models.generate_content.call_args.kwargs["config"]
        assert config.system_instruction == "You are HR"

    def test_no_system_instruction_when_not_given(self):
        mock_client = _make_gemini_mock(_make_feedback())
        with patch("llm_calls.gemini_client", mock_client, create=True):
            llm_calls.parse_gemini("model", "user", Feedback)
        config = mock_client.models.generate_content.call_args.kwargs["config"]
        assert config.system_instruction is None

    def test_response_schema_passed_in_config(self):
        mock_client = _make_gemini_mock(_make_feedback())
        with patch("llm_calls.gemini_client", mock_client, create=True):
            llm_calls.parse_gemini("model", "user", Feedback)
        config = mock_client.models.generate_content.call_args.kwargs["config"]
        assert config.response_schema is Feedback

    def test_invalid_json_response_raises(self):
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value.text = "not valid json {"
        with patch("llm_calls.gemini_client", mock_client, create=True):
            with pytest.raises(Exception):
                llm_calls.parse_gemini("model", "user", Feedback)


class TestParseLlmDispatch:
    def test_mistral_provider_calls_parse_mistral(self, monkeypatch):
        monkeypatch.setattr(llm_calls, "llm_provider", "mistral")
        monkeypatch.setattr(llm_calls, "llm_model", "mistral-small")
        with patch("llm_calls.parse_mistral", return_value=_make_feedback()) as mock:
            llm_calls.parse_llm("prompt", Feedback)
        mock.assert_called_once_with("mistral-small", "prompt", Feedback, None, 2000)

    def test_openrouter_provider_calls_parse_openrouter(self, monkeypatch):
        monkeypatch.setattr(llm_calls, "llm_provider", "openrouter")
        monkeypatch.setattr(llm_calls, "llm_model", "deepseek/v3")
        with patch("llm_calls.parse_openrouter", return_value=_make_feedback()) as mock:
            llm_calls.parse_llm("prompt", Feedback)
        mock.assert_called_once_with("deepseek/v3", "prompt", Feedback, None, 2000)

    def test_gemini_provider_calls_parse_gemini(self, monkeypatch):
        monkeypatch.setattr(llm_calls, "llm_provider", "gemini")
        monkeypatch.setattr(llm_calls, "llm_model", "gemini-flash")
        with patch("llm_calls.parse_gemini", return_value=_make_feedback()) as mock:
            llm_calls.parse_llm("prompt", Feedback)
        mock.assert_called_once_with("gemini-flash", "prompt", Feedback, None, 2000)

    def test_system_prompt_forwarded(self, monkeypatch):
        monkeypatch.setattr(llm_calls, "llm_provider", "mistral")
        monkeypatch.setattr(llm_calls, "llm_model", "mistral-small")
        with patch("llm_calls.parse_mistral", return_value=_make_feedback()) as mock:
            llm_calls.parse_llm("prompt", Feedback, system_prompt="sys")
        mock.assert_called_once_with("mistral-small", "prompt", Feedback, "sys", 2000)

    def test_unknown_provider_raises(self, monkeypatch):
        monkeypatch.setattr(llm_calls, "llm_provider", "unknown_provider")
        with pytest.raises(ValueError, match="Unknown LLM_PROVIDER"):
            llm_calls.parse_llm("prompt", Feedback)
