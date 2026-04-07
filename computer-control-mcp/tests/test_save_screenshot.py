"""Tests for handle_save_screenshot_sync."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from computer_control_mcp import runtime as runtime_mod
from computer_control_mcp.runtime import handle_save_screenshot_sync


@pytest.fixture
def mock_gui() -> MagicMock:
    with patch("computer_control_mcp.runtime.pyautogui") as m:
        m.size.return_value = (1920, 1080)
        m.position.return_value = (100, 200)
        yield m


def test_save_screenshot_custom_directory(mock_gui: MagicMock, tmp_path: Path) -> None:
    shot = Image.new("RGB", (80, 60), color=(1, 2, 3))
    custom = tmp_path / "shots"
    mock_now = MagicMock()
    mock_now.strftime.return_value = "2026-04-07-13-06-05"
    with patch("computer_control_mcp.runtime.time.sleep"):
        with patch("computer_control_mcp.runtime._grab_screen_pil", return_value=shot.convert("RGBA")):
            with patch("computer_control_mcp.runtime.datetime") as dtm:
                dtm.now.return_value = mock_now
                r = handle_save_screenshot_sync({"path": str(custom)})
    assert r == {
        "kind": "json",
        "data": {
            "ok": True,
            "path": str(custom / "screenshot-2026-04-07-13-06-05.png"),
            "filename": "screenshot-2026-04-07-13-06-05.png",
        },
    }
    out = custom / "screenshot-2026-04-07-13-06-05.png"
    assert out.is_file()
    assert out.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_save_screenshot_default_directory(mock_gui: MagicMock, tmp_path: Path) -> None:
    shot = Image.new("RGB", (40, 30), color=(9, 9, 9))
    mock_now = MagicMock()
    mock_now.strftime.return_value = "2099-01-01-00-00-00"
    with patch.object(runtime_mod, "_DEFAULT_SCREENSHOT_DIR", tmp_path):
        with patch("computer_control_mcp.runtime.time.sleep"):
            with patch("computer_control_mcp.runtime._grab_screen_pil", return_value=shot.convert("RGBA")):
                with patch("computer_control_mcp.runtime.datetime") as dtm:
                    dtm.now.return_value = mock_now
                    r = handle_save_screenshot_sync({})
    expected = tmp_path / "screenshot-2099-01-01-00-00-00.png"
    assert r["data"]["path"] == str(expected)
    assert expected.is_file()


def test_save_screenshot_creates_parent_directories(mock_gui: MagicMock, tmp_path: Path) -> None:
    shot = Image.new("RGB", (10, 10), color=(0, 0, 0))
    nested = tmp_path / "a" / "b"
    mock_now = MagicMock()
    mock_now.strftime.return_value = "2026-04-07-00-00-01"
    with patch("computer_control_mcp.runtime.time.sleep"):
        with patch("computer_control_mcp.runtime._grab_screen_pil", return_value=shot.convert("RGBA")):
            with patch("computer_control_mcp.runtime.datetime") as dtm:
                dtm.now.return_value = mock_now
                handle_save_screenshot_sync({"path": str(nested)})
    assert (nested / "screenshot-2026-04-07-00-00-01.png").is_file()


def test_save_screenshot_path_must_be_directory(mock_gui: MagicMock, tmp_path: Path) -> None:
    file_path = tmp_path / "not_a_dir"
    file_path.write_text("x", encoding="utf-8")
    with patch("computer_control_mcp.runtime.time.sleep"):
        with pytest.raises(ValueError, match="must be a directory"):
            handle_save_screenshot_sync({"path": str(file_path)})


def test_save_screenshot_path_must_be_string(mock_gui: MagicMock, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="path must be a string"):
        handle_save_screenshot_sync({"path": 123})  # type: ignore[arg-type]
