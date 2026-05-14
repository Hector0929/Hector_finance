"""
test_recent_search.py — 最近搜尋紀錄邏輯的單元測試

測試 firebase_client 中 save_recent_search / get_recent_searches 的行為，
使用 unittest.mock patch 隔離 Firestore。
"""

from unittest.mock import MagicMock, patch


# ─── helpers ──────────────────────────────────────────────────────────────────

def _make_db_mock(existing_stocks: list[str]):
    """
    回傳一個模擬 Firestore db，其 recent_searches/{user_id} 文件
    已存有 existing_stocks 列表。
    """
    doc_mock = MagicMock()
    doc_mock.exists = bool(existing_stocks)
    doc_mock.to_dict.return_value = {"stocks": list(existing_stocks)}

    doc_ref_mock = MagicMock()
    doc_ref_mock.get.return_value = doc_mock

    collection_mock = MagicMock()
    collection_mock.document.return_value = doc_ref_mock

    db_mock = MagicMock()
    db_mock.collection.return_value = collection_mock

    return db_mock, doc_ref_mock


# ─── save_recent_search ───────────────────────────────────────────────────────

class TestSaveRecentSearch:
    def test_adds_new_stock_to_front(self):
        db_mock, doc_ref = _make_db_mock(["2454", "6669"])
        with patch("src.data.firebase_client._get_db", return_value=db_mock):
            from src.data.firebase_client import save_recent_search
            save_recent_search("2330", "user1")

        saved = doc_ref.set.call_args[0][0]["stocks"]
        assert saved[0] == "2330"
        assert "2454" in saved
        assert "6669" in saved

    def test_duplicate_moves_to_front(self):
        db_mock, doc_ref = _make_db_mock(["2454", "2330", "6669"])
        with patch("src.data.firebase_client._get_db", return_value=db_mock):
            from src.data.firebase_client import save_recent_search
            save_recent_search("2330", "user1")

        saved = doc_ref.set.call_args[0][0]["stocks"]
        assert saved[0] == "2330"
        # 不重複：原本的 2330 被移除，只出現一次
        assert saved.count("2330") == 1

    def test_caps_at_max_entries(self):
        existing = [str(i) for i in range(10)]  # 10 筆（已滿）
        db_mock, doc_ref = _make_db_mock(existing)
        with patch("src.data.firebase_client._get_db", return_value=db_mock):
            from src.data.firebase_client import save_recent_search
            save_recent_search("9999", "user1")

        saved = doc_ref.set.call_args[0][0]["stocks"]
        assert len(saved) == 10
        assert saved[0] == "9999"
        # 最舊的（index 9）應被捨棄
        assert "9" not in saved

    def test_no_db_silently_skips(self):
        with patch("src.data.firebase_client._get_db", return_value=None):
            from src.data.firebase_client import save_recent_search
            # 不應丟出例外
            save_recent_search("2330", "user1")

    def test_empty_existing_list(self):
        db_mock, doc_ref = _make_db_mock([])
        with patch("src.data.firebase_client._get_db", return_value=db_mock):
            from src.data.firebase_client import save_recent_search
            save_recent_search("2330", "user1")

        saved = doc_ref.set.call_args[0][0]["stocks"]
        assert saved == ["2330"]


# ─── get_recent_searches ──────────────────────────────────────────────────────

class TestGetRecentSearches:
    def test_returns_list_when_doc_exists(self):
        db_mock, _ = _make_db_mock(["2330", "2454"])
        with patch("src.data.firebase_client._get_db", return_value=db_mock):
            from src.data.firebase_client import get_recent_searches
            result = get_recent_searches("user1")

        assert result == ["2330", "2454"]

    def test_returns_empty_when_doc_not_exists(self):
        doc_mock = MagicMock()
        doc_mock.exists = False
        doc_ref_mock = MagicMock()
        doc_ref_mock.get.return_value = doc_mock
        collection_mock = MagicMock()
        collection_mock.document.return_value = doc_ref_mock
        db_mock = MagicMock()
        db_mock.collection.return_value = collection_mock

        with patch("src.data.firebase_client._get_db", return_value=db_mock):
            from src.data.firebase_client import get_recent_searches
            result = get_recent_searches("user1")

        assert result == []

    def test_returns_empty_when_no_db(self):
        with patch("src.data.firebase_client._get_db", return_value=None):
            from src.data.firebase_client import get_recent_searches
            result = get_recent_searches("user1")

        assert result == []
