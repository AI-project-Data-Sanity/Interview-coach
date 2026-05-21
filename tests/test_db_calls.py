import json
import pytest
import db_calls


class TestGetAllQuestions:
    def test_returns_list(self, seeded_db):
        result = db_calls.get_all_questions()
        assert isinstance(result, list)

    def test_each_item_has_required_keys(self, seeded_db):
        result = db_calls.get_all_questions()
        for item in result:
            assert "question_id" in item
            assert "question" in item

    def test_returns_inserted_question(self, seeded_db):
        result = db_calls.get_all_questions()
        assert any(q["question_id"] == 1 for q in result)

    def test_empty_db_returns_empty_list(self, db_path):
        assert db_calls.get_all_questions() == []


class TestGetQuestionById:
    def test_returns_question_text(self, seeded_db):
        text = db_calls.get_question_by_id(1)
        assert "challenge" in text.lower()

    def test_raises_on_missing_id(self, seeded_db):
        with pytest.raises(Exception):
            db_calls.get_question_by_id(9999)


class TestGetAnswersByQuestionId:
    def test_returns_three_answers(self, seeded_db):
        answers = db_calls.get_answers_by_question_id(1)
        assert len(answers) == 3

    def test_answer_dict_keys(self, seeded_db):
        answers = db_calls.get_answers_by_question_id(1)
        for a in answers:
            assert "answer_id" in a
            assert "answer" in a
            assert "mark" in a
            assert "reason" in a

    def test_marks_are_valid(self, seeded_db):
        answers = db_calls.get_answers_by_question_id(1)
        for a in answers:
            assert a["mark"] in ("bad", "middle", "good")

    def test_no_answers_returns_empty(self, db_path):
        import sqlite3
        conn = sqlite3.connect(db_path)
        conn.execute("INSERT INTO questions VALUES (7, 'New question')")
        conn.commit()
        conn.close()
        assert db_calls.get_answers_by_question_id(7) == []


class TestAddUser:
    def test_new_user_is_inserted(self, db_path):
        db_calls.add_user(101, "@bob")
        import sqlite3
        conn = sqlite3.connect(db_path)
        row = conn.execute("SELECT user_id, user_name FROM users WHERE user_id=101").fetchone()
        conn.close()
        assert row is not None
        assert row[1] == "@bob"

    def test_existing_user_username_updated(self, seeded_db):
        db_calls.add_user(42, "@alice_new")
        import sqlite3
        conn = sqlite3.connect(seeded_db)
        row = conn.execute("SELECT user_name FROM users WHERE user_id=42").fetchone()
        conn.close()
        assert row[0] == "@alice_new"

    def test_existing_user_same_name_no_error(self, seeded_db):
        db_calls.add_user(42, "alice")  # same name, should not raise


class TestGetResumeDbErrors:
    def test_raises_for_nonexistent_user(self, db_path):
        with pytest.raises(Exception):
            db_calls.get_resume_db(9999)


class TestGetUserAnsweredErrors:
    def test_raises_for_nonexistent_user(self, db_path):
        with pytest.raises(Exception):
            db_calls.get_user_answered(9999)


class TestSaveAndGetResume:
    def test_save_and_retrieve(self, seeded_db):
        db_calls.save_resume_db(42, "Python developer with 5 years experience")
        result = db_calls.get_resume_db(42)
        assert result == "Python developer with 5 years experience"

    def test_overwrite_existing_resume(self, seeded_db):
        db_calls.save_resume_db(42, "First resume")
        db_calls.save_resume_db(42, "Updated resume")
        result = db_calls.get_resume_db(42)
        assert result == "Updated resume"


class TestUserAnswered:
    def test_initial_asked_questions_is_empty(self, seeded_db):
        result = db_calls.get_user_answered(42)
        assert result == []

    def test_save_and_retrieve_answered(self, seeded_db):
        db_calls.save_user_answered(42, 1)
        result = db_calls.get_user_answered(42)
        assert 1 in result

    def test_duplicates_are_deduplicated(self, seeded_db):
        db_calls.save_user_answered(42, 1)
        db_calls.save_user_answered(42, 1)
        result = db_calls.get_user_answered(42)
        assert result.count(1) == 1

    def test_multiple_questions_saved(self, seeded_db):
        db_calls.save_user_answered(42, 1)
        db_calls.save_user_answered(42, 2)
        result = db_calls.get_user_answered(42)
        assert set(result) == {1, 2}
