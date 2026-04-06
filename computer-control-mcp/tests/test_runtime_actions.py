"""Tests for handle_computer_sync (PyAutoGUI mocked)."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from computer_control_mcp.runtime import handle_computer_sync


@pytest.fixture
def mock_gui() -> MagicMock:
    with patch("computer_control_mcp.runtime.pyautogui") as m:
        m.size.return_value = (1920, 1080)
        m.position.return_value = (100, 200)
        yield m


def test_key(mock_gui: MagicMock) -> None:
    r = handle_computer_sync({"action": "key", "text": "ctrl+s"})
    assert r == {"kind": "json", "data": {"ok": True}}
    mock_gui.hotkey.assert_called_once_with("ctrl", "s")


def test_key_requires_text(mock_gui: MagicMock) -> None:
    with pytest.raises(ValueError, match="Text required for key"):
        handle_computer_sync({"action": "key"})


def test_type_pyautogui_when_not_linux_xdotool(mock_gui: MagicMock) -> None:
    with patch.object(sys, "platform", "darwin"):
        r = handle_computer_sync({"action": "type", "text": "hello"})
    assert r == {"kind": "json", "data": {"ok": True}}
    mock_gui.write.assert_called_once()
    args, kwargs = mock_gui.write.call_args
    assert args[0] == "hello"
    assert "interval" in kwargs


def test_type_uses_xdotool_on_linux_when_available(mock_gui: MagicMock) -> None:
    with patch.object(sys, "platform", "linux"):
        with patch("computer_control_mcp.runtime.shutil.which", return_value="/usr/bin/xdotool"):
            with patch("computer_control_mcp.runtime.subprocess.run") as run:
                r = handle_computer_sync({"action": "type", "text": "x"})
    assert r == {"kind": "json", "data": {"ok": True}}
    mock_gui.write.assert_not_called()
    run.assert_called_once()
    assert run.call_args[0][0][:2] == ["xdotool", "type"]


def test_get_cursor_position(mock_gui: MagicMock) -> None:
    mock_gui.size.return_value = (800, 600)
    mock_gui.position.return_value = (100, 200)
    r = handle_computer_sync({"action": "get_cursor_position"})
    assert r["kind"] == "json"
    assert r["data"]["x"] == 100
    assert r["data"]["y"] == 200


def test_mouse_move(mock_gui: MagicMock) -> None:
    with patch("computer_control_mcp.runtime.pyautogui.size", return_value=(500, 500)):
        r = handle_computer_sync({"action": "mouse_move", "coordinate": [10, 20]})
    assert r == {"kind": "json", "data": {"ok": True}}
    mock_gui.moveTo.assert_called_with(10, 20, duration=0)


def test_left_click_with_coordinate(mock_gui: MagicMock) -> None:
    with patch("computer_control_mcp.runtime.pyautogui.size", return_value=(500, 500)):
        r = handle_computer_sync({"action": "left_click", "coordinate": [5, 6]})
    assert r == {"kind": "json", "data": {"ok": True}}
    mock_gui.moveTo.assert_called_once_with(5, 6, duration=0)
    mock_gui.click.assert_called_once_with(button="left")


def test_left_click_without_coordinate(mock_gui: MagicMock) -> None:
    r = handle_computer_sync({"action": "left_click"})
    mock_gui.moveTo.assert_not_called()
    mock_gui.click.assert_called_once_with(button="left")


def test_left_click_drag(mock_gui: MagicMock) -> None:
    with patch("computer_control_mcp.runtime.pyautogui.size", return_value=(800, 600)):
        r = handle_computer_sync({"action": "left_click_drag", "coordinate": [7, 8]})
    assert r == {"kind": "json", "data": {"ok": True}}
    mock_gui.mouseDown.assert_called_once_with(button="left")
    mock_gui.moveTo.assert_called_once_with(7, 8, duration=0)
    mock_gui.mouseUp.assert_called_once_with(button="left")


def test_right_click(mock_gui: MagicMock) -> None:
    with patch("computer_control_mcp.runtime.pyautogui.size", return_value=(800, 600)):
        r = handle_computer_sync({"action": "right_click", "coordinate": [1, 2]})
    mock_gui.click.assert_called_once_with(button="right")


def test_middle_click(mock_gui: MagicMock) -> None:
    with patch("computer_control_mcp.runtime.pyautogui.size", return_value=(800, 600)):
        r = handle_computer_sync({"action": "middle_click", "coordinate": [3, 4]})
    mock_gui.click.assert_called_once_with(button="middle")


def test_double_click(mock_gui: MagicMock) -> None:
    with patch("computer_control_mcp.runtime.pyautogui.size", return_value=(800, 600)):
        r = handle_computer_sync({"action": "double_click", "coordinate": [9, 9]})
    mock_gui.doubleClick.assert_called_once()


@pytest.mark.parametrize(
    ("text", "scroll_kw", "hscroll_kw"),
    [
        ("up", {"call": "scroll", "args": (30,)}, None),
        ("down", {"call": "scroll", "args": (-30,)}, None),
        ("left", None, {"call": "hscroll", "args": (-30,)}),
        ("right", None, {"call": "hscroll", "args": (30,)}),
    ],
)
def test_scroll_directions(
    mock_gui: MagicMock,
    text: str,
    scroll_kw: dict | None,
    hscroll_kw: dict | None,
) -> None:
    with patch("computer_control_mcp.runtime.pyautogui.size", return_value=(800, 600)):
        r = handle_computer_sync({"action": "scroll", "coordinate": [10, 10], "text": f"{text}:300"})
    assert r == {"kind": "json", "data": {"ok": True}}
    mock_gui.moveTo.assert_called_with(10, 10, duration=0)
    if scroll_kw:
        getattr(mock_gui, scroll_kw["call"]).assert_called_once_with(*scroll_kw["args"])
    if hscroll_kw:
        getattr(mock_gui, hscroll_kw["call"]).assert_called_once_with(*hscroll_kw["args"])


def test_scroll_default_amount(mock_gui: MagicMock) -> None:
    with patch("computer_control_mcp.runtime.pyautogui.size", return_value=(800, 600)):
        handle_computer_sync({"action": "scroll", "coordinate": [0, 0], "text": "down"})
    mock_gui.scroll.assert_called_once_with(-30)


def test_scroll_errors(mock_gui: MagicMock) -> None:
    with patch("computer_control_mcp.runtime.pyautogui.size", return_value=(800, 600)):
        with pytest.raises(ValueError, match="Coordinate required"):
            handle_computer_sync({"action": "scroll", "text": "up"})
        with pytest.raises(ValueError, match="Text required"):
            handle_computer_sync({"action": "scroll", "coordinate": [1, 1]})
        with pytest.raises(ValueError, match="Invalid scroll direction"):
            handle_computer_sync({"action": "scroll", "coordinate": [1, 1], "text": "sideways"})
        with pytest.raises(ValueError, match="Invalid scroll amount"):
            handle_computer_sync({"action": "scroll", "coordinate": [1, 1], "text": "up:0"})
        with pytest.raises(ValueError, match="Invalid scroll amount"):
            handle_computer_sync({"action": "scroll", "coordinate": [1, 1], "text": "up:"})


def test_get_screenshot(mock_gui: MagicMock) -> None:
    shot = Image.new("RGB", (400, 300), color=(10, 20, 30))
    with patch("computer_control_mcp.runtime.time.sleep"):
        with patch("computer_control_mcp.runtime._grab_screen_pil", return_value=shot.convert("RGBA")):
            with patch("computer_control_mcp.runtime.pyautogui.size", return_value=(1920, 1080)):
                r = handle_computer_sync({"action": "get_screenshot"})
    assert r["kind"] == "screenshot"
    assert r["meta"] == {"image_width": 400, "image_height": 300}
    assert r["png_bytes"].startswith(b"\x89PNG\r\n\x1a\n")


def test_get_screenshot_downscales_large_image(mock_gui: MagicMock) -> None:
    shot = Image.new("RGB", (4000, 3000), color=(0, 0, 0))
    with patch("computer_control_mcp.runtime.time.sleep"):
        with patch("computer_control_mcp.runtime._grab_screen_pil", return_value=shot.convert("RGBA")):
            with patch("computer_control_mcp.runtime.pyautogui.size", return_value=(4000, 3000)):
                r = handle_computer_sync({"action": "get_screenshot"})
    assert r["kind"] == "screenshot"
    assert r["meta"]["image_width"] < 4000
    assert r["meta"]["image_height"] < 3000


def test_unknown_action(mock_gui: MagicMock) -> None:
    with pytest.raises(ValueError, match="Unknown action"):
        handle_computer_sync({"action": "not_an_action"})  # type: ignore[arg-type]


def test_bad_coordinate_length(mock_gui: MagicMock) -> None:
    with pytest.raises(ValueError, match="coordinate must have length 2"):
        handle_computer_sync({"action": "mouse_move", "coordinate": [1]})  # type: ignore[arg-type]
