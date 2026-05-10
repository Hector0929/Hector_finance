"""
Unit tests for src/notes/notion.py — M7 個人筆記（Notion 整合）

TDD Red → Green order:
  1. TestFormatNoteDisplay   (pure function, no I/O)
  2. TestCreateNote
  3. TestGetNotes
  4. TestDeleteNote
"""

from datetime import date
from unittest.mock import patch, MagicMock

import pytest

from src.notes.notion import (
    create_note,
    delete_note,
    format_note_display,
    get_notes,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_notion_page(
    page_id: str = "page-abc-123",
    stock_id: str = "2330",
    note_type: str = "買入",
    note_date: str = "2026-05-02",
    price: float = 850.0,
    shares: int = 1,
    content: str = "布林通道突破",
) -> dict:
    """Return a minimal Notion page object that matches the property schema."""
    return {
        "id": page_id,
        "properties": {
            "stock_id": {
                "rich_text": [{"plain_text": stock_id}]
            },
            "note_type": {
                "select": {"name": note_type}
            },
            "date": {
                "date": {"start": note_date}
            },
            "price": {
                "number": price
            },
            "shares": {
                "number": shares
            },
            "content": {
                "rich_text": [{"plain_text": content}]
            },
        },
    }


# ---------------------------------------------------------------------------
# TestFormatNoteDisplay
# ---------------------------------------------------------------------------

class TestFormatNoteDisplay:
    def test_format_buy_note(self):
        note = {
            "page_id": "abc",
            "stock_id": "2330",
            "note_type": "買入",
            "date": "2026-05-02",
            "price": 850.0,
            "shares": 1,
            "content": "布林通道突破",
        }
        result = format_note_display(note)
        assert "2026-05-02" in result
        assert "買入" in result
        assert "2330" in result
        assert "850" in result
        assert "布林通道突破" in result

    def test_format_sell_note(self):
        note = {
            "page_id": "xyz",
            "stock_id": "0050",
            "note_type": "賣出",
            "date": "2026-04-15",
            "price": 200.5,
            "shares": 2,
            "content": "停利出場",
        }
        result = format_note_display(note)
        assert "賣出" in result
        assert "0050" in result
        assert "200" in result
        assert "停利出場" in result

    def test_format_no_content(self):
        note = {
            "page_id": "abc",
            "stock_id": "2330",
            "note_type": "觀察",
            "date": "2026-05-02",
            "price": 800.0,
            "shares": 0,
            "content": "",
        }
        result = format_note_display(note)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_format_returns_string(self):
        note = {
            "page_id": "id1",
            "stock_id": "3008",
            "note_type": "其他",
            "date": "2026-01-01",
            "price": 0.0,
            "shares": 0,
            "content": "測試備註",
        }
        result = format_note_display(note)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# TestCreateNote
# ---------------------------------------------------------------------------

class TestCreateNote:
    @patch("src.notes.notion.Client")
    def test_success_returns_page_id(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.pages.create.return_value = {"id": "new-page-001"}

        result = create_note(
            stock_id="2330",
            note_type="買入",
            price=850.0,
            shares=1,
            content="布林通道突破",
            date="2026-05-02",
        )

        assert result["success"] is True
        assert result["page_id"] == "new-page-001"
        assert "message" in result
        mock_client.pages.create.assert_called_once()

    @patch("src.notes.notion.Client")
    def test_api_failure_returns_error_dict(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.pages.create.side_effect = Exception("Notion API error")

        result = create_note(
            stock_id="2330",
            note_type="買入",
            price=850.0,
            shares=1,
            content="test",
        )

        assert result["success"] is False
        assert result["page_id"] == ""
        assert "message" in result
        # Must NOT raise
        assert isinstance(result, dict)

    @patch("src.notes.notion.Client")
    def test_date_defaults_to_today(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.pages.create.return_value = {"id": "page-today"}

        result = create_note(
            stock_id="2330",
            note_type="觀察",
            price=800.0,
            shares=0,
            content="no date passed",
            # date intentionally omitted
        )

        assert result["success"] is True
        # Verify that the properties sent to Notion contain today's date
        call_kwargs = mock_client.pages.create.call_args[1]
        props = call_kwargs["properties"]
        today_str = date.today().isoformat()
        assert props["date"]["date"]["start"] == today_str

    @patch("src.notes.notion.Client")
    def test_create_note_passes_correct_stock_id(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.pages.create.return_value = {"id": "page-xyz"}

        create_note(
            stock_id="0050",
            note_type="賣出",
            price=200.0,
            shares=3,
            content="部分獲利",
            date="2026-05-01",
        )

        call_kwargs = mock_client.pages.create.call_args[1]
        props = call_kwargs["properties"]
        # stock_id should appear as rich_text
        rich_texts = props["stock_id"]["rich_text"]
        assert any("0050" in rt["text"]["content"] for rt in rich_texts)

    @patch("src.notes.notion.Client")
    def test_create_note_sets_parent_database(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.pages.create.return_value = {"id": "page-db-check"}

        create_note(
            stock_id="2412",
            note_type="買入",
            price=100.0,
            shares=1,
            content="",
            date="2026-05-02",
        )

        call_kwargs = mock_client.pages.create.call_args[1]
        assert "parent" in call_kwargs
        assert "database_id" in call_kwargs["parent"]


# ---------------------------------------------------------------------------
# TestGetNotes
# ---------------------------------------------------------------------------

class TestGetNotes:
    @patch("src.notes.notion.Client")
    def test_returns_list_of_dicts(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.databases.query.return_value = {
            "results": [_make_notion_page()]
        }

        results = get_notes("2330")

        assert isinstance(results, list)
        assert len(results) == 1
        note = results[0]
        assert note["page_id"] == "page-abc-123"
        assert note["stock_id"] == "2330"
        assert note["note_type"] == "買入"
        assert note["date"] == "2026-05-02"
        assert note["price"] == 850.0
        assert note["shares"] == 1
        assert note["content"] == "布林通道突破"

    @patch("src.notes.notion.Client")
    def test_api_failure_returns_empty_list(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.databases.query.side_effect = Exception("connection error")

        results = get_notes("2330")

        assert results == []
        # Must NOT raise

    @patch("src.notes.notion.Client")
    def test_empty_database_returns_empty_list(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.databases.query.return_value = {"results": []}

        results = get_notes("2330")

        assert results == []

    @patch("src.notes.notion.Client")
    def test_filters_by_stock_id(self, mock_client_cls):
        """Verify that query is called with a filter for the given stock_id."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.databases.query.return_value = {"results": []}

        get_notes("9999")

        call_kwargs = mock_client.databases.query.call_args[1]
        # Should pass a filter so Notion returns only matching pages
        assert "filter" in call_kwargs
        filter_obj = call_kwargs["filter"]
        # filter must reference "stock_id" and value "9999"
        assert "9999" in str(filter_obj)

    @patch("src.notes.notion.Client")
    def test_multiple_results_parsed_correctly(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.databases.query.return_value = {
            "results": [
                _make_notion_page(page_id="p1", stock_id="2330", price=850.0),
                _make_notion_page(page_id="p2", stock_id="2330", price=900.0),
            ]
        }

        results = get_notes("2330")

        assert len(results) == 2
        page_ids = {r["page_id"] for r in results}
        assert page_ids == {"p1", "p2"}


# ---------------------------------------------------------------------------
# TestDeleteNote
# ---------------------------------------------------------------------------

class TestDeleteNote:
    @patch("src.notes.notion.Client")
    def test_success(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.pages.update.return_value = {"id": "page-del-001"}

        result = delete_note("page-del-001")

        assert result["success"] is True
        assert "message" in result
        mock_client.pages.update.assert_called_once_with(
            page_id="page-del-001", archived=True
        )

    @patch("src.notes.notion.Client")
    def test_failure_returns_error_dict(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.pages.update.side_effect = Exception("not found")

        result = delete_note("bad-page-id")

        assert result["success"] is False
        assert "message" in result
        # Must NOT raise

    @patch("src.notes.notion.Client")
    def test_delete_archives_not_hard_deletes(self, mock_client_cls):
        """Notion does not support hard delete; archived=True is the correct approach."""
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.pages.update.return_value = {}

        delete_note("some-page")

        _, kwargs = mock_client.pages.update.call_args
        assert kwargs.get("archived") is True
