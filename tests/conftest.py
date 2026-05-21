"""
Set env vars before any project module is imported, so module-level
`os.environ[...]` reads in llm_calls.py, db_calls.py, etc. all succeed.
"""
import os
import sqlite3
import pytest

# Must be set before any project module is imported.
os.environ.setdefault("LLM_PROVIDER", "mistral")
os.environ.setdefault("LLM_MODEL", "mistral-small")
os.environ.setdefault("MISTRAL_KEY", "test-key")
os.environ.setdefault("OPENROUTER_KEY", "test-key")
os.environ.setdefault("GEMINI_API_KEY", "test-key")
os.environ.setdefault("DB_PATH", ":memory:")  # overridden per-test via monkeypatch


def _create_schema(conn: sqlite3.Connection):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            question_id INTEGER PRIMARY KEY,
            question TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS answers (
            answer_id INTEGER PRIMARY KEY,
            question_id INTEGER NOT NULL,
            answer TEXT NOT NULL,
            mark TEXT CHECK(mark IN ('bad', 'middle', 'good')),
            reason TEXT,
            FOREIGN KEY (question_id) REFERENCES questions(question_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            user_name TEXT NOT NULL,
            resume_text TEXT,
            asked_questions TEXT,
            dialog_text TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS answers_golden (
            golden_answer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            golden_answer TEXT NOT NULL,
            question_id INTEGER NOT NULL,
            mark TEXT CHECK(mark IN ('bad', 'good')),
            split TEXT CHECK(split IN ('test', 'val')),
            FOREIGN KEY (question_id) REFERENCES questions(question_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS resumes_golden (
            resume_id INTEGER PRIMARY KEY,
            filename TEXT NOT NULL,
            is_it_resume BOOLEAN NOT NULL,
            split TEXT CHECK(split IN ('test', 'val')),
            questions_plan TEXT
        )
    """)
    conn.commit()


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    """Create a fresh SQLite DB file and redirect db_calls.db_path to it."""
    path = str(tmp_path / "test.db")
    conn = sqlite3.connect(path)
    _create_schema(conn)
    conn.close()

    import db_calls
    monkeypatch.setattr(db_calls, "db_path", path)
    return path


@pytest.fixture
def seeded_db(db_path):
    """db_path with one question, three answers, and one user pre-inserted."""
    conn = sqlite3.connect(db_path)
    conn.execute("INSERT INTO questions VALUES (1, 'Tell me about a challenge you overcame.')")
    conn.execute("INSERT INTO answers VALUES (1, 1, 'I faced X and did Y.', 'good', 'Shows perseverance')")
    conn.execute("INSERT INTO answers VALUES (2, 1, 'I gave up.',           'bad',  'No persistence')")
    conn.execute("INSERT INTO answers VALUES (3, 1, 'It was okay.',         'middle','Adequate')")
    conn.execute(
        "INSERT INTO users VALUES (42, 'alice', 'resume text', '[]', '')"
    )
    conn.commit()
    conn.close()
    return db_path
