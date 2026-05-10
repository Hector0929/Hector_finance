"""
test_watchlist.py — M9 自選清單單元測試

使用 monkeypatch 將 WATCHLIST_PATH 指向 tmp_path，確保測試隔離。
"""

import json
import pytest
from unittest.mock import patch
from pathlib import Path

from src.watchlist.manager import (
    load_watchlist,
    save_watchlist,
    add_stock,
    remove_stock,
    is_in_watchlist,
    get_watchlist_ids,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _patch_path(monkeypatch, tmp_path: Path) -> Path:
    """將 WATCHLIST_PATH patch 指向 tmp_path 底下的 watchlist.json。"""
    target = tmp_path / "watchlist.json"
    monkeypatch.setattr("src.watchlist.manager.WATCHLIST_PATH", target)
    return target


# ---------------------------------------------------------------------------
# TestLoadWatchlist
# ---------------------------------------------------------------------------

class TestLoadWatchlist:
    def test_returns_empty_list_when_file_not_exist(self, monkeypatch, tmp_path):
        """檔案不存在時應回傳空清單，不拋出例外。"""
        _patch_path(monkeypatch, tmp_path)
        result = load_watchlist()
        assert result == []

    def test_loads_existing_file(self, monkeypatch, tmp_path):
        """正常的 JSON 檔案應正確讀取並回傳清單。"""
        target = _patch_path(monkeypatch, tmp_path)
        sample = [
            {"stock_id": "2330", "name": "台積電", "added_at": "2026-01-01T00:00:00"},
            {"stock_id": "2317", "name": "鴻海", "added_at": "2026-01-02T00:00:00"},
        ]
        target.write_text(json.dumps(sample, ensure_ascii=False), encoding="utf-8")

        result = load_watchlist()
        assert len(result) == 2
        assert result[0]["stock_id"] == "2330"
        assert result[1]["stock_id"] == "2317"

    def test_returns_empty_on_corrupt_json(self, monkeypatch, tmp_path):
        """損壞的 JSON 內容應回傳空清單，不拋出例外。"""
        target = _patch_path(monkeypatch, tmp_path)
        target.write_text("{ this is not valid json !!!", encoding="utf-8")

        result = load_watchlist()
        assert result == []

    def test_returns_empty_when_json_is_not_list(self, monkeypatch, tmp_path):
        """JSON 內容不是 list 時應回傳空清單。"""
        target = _patch_path(monkeypatch, tmp_path)
        target.write_text(json.dumps({"key": "value"}), encoding="utf-8")

        result = load_watchlist()
        assert result == []


# ---------------------------------------------------------------------------
# TestSaveWatchlist
# ---------------------------------------------------------------------------

class TestSaveWatchlist:
    def test_saves_and_reloads(self, monkeypatch, tmp_path):
        """儲存後重新讀取應得到相同資料。"""
        _patch_path(monkeypatch, tmp_path)
        data = [{"stock_id": "2330", "name": "台積電", "added_at": "2026-01-01T00:00:00"}]

        save_watchlist(data)
        reloaded = load_watchlist()

        assert reloaded == data

    def test_returns_true_on_success(self, monkeypatch, tmp_path):
        """成功寫入應回傳 True。"""
        _patch_path(monkeypatch, tmp_path)
        result = save_watchlist([])
        assert result is True

    def test_returns_false_on_write_error(self, monkeypatch, tmp_path):
        """無法寫入時應回傳 False，不拋出例外。"""
        # 將路徑指向一個目錄（無法寫入檔案）
        bad_path = tmp_path / "subdir"
        bad_path.mkdir()
        monkeypatch.setattr("src.watchlist.manager.WATCHLIST_PATH", bad_path)

        result = save_watchlist([{"stock_id": "2330"}])
        assert result is False


# ---------------------------------------------------------------------------
# TestAddStock
# ---------------------------------------------------------------------------

class TestAddStock:
    def test_add_new_stock(self, monkeypatch, tmp_path):
        """新增不在清單中的股票應回傳 success=True。"""
        _patch_path(monkeypatch, tmp_path)
        result = add_stock("2330", "台積電")
        assert result["success"] is True
        assert result["message"] == "已加入自選清單"

    def test_add_stock_persisted(self, monkeypatch, tmp_path):
        """新增股票後，清單中應包含該股票。"""
        _patch_path(monkeypatch, tmp_path)
        add_stock("2330", "台積電")
        ids = get_watchlist_ids()
        assert "2330" in ids

    def test_duplicate_returns_false(self, monkeypatch, tmp_path):
        """重複新增同一股票應回傳 success=False，且訊息正確。"""
        _patch_path(monkeypatch, tmp_path)
        add_stock("2330", "台積電")
        result = add_stock("2330", "台積電")
        assert result["success"] is False
        assert result["message"] == "已在自選清單中"

    def test_duplicate_does_not_increase_count(self, monkeypatch, tmp_path):
        """重複新增同一股票時，清單長度不應增加。"""
        _patch_path(monkeypatch, tmp_path)
        add_stock("2330", "台積電")
        add_stock("2330", "台積電")
        assert len(load_watchlist()) == 1

    def test_added_at_is_set(self, monkeypatch, tmp_path):
        """新增後 added_at 欄位應存在且非空字串。"""
        _patch_path(monkeypatch, tmp_path)
        add_stock("2330", "台積電")
        watchlist = load_watchlist()
        assert len(watchlist) == 1
        assert "added_at" in watchlist[0]
        assert watchlist[0]["added_at"] != ""

    def test_added_at_is_iso_format(self, monkeypatch, tmp_path):
        """added_at 應為合法的 ISO 8601 格式字串。"""
        from datetime import datetime
        _patch_path(monkeypatch, tmp_path)
        add_stock("2330", "台積電")
        watchlist = load_watchlist()
        # datetime.fromisoformat 解析失敗會拋出 ValueError
        dt = datetime.fromisoformat(watchlist[0]["added_at"])
        assert isinstance(dt, datetime)

    def test_add_stock_with_empty_name(self, monkeypatch, tmp_path):
        """不傳 name 時應正常新增，name 預設為空字串。"""
        _patch_path(monkeypatch, tmp_path)
        result = add_stock("2330")
        assert result["success"] is True
        watchlist = load_watchlist()
        assert watchlist[0]["name"] == ""


# ---------------------------------------------------------------------------
# TestRemoveStock
# ---------------------------------------------------------------------------

class TestRemoveStock:
    def test_remove_existing(self, monkeypatch, tmp_path):
        """移除清單中存在的股票應回傳 success=True。"""
        _patch_path(monkeypatch, tmp_path)
        add_stock("2330", "台積電")
        result = remove_stock("2330")
        assert result["success"] is True
        assert result["message"] == "已移除"

    def test_remove_existing_clears_from_list(self, monkeypatch, tmp_path):
        """移除後，清單中不應再含有該股票。"""
        _patch_path(monkeypatch, tmp_path)
        add_stock("2330", "台積電")
        remove_stock("2330")
        assert "2330" not in get_watchlist_ids()

    def test_remove_nonexistent_returns_false(self, monkeypatch, tmp_path):
        """移除不存在的股票應回傳 success=False，且訊息正確。"""
        _patch_path(monkeypatch, tmp_path)
        result = remove_stock("9999")
        assert result["success"] is False
        assert result["message"] == "股票不在自選清單中"

    def test_remove_only_target_stock(self, monkeypatch, tmp_path):
        """移除特定股票時，其他股票應保留。"""
        _patch_path(monkeypatch, tmp_path)
        add_stock("2330", "台積電")
        add_stock("2317", "鴻海")
        remove_stock("2330")
        ids = get_watchlist_ids()
        assert "2317" in ids
        assert "2330" not in ids


# ---------------------------------------------------------------------------
# TestIsInWatchlist
# ---------------------------------------------------------------------------

class TestIsInWatchlist:
    def test_existing_stock(self, monkeypatch, tmp_path):
        """清單中存在的股票應回傳 True。"""
        _patch_path(monkeypatch, tmp_path)
        add_stock("2330", "台積電")
        assert is_in_watchlist("2330") is True

    def test_nonexistent_stock(self, monkeypatch, tmp_path):
        """清單中不存在的股票應回傳 False。"""
        _patch_path(monkeypatch, tmp_path)
        assert is_in_watchlist("9999") is False

    def test_after_removal_returns_false(self, monkeypatch, tmp_path):
        """移除後再查詢應回傳 False。"""
        _patch_path(monkeypatch, tmp_path)
        add_stock("2330", "台積電")
        remove_stock("2330")
        assert is_in_watchlist("2330") is False

    def test_empty_watchlist_returns_false(self, monkeypatch, tmp_path):
        """空清單時對任何 stock_id 應回傳 False。"""
        _patch_path(monkeypatch, tmp_path)
        assert is_in_watchlist("2330") is False


# ---------------------------------------------------------------------------
# TestGetWatchlistIds
# ---------------------------------------------------------------------------

class TestGetWatchlistIds:
    def test_returns_list_of_ids(self, monkeypatch, tmp_path):
        """有資料時應回傳包含所有 stock_id 的列表。"""
        _patch_path(monkeypatch, tmp_path)
        add_stock("2330", "台積電")
        add_stock("2317", "鴻海")
        ids = get_watchlist_ids()
        assert "2330" in ids
        assert "2317" in ids
        assert len(ids) == 2

    def test_empty_watchlist(self, monkeypatch, tmp_path):
        """空清單時應回傳空列表。"""
        _patch_path(monkeypatch, tmp_path)
        ids = get_watchlist_ids()
        assert ids == []

    def test_returns_only_strings(self, monkeypatch, tmp_path):
        """回傳的列表中每個元素都應為字串。"""
        _patch_path(monkeypatch, tmp_path)
        add_stock("2330", "台積電")
        add_stock("2317", "鴻海")
        ids = get_watchlist_ids()
        assert all(isinstance(i, str) for i in ids)

    def test_order_preserved(self, monkeypatch, tmp_path):
        """回傳的 stock_id 列表應保持加入順序。"""
        _patch_path(monkeypatch, tmp_path)
        add_stock("2330", "台積電")
        add_stock("2317", "鴻海")
        add_stock("0050", "元大台灣50")
        ids = get_watchlist_ids()
        assert ids == ["2330", "2317", "0050"]
