"""
Tests for bot.py handler functions and ConversationHandler routing config.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram.ext import MessageHandler

import messages
from telegram.ext import ConversationHandler

from bot import (
    AFTER_START, WAITING_FOR_PDF, AFTER_RESUME, IN_INTERVIEW,
    start,
    handle_unexpected_in_pdf_state,
    handle_unexpected_in_interview,
    handle_document,
    handle_answer,
    error_handler,
    build_conv_handler,
)


def _make_update():
    update = MagicMock()
    update.message.reply_text = AsyncMock()
    return update


def _make_context(question_ids=None, index=0):
    context = MagicMock()
    context.user_data = {}
    if question_ids is not None:
        context.user_data["question_ids"] = question_ids
        context.user_data["current_index"] = index
    return context


def _replied_texts(update):
    return [call.args[0] for call in update.message.reply_text.call_args_list]


def _make_doc_update(mime_type="application/pdf", file_id="abc123"):
    update = _make_update()
    update.message.document.mime_type = mime_type
    update.message.document.file_id = file_id
    update.message.document.get_file = AsyncMock(return_value=AsyncMock())
    update.message.from_user.id = 42
    return update


# --- start ---

class TestStart:
    def _make_start_update(self, user_id=42, username="alice"):
        update = _make_update()
        update.message.from_user.id = user_id
        update.message.from_user.username = username
        return update

    @pytest.mark.asyncio
    async def test_returns_after_start(self):
        update = self._make_start_update()
        with patch("bot.register_user"):
            result = await start(update, _make_context())
        assert result == AFTER_START

    @pytest.mark.asyncio
    async def test_sends_welcome_message(self):
        update = self._make_start_update()
        with patch("bot.register_user"):
            await start(update, _make_context())
        assert _replied_texts(update) == [messages.WELCOME]

    @pytest.mark.asyncio
    async def test_clears_stale_session_data(self):
        """Returning user's old question list must not bleed into the new session."""
        update = self._make_start_update()
        context = _make_context()
        context.user_data["question_ids"] = [1, 2, 3]
        context.user_data["current_index"] = 2
        with patch("bot.register_user"):
            await start(update, context)
        assert context.user_data == {}

    @pytest.mark.asyncio
    async def test_registration_failure_sends_error(self):
        exc = Exception("DB unavailable")
        update = self._make_start_update()
        with patch("bot.register_user", side_effect=exc):
            await start(update, _make_context())
        assert _replied_texts(update) == [f"{messages.REGISTRATION_FAILED}\n{exc}"]

    @pytest.mark.asyncio
    async def test_registration_failure_ends_conversation(self):
        update = self._make_start_update()
        with patch("bot.register_user", side_effect=Exception("DB unavailable")):
            result = await start(update, _make_context())
        assert result == ConversationHandler.END


# --- handle_unexpected_in_pdf_state ---

class TestHandleUnexpectedInPdfState:
    @pytest.mark.asyncio
    async def test_reply_text(self):
        update = _make_update()
        await handle_unexpected_in_pdf_state(update, _make_context())
        assert _replied_texts(update) == [messages.SEND_PDF]

    @pytest.mark.asyncio
    async def test_returns_waiting_for_pdf(self):
        result = await handle_unexpected_in_pdf_state(_make_update(), _make_context())
        assert result == WAITING_FOR_PDF


# --- handle_unexpected_in_interview ---

class TestHandleUnexpectedInInterview:
    @pytest.mark.asyncio
    async def test_reply_text(self):
        update = _make_update()
        await handle_unexpected_in_interview(update, _make_context())
        assert _replied_texts(update) == [messages.REPLY_WITH_TEXT]

    @pytest.mark.asyncio
    async def test_returns_in_interview(self):
        result = await handle_unexpected_in_interview(_make_update(), _make_context())
        assert result == IN_INTERVIEW


# --- handle_document ---

class TestHandleDocument:
    @pytest.mark.asyncio
    async def test_wrong_mime_type_reply(self):
        update = _make_doc_update(mime_type="image/jpeg")
        await handle_document(update, _make_context())
        assert messages.WRONG_FILE_TYPE in _replied_texts(update)

    @pytest.mark.asyncio
    async def test_wrong_mime_type_returns_waiting_for_pdf(self):
        update = _make_doc_update(mime_type="image/jpeg")
        result = await handle_document(update, _make_context())
        assert result == WAITING_FOR_PDF

    @pytest.mark.asyncio
    async def test_save_failure_reply(self):
        exc = Exception("some error")
        update = _make_doc_update()
        with patch("bot.save_resume", side_effect=exc):
            await handle_document(update, _make_context())
        # message 1: RESUME_PROCESSING, message 2: the error
        assert _replied_texts(update)[1] == f"{messages.RESUME_SAVE_FAILED}\n{exc}"

    @pytest.mark.asyncio
    async def test_save_failure_returns_waiting_for_pdf(self):
        update = _make_doc_update()
        with patch("bot.save_resume", side_effect=Exception("disk full")):
            result = await handle_document(update, _make_context())
        assert result == WAITING_FOR_PDF

    @pytest.mark.asyncio
    async def test_success_reply(self):
        update = _make_doc_update()
        with patch("bot.save_resume"):
            await handle_document(update, _make_context())
        assert messages.RESUME_SAVED in _replied_texts(update)

    @pytest.mark.asyncio
    async def test_success_returns_after_resume(self):
        update = _make_doc_update()
        with patch("bot.save_resume"):
            result = await handle_document(update, _make_context())
        assert result == AFTER_RESUME


# --- handle_answer ---

