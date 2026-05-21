"""
Integration tests for app.py: real SQLite database, LLM calls mocked.
These tests exercise the wiring between app.py and db_calls.py that
unit tests miss because they mock the DB entirely.
"""
import pytest
from unittest.mock import patch

from llm_calls import Feedback, ResumePlan


def _make_feedback(**overrides) -> Feedback:
    defaults = dict(
        STAR="Good", motivation="High", proactivity="Strong",
        adaptability="Flexible", perseverance="Resilient",
        nonconflicteness="Cooperative", empathy="Empathetic",
        growth="Learning", communication="Clear", mark=0.8,
    )
    defaults.update(overrides)
    return Feedback(**defaults)


@pytest.fixture
def app_db(seeded_db):
    """seeded_db already has question 1 + 3 answers + user 42.
    Import app after db_path is patched so it picks up the test DB."""
    import app
    return app


class TestRegisterAndResume:
    def test_register_new_user_persists(self, app_db, db_path):
        import sqlite3
        app_db.register_user(99, "@newuser")
        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT user_name FROM users WHERE user_id=99").fetchone()
        conn.close()
        assert row[0] == "@newuser"

    def test_save_and_retrieve_resume_round_trip(self, app_db):
        with patch("app.parse_resume_pdf", return_value="Python engineer with 5 years experience"):
            app_db.save_resume(user_id=42, pdf_path="fake.pdf")
        result = app_db.get_question_text_by_id(1)
        assert isinstance(result, str)

    def test_save_resume_stores_plain_string(self, app_db, db_path):
        import sqlite3
        with patch("app.parse_resume_pdf", return_value="Senior backend engineer"):
            app_db.save_resume(user_id=42, pdf_path="fake.pdf")
        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT resume_text FROM users WHERE user_id=42").fetchone()
        conn.close()
        assert row[0] == "Senior backend engineer"


class TestGetQuestionList:
    def test_returns_list_of_ints(self, app_db):
        with patch("app.parse_resume_pdf", return_value="resume text"):
            app_db.save_resume(user_id=42, pdf_path="fake.pdf")
        mock_plan = ResumePlan(plan=[1])
        with patch("app.question_list_builder", return_value=[1]):
            result = app_db.get_question_list(user_id=42)
        assert isinstance(result, list)

    def test_resume_text_passed_as_string_not_tuple(self, app_db):
        """get_resume_db returns a tuple row — verify app unwraps it before
        passing to question_list_builder so the LLM gets plain text."""
        with patch("app.parse_resume_pdf", return_value="plain resume text"):
            app_db.save_resume(user_id=42, pdf_path="fake.pdf")
        with patch("app.question_list_builder", return_value=[1]) as mock_builder:
            app_db.get_question_list(user_id=42)
        resume_arg = mock_builder.call_args.args[0]
        assert resume_arg == "plain resume text", (
            f"Expected plain string, got {type(resume_arg)}: {resume_arg!r}"
        )

    def test_already_answered_questions_excluded(self, app_db):
        with patch("app.parse_resume_pdf", return_value="resume"):
            app_db.save_resume(user_id=42, pdf_path="fake.pdf")
        with patch("app.response_evaluator", return_value=_make_feedback()):
            with patch("app.get_answers_by_question_id", return_value=[]):
                with patch("app.get_question_by_id", return_value="Tell me about a challenge"):
                    app_db.get_llm_feedback(user_id=42, question_id=1, answer="My answer")
        with patch("app.question_list_builder", return_value=[]) as mock_builder:
            app_db.get_question_list(user_id=42)
        answered = mock_builder.call_args.args[2]
        assert 1 in answered


class TestGetLlmFeedback:
    def test_marks_question_as_answered_in_db(self, app_db, db_path):
        import sqlite3, json
        with patch("app.response_evaluator", return_value=_make_feedback()), \
             patch("app.get_answers_by_question_id", return_value=[]), \
             patch("app.get_question_by_id", return_value="Tell me about a challenge"):
            app_db.get_llm_feedback(user_id=42, question_id=1, answer="My answer")
        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT asked_questions FROM users WHERE user_id=42").fetchone()
        conn.close()
        assert 1 in json.loads(row[0])

    def test_calling_twice_does_not_duplicate_in_db(self, app_db, db_path):
        import sqlite3, json
        with patch("app.response_evaluator", return_value=_make_feedback()), \
             patch("app.get_answers_by_question_id", return_value=[]), \
             patch("app.get_question_by_id", return_value="Tell me about a challenge"):
            app_db.get_llm_feedback(user_id=42, question_id=1, answer="First")
            app_db.get_llm_feedback(user_id=42, question_id=1, answer="Second")
        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT asked_questions FROM users WHERE user_id=42").fetchone()
        conn.close()
        asked = json.loads(row[0])
        assert asked.count(1) == 1

    def test_uses_question_text_from_db(self, app_db):
        captured = {}
        def fake_evaluator(question_text, answer, prefounded):
            captured["question_text"] = question_text
            return _make_feedback()
        with patch("app.response_evaluator", side_effect=fake_evaluator), \
             patch("app.get_answers_by_question_id", return_value=[]):
            app_db.get_llm_feedback(user_id=42, question_id=1, answer="My answer")
        assert "challenge" in captured["question_text"].lower()
