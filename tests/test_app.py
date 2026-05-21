import pytest
from unittest.mock import patch, MagicMock

from llm_calls import Feedback


def _make_feedback(**overrides) -> Feedback:
    defaults = dict(
        STAR="STAR usage comment",
        motivation="Motivated",
        proactivity="Proactive",
        adaptability="Adaptable",
        perseverance="Persistent",
        nonconflicteness="Non-conflicting",
        empathy="Empathetic",
        growth="Growth-oriented",
        communication="Clear",
        mark=0.75,
    )
    defaults.update(overrides)
    return Feedback(**defaults)


class TestGetLlmFeedback:
    def _run(self, feedback: Feedback, question_text="Why do you want this job?"):
        with patch("app.save_user_answered"), \
             patch("app.get_question_by_id", return_value=question_text), \
             patch("app.get_answers_by_question_id", return_value=[]), \
             patch("app.response_evaluator", return_value=feedback):
            from app import get_llm_feedback
            return get_llm_feedback(user_id=1, question_id=1, answer="My answer")

    def test_returns_string(self):
        result = self._run(_make_feedback())
        assert isinstance(result, str)

    def test_mark_in_output(self):
        result = self._run(_make_feedback(mark=0.75))
        assert "0.75" in result

    def test_all_dimensions_present(self):
        result = self._run(_make_feedback())
        for label in ("Mark", "STAR", "Motivation", "Proactivity", "Adaptability",
                      "Perseverance", "Nonconflicteness", "Empathy", "Growth", "Communication"):
            assert label in result, f"Missing '{label}' in feedback output"

    def test_feedback_text_included(self):
        fb = _make_feedback(motivation="Extremely passionate about building products")
        result = self._run(fb)
        assert "Extremely passionate about building products" in result

    def test_save_user_answered_called(self):
        with patch("app.save_user_answered") as mock_save, \
             patch("app.get_question_by_id", return_value="Question"), \
             patch("app.get_answers_by_question_id", return_value=[]), \
             patch("app.response_evaluator", return_value=_make_feedback()):
            from app import get_llm_feedback
            get_llm_feedback(user_id=7, question_id=3, answer="Answer")
            mock_save.assert_called_once_with(7, 3)

    def test_zero_mark_output(self):
        result = self._run(_make_feedback(mark=0.0))
        assert "0.0" in result

    def test_full_mark_output(self):
        result = self._run(_make_feedback(mark=1.0))
        assert "1.0" in result


class TestRegisterUser:
    def test_delegates_to_add_user(self):
        with patch("app.add_user") as mock_add:
            from app import register_user
            register_user(99, "@charlie")
            mock_add.assert_called_once_with(99, "@charlie")


class TestSaveResume:
    def test_parses_pdf_and_saves(self):
        with patch("app.parse_resume_pdf", return_value="Parsed resume text") as mock_parse, \
             patch("app.save_resume_db") as mock_save:
            from app import save_resume
            save_resume(user_id=5, pdf_path="path/to/resume.pdf")
            mock_parse.assert_called_once_with("path/to/resume.pdf")
            mock_save.assert_called_once_with(5, "Parsed resume text")


class TestGetQuestionList:
    def test_returns_plan_from_builder(self):
        with patch("app.get_user_answered", return_value=[]), \
             patch("app.get_resume_db", return_value=("resume text",)), \
             patch("app.get_all_questions", return_value=[{"question_id": i} for i in range(10)]), \
             patch("app.question_list_builder", return_value=[1, 4, 7, 2, 5]) as mock_builder:
            from app import get_question_list
            result = get_question_list(user_id=1)
            assert result == [1, 4, 7, 2, 5]