class TestHandleAnswer:
    @pytest.mark.asyncio
    async def test_too_long_answer_reply(self):
        update = _make_update()
        update.message.text = "x" * 3001
        update.message.from_user.id = 42
        await handle_answer(update, _make_context(question_ids=[1, 2, 3]))
        assert messages.ANSWER_TOO_LONG in _replied_texts(update)

    @pytest.mark.asyncio
    async def test_too_long_answer_returns_in_interview(self):
        update = _make_update()
        update.message.text = "x" * 3001
        update.message.from_user.id = 42
        result = await handle_answer(update, _make_context(question_ids=[1, 2, 3]))
        assert result == IN_INTERVIEW

    @pytest.mark.asyncio
    async def test_feedback_failure_reply(self):
        exc = Exception("some error")
        update = _make_update()
        update.message.text = "My answer"
        update.message.from_user.id = 42
        with patch("bot.get_llm_feedback", side_effect=exc):
            await handle_answer(update, _make_context(question_ids=[1, 2, 3]))
        # only one message is sent on failure
        assert _replied_texts(update) == [f"{messages.FEEDBACK_FAILED}\n{exc}"]

    @pytest.mark.asyncio
    async def test_feedback_failure_returns_in_interview(self):
        update = _make_update()
        update.message.text = "My answer"
        update.message.from_user.id = 42
        with patch("bot.get_llm_feedback", side_effect=Exception("LLM timeout")):
            result = await handle_answer(update, _make_context(question_ids=[1, 2, 3]))
        assert result == IN_INTERVIEW

    @pytest.mark.asyncio
    async def test_mid_interview_shows_feedback_then_next_question(self):
        update = _make_update()
        update.message.text = "My answer"
        update.message.from_user.id = 42
        with patch("bot.get_llm_feedback", return_value="Good answer!"), \
             patch("bot.get_question_text_by_id", return_value="Next question text"):
            result = await handle_answer(update, _make_context(question_ids=[1, 2, 3], index=0))
        texts = _replied_texts(update)
        assert any("Good answer!" in t for t in texts)
        assert any("Next question text" in t for t in texts)
        assert result == IN_INTERVIEW

    @pytest.mark.asyncio
    async def test_mid_interview_advances_index(self):
        update = _make_update()
        update.message.text = "My answer"
        update.message.from_user.id = 42
        context = _make_context(question_ids=[1, 2, 3], index=0)
        with patch("bot.get_llm_feedback", return_value="feedback"), \
             patch("bot.get_question_text_by_id", return_value="Q"):
            await handle_answer(update, context)
        assert context.user_data["current_index"] == 1

    @pytest.mark.asyncio
    async def test_last_question_shows_complete_message(self):
        update = _make_update()
        update.message.text = "My final answer"
        update.message.from_user.id = 42
        with patch("bot.get_llm_feedback", return_value="Great!"):
            await handle_answer(update, _make_context(question_ids=[1, 2, 3], index=2))
        assert messages.INTERVIEW_COMPLETE in _replied_texts(update)

    @pytest.mark.asyncio
    async def test_last_question_ends_session(self):
        update = _make_update()
        update.message.text = "My final answer"
        update.message.from_user.id = 42
        with patch("bot.get_llm_feedback", return_value="Great!"):
            await handle_answer(update, _make_context(question_ids=[1, 2, 3], index=2))
        assert messages.SESSION_ENDED in _replied_texts(update)


# --- error_handler ---

class TestErrorHandler:
    @pytest.mark.asyncio
    async def test_logs_the_exception(self):
        exc = Exception("something went wrong")
        context = _make_context()
        context.error = exc
        with patch("bot.logging") as mock_log:
            await error_handler(None, context)
        mock_log.error.assert_called_once_with("Unhandled exception", exc_info=exc)


# --- Routing configuration ---

def _message_handlers_for_state(state_id):
    conv = build_conv_handler()
    return [h for h in conv.states[state_id] if isinstance(h, MessageHandler)]


class TestWaitingForPdfRouting:
    def test_pdf_document_goes_to_handle_document(self):
        handlers = _message_handlers_for_state(WAITING_FOR_PDF)
        assert any(h.callback is handle_document for h in handlers)

    def test_catch_all_goes_to_unexpected_handler(self):
        handlers = _message_handlers_for_state(WAITING_FOR_PDF)
        assert any(h.callback is handle_unexpected_in_pdf_state for h in handlers)

    def test_document_handler_comes_before_catch_all(self):
        callbacks = [h.callback for h in _message_handlers_for_state(WAITING_FOR_PDF)]
        assert callbacks.index(handle_document) < callbacks.index(handle_unexpected_in_pdf_state)

    def test_catch_all_filter_matches_photo(self):
        handlers = _message_handlers_for_state(WAITING_FOR_PDF)
        catch_all = next(h for h in handlers if h.callback is handle_unexpected_in_pdf_state)
        photo_update = MagicMock()
        photo_update.message.photo = [MagicMock()]
        photo_update.message.document = None
        photo_update.message.text = None
        photo_update.message.entities = []
        assert catch_all.filters.check_update(photo_update)


class TestInInterviewRouting:
    def test_text_goes_to_handle_answer(self):
        handlers = _message_handlers_for_state(IN_INTERVIEW)
        assert any(h.callback is handle_answer for h in handlers)

    def test_catch_all_goes_to_unexpected_handler(self):
        handlers = _message_handlers_for_state(IN_INTERVIEW)
        assert any(h.callback is handle_unexpected_in_interview for h in handlers)

    def test_text_handler_comes_before_catch_all(self):
        callbacks = [h.callback for h in _message_handlers_for_state(IN_INTERVIEW)]
        assert callbacks.index(handle_answer) < callbacks.index(handle_unexpected_in_interview)
