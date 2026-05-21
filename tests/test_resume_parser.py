import pytest
from unittest.mock import patch, MagicMock

import llm_resume_parser
from llm_resume_parser import check_resume, parse_resume_pdf, ResumeChecker, Resume


class TestCheckResume:
    def _capture(self, text="some resume text"):
        mock_result = ResumeChecker(is_it_resume=True)
        with patch("llm_resume_parser.parse_llm", return_value=mock_result) as mock:
            result = check_resume(text)
            return result, mock.call_args

    def test_returns_true_for_it_resume(self):
        result, _ = self._capture()
        assert result is True

    def test_returns_false_for_non_it_resume(self):
        mock_result = ResumeChecker(is_it_resume=False)
        with patch("llm_resume_parser.parse_llm", return_value=mock_result):
            result = check_resume("Annual financial report Q3 2024")
        assert result is False

    def test_raw_text_in_user_prompt(self):
        _, call_args = self._capture(text="UniqueResumeTextXYZ")
        user_prompt = call_args.args[2]
        assert "UniqueResumeTextXYZ" in user_prompt

    def test_response_format_is_resume_checker(self):
        _, call_args = self._capture()
        assert call_args.args[3] is ResumeChecker


class TestParseResumePdf:
    def _make_mock_doc(self, pages_text: list[str]):
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = len(pages_text)
        mock_doc.__iter__.return_value = iter([
            MagicMock(**{"get_text.return_value": t}) for t in pages_text
        ])
        return mock_doc

    def test_too_many_pages_raises(self):
        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 11
        with patch("llm_resume_parser.pymupdf.open", return_value=mock_doc):
            with pytest.raises(Exception, match="Too long"):
                parse_resume_pdf("fake.pdf")

    def test_non_resume_raises(self):
        mock_doc = self._make_mock_doc(["Some random text"])
        with patch("llm_resume_parser.pymupdf.open", return_value=mock_doc), \
             patch("llm_resume_parser.check_resume", return_value=False):
            with pytest.raises(Exception, match="Not an IT resume"):
                parse_resume_pdf("fake.pdf")

    def test_returns_cleared_text(self):
        mock_doc = self._make_mock_doc(["Raw resume content"])
        mock_resume = Resume(cleared_text="Cleaned and structured resume")
        with patch("llm_resume_parser.pymupdf.open", return_value=mock_doc), \
             patch("llm_resume_parser.check_resume", return_value=True), \
             patch("llm_resume_parser.parse_llm", return_value=mock_resume), \
             patch("llm_resume_parser.time.sleep"):
            result = parse_resume_pdf("fake.pdf")
        assert result == "Cleaned and structured resume"

    def test_raw_text_passed_to_check_resume(self):
        mock_doc = self._make_mock_doc(["UniqueCheckTextDEF456"])
        mock_resume = Resume(cleared_text="cleaned")
        with patch("llm_resume_parser.pymupdf.open", return_value=mock_doc), \
             patch("llm_resume_parser.check_resume", return_value=True) as mock_check, \
             patch("llm_resume_parser.parse_llm", return_value=mock_resume), \
             patch("llm_resume_parser.time.sleep"):
            parse_resume_pdf("fake.pdf")
        assert "UniqueCheckTextDEF456" in mock_check.call_args.args[0]

    def test_multipage_text_joined_with_newline(self):
        mock_doc = self._make_mock_doc(["Page one text", "Page two text"])
        mock_resume = Resume(cleared_text="cleaned")
        with patch("llm_resume_parser.pymupdf.open", return_value=mock_doc), \
             patch("llm_resume_parser.check_resume", return_value=True) as mock_check, \
             patch("llm_resume_parser.parse_llm", return_value=mock_resume), \
             patch("llm_resume_parser.time.sleep"):
            parse_resume_pdf("fake.pdf")
        passed_text = mock_check.call_args.args[0]
        assert "Page one text" in passed_text
        assert "Page two text" in passed_text
        assert "\n" in passed_text

    def test_raw_text_in_extraction_prompt(self):
        mock_doc = self._make_mock_doc(["UniqueRawTextABC123"])
        mock_resume = Resume(cleared_text="cleaned")
        with patch("llm_resume_parser.pymupdf.open", return_value=mock_doc), \
             patch("llm_resume_parser.check_resume", return_value=True), \
             patch("llm_resume_parser.parse_llm", return_value=mock_resume) as mock_parse, \
             patch("llm_resume_parser.time.sleep"):
            parse_resume_pdf("fake.pdf")
        user_prompt = mock_parse.call_args.args[2]
        assert "UniqueRawTextABC123" in user_prompt

    def test_response_format_is_resume(self):
        mock_doc = self._make_mock_doc(["Some resume text"])
        mock_resume = Resume(cleared_text="cleaned")
        with patch("llm_resume_parser.pymupdf.open", return_value=mock_doc), \
             patch("llm_resume_parser.check_resume", return_value=True), \
             patch("llm_resume_parser.parse_llm", return_value=mock_resume) as mock_parse, \
             patch("llm_resume_parser.time.sleep"):
            parse_resume_pdf("fake.pdf")
        assert mock_parse.call_args.args[3] is Resume
