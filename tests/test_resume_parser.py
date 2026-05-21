import re
import pytest
from unittest.mock import patch, MagicMock

from resume_parser import _NOISE_PATTERNS


# --- Noise pattern tests (pure regex, no I/O) ---

def _matches_any(text: str) -> bool:
    return any(re.search(p, text, flags=re.IGNORECASE) for p in _NOISE_PATTERNS)


class TestNoisePatterns:
    def test_email_is_noise(self):
        assert _matches_any("john.doe@example.com")

    def test_phone_is_noise(self):
        assert _matches_any("+1 (555) 123-4567")

    def test_url_is_noise(self):
        assert _matches_any("https://github.com/johndoe")

    def test_www_url_is_noise(self):
        assert _matches_any("www.linkedin.com/in/johndoe")

    def test_linkedin_is_noise(self):
        assert _matches_any("linkedin.com/in/johndoe")

    def test_github_is_noise(self):
        assert _matches_any("github.com/johndoe/repo")

    def test_date_is_noise(self):
        assert _matches_any("12/05/2024")

    def test_regular_sentence_is_not_noise(self):
        assert not _matches_any("Developed a distributed caching layer in Python")

    def test_company_name_is_not_noise(self):
        assert not _matches_any("Google Inc.")

    def test_skill_list_is_not_noise(self):
        assert not _matches_any("Python, Java, Go, Kubernetes")


# --- parse_resume_pdf integration (PDF reading + LLM mocked) ---

class TestParseResumePdf:
    def _make_mock_doc(self, pages_text: list[str]):
        """Build a minimal pymupdf.Document mock."""
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = len(pages_text)
        mock_doc.__iter__.return_value = iter([
            MagicMock(**{"get_text.return_value": t}) for t in pages_text
        ])
        return mock_doc

    def test_too_many_pages_raises(self):
        with patch("resume_parser.pymupdf.open") as mock_open:
            mock_doc = MagicMock()
            mock_doc.__len__.return_value = 11
            mock_open.return_value = mock_doc
            with pytest.raises(Exception, match="Too long"):
                from resume_parser import parse_resume_pdf
                parse_resume_pdf("fake.pdf")

    def test_non_resume_raises(self):
        with patch("resume_parser.pymupdf.open") as mock_open, \
             patch("resume_parser.check_resume", return_value=False):
            mock_doc = self._make_mock_doc(["Some random text document"])
            mock_open.return_value = mock_doc
            from resume_parser import parse_resume_pdf
            with pytest.raises(Exception, match="Not an IT resume"):
                parse_resume_pdf("fake.pdf")

    def test_valid_resume_returns_string(self):
        resume_text = (
            "Software Engineer\n"
            "Skills: Python, Docker, Kubernetes\n"
            "Experience: 5 years at BigCorp building distributed systems\n"
            "Education: BSc Computer Science\n"
        )
        with patch("resume_parser.pymupdf.open") as mock_open, \
             patch("resume_parser.check_resume", return_value=True):
            mock_doc = self._make_mock_doc([resume_text])
            mock_open.return_value = mock_doc
            from resume_parser import parse_resume_pdf
            result = parse_resume_pdf("fake.pdf")
            assert isinstance(result, str)
            assert len(result) > 0

    def test_noise_removed_from_output(self):
        resume_text = (
            "John Doe\n"
            "john@example.com\n"
            "+1-555-000-0000\n"
            "Skills: Python, Docker, Kubernetes\n"
            "Experience: Built microservices at a fintech company for 3 years\n"
            "Education: BSc Computer Science, MIT\n"
        )
        with patch("resume_parser.pymupdf.open") as mock_open, \
             patch("resume_parser.check_resume", return_value=True):
            mock_doc = self._make_mock_doc([resume_text])
            mock_open.return_value = mock_doc
            from resume_parser import parse_resume_pdf
            result = parse_resume_pdf("fake.pdf")
            assert "john@example.com" not in result
            assert "+1-555-000-0000" not in result

    def test_skills_section_preserved(self):
        resume_text = (
            "Skills: Python, Docker, Kubernetes, PostgreSQL\n"
            "Experience: Led backend team of 5 engineers building a payment platform\n"
            "Education: MSc Software Engineering\n"
        )
        with patch("resume_parser.pymupdf.open") as mock_open, \
             patch("resume_parser.check_resume", return_value=True):
            mock_doc = self._make_mock_doc([resume_text])
            mock_open.return_value = mock_doc
            from resume_parser import parse_resume_pdf
            result = parse_resume_pdf("fake.pdf")
            assert "Python" in result
