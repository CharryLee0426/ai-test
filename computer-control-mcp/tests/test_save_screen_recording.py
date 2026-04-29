"""Tests for handle_save_screen_recording_sync."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from computer_control_mcp import runtime as runtime_mod
from computer_control_mcp.runtime import handle_save_screen_recording_sync


@pytest.fixture
def mock_gui() -> MagicMock:
    with patch("computer_control_mcp.runtime.pyautogui") as m:
        m.size.return_value = (1920, 1080)
        m.position.return_value = (100, 200)
        yield m


def test_save_screen_recording_custom_directory(mock_gui: MagicMock, tmp_path: Path) -> None:
    shot = Image.new("RGB", (80, 60), color=(1, 2, 3))
    custom = tmp_path / "recordings"
    mock_now = MagicMock()
    mock_now.strftime.return_value = "2026-04-28-12-00-00"
    ffmpeg_calls: list[list[str]] = []

    def _run_ffmpeg(cmd: list[str], **_kwargs: object) -> None:
        ffmpeg_calls.append(cmd)
        Path(cmd[-1]).write_bytes(b"mp4")

    with patch("computer_control_mcp.runtime._grab_screen_pil", return_value=shot.convert("RGBA")):
        with patch("computer_control_mcp.runtime._has_ffmpeg", return_value=True):
            with patch("computer_control_mcp.runtime.subprocess.run", side_effect=_run_ffmpeg):
                with patch("computer_control_mcp.runtime.datetime") as dtm:
                    with patch("computer_control_mcp.runtime.time.monotonic", side_effect=[0.0, 0.1, 0.2, 0.3]):
                        with patch("computer_control_mcp.runtime.time.sleep"):
                            dtm.now.return_value = mock_now
                            r = handle_save_screen_recording_sync(
                                {"path": str(custom), "duration_seconds": 1, "fps": 2}
                            )
    assert r == {
        "kind": "json",
        "data": {
            "ok": True,
            "path": str(custom / "screen-recording-2026-04-28-12-00-00.mp4"),
            "filename": "screen-recording-2026-04-28-12-00-00.mp4",
            "duration_seconds": 1.0,
            "fps": 2.0,
            "frames": 2,
            "frame_duration_ms": 500,
        },
    }
    out = custom / "screen-recording-2026-04-28-12-00-00.mp4"
    assert out.is_file()
    assert out.read_bytes() == b"mp4"
    assert ffmpeg_calls
    assert ffmpeg_calls[0][0] == "ffmpeg"


def test_save_screen_recording_default_directory(mock_gui: MagicMock, tmp_path: Path) -> None:
    shot = Image.new("RGB", (40, 30), color=(9, 9, 9))
    mock_now = MagicMock()
    mock_now.strftime.return_value = "2099-01-01-00-00-00"

    def _run_ffmpeg(cmd: list[str], **_kwargs: object) -> None:
        Path(cmd[-1]).write_bytes(b"mp4")

    with patch.object(runtime_mod, "_DEFAULT_SCREEN_RECORDING_DIR", tmp_path):
        with patch("computer_control_mcp.runtime._grab_screen_pil", return_value=shot.convert("RGBA")):
            with patch("computer_control_mcp.runtime._has_ffmpeg", return_value=True):
                with patch("computer_control_mcp.runtime.subprocess.run", side_effect=_run_ffmpeg):
                    with patch("computer_control_mcp.runtime.datetime") as dtm:
                        with patch("computer_control_mcp.runtime.time.monotonic", side_effect=[0.0, 0.1]):
                            with patch("computer_control_mcp.runtime.time.sleep"):
                                dtm.now.return_value = mock_now
                                r = handle_save_screen_recording_sync({})
    expected = tmp_path / "screen-recording-2099-01-01-00-00-00.mp4"
    assert r["data"]["path"] == str(expected)
    assert expected.is_file()


def test_save_screen_recording_creates_parent_directories(mock_gui: MagicMock, tmp_path: Path) -> None:
    shot = Image.new("RGB", (10, 10), color=(0, 0, 0))
    nested = tmp_path / "a" / "b"
    mock_now = MagicMock()
    mock_now.strftime.return_value = "2026-04-28-00-00-01"

    def _run_ffmpeg(cmd: list[str], **_kwargs: object) -> None:
        Path(cmd[-1]).write_bytes(b"mp4")

    with patch("computer_control_mcp.runtime._grab_screen_pil", return_value=shot.convert("RGBA")):
        with patch("computer_control_mcp.runtime._has_ffmpeg", return_value=True):
            with patch("computer_control_mcp.runtime.subprocess.run", side_effect=_run_ffmpeg):
                with patch("computer_control_mcp.runtime.datetime") as dtm:
                    with patch("computer_control_mcp.runtime.time.monotonic", side_effect=[0.0, 0.1]):
                        with patch("computer_control_mcp.runtime.time.sleep"):
                            dtm.now.return_value = mock_now
                            handle_save_screen_recording_sync({"path": str(nested)})
    assert (nested / "screen-recording-2026-04-28-00-00-01.mp4").is_file()


def test_save_screen_recording_path_must_be_directory(mock_gui: MagicMock, tmp_path: Path) -> None:
    file_path = tmp_path / "not_a_dir"
    file_path.write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="must be a directory"):
        handle_save_screen_recording_sync({"path": str(file_path)})


def test_save_screen_recording_path_must_be_string(mock_gui: MagicMock) -> None:
    with pytest.raises(ValueError, match="path must be a string"):
        handle_save_screen_recording_sync({"path": 123})  # type: ignore[arg-type]


def test_save_screen_recording_duration_must_be_number(mock_gui: MagicMock) -> None:
    with pytest.raises(ValueError, match="duration_seconds must be a number"):
        handle_save_screen_recording_sync({"duration_seconds": "3"})  # type: ignore[arg-type]


def test_save_screen_recording_duration_must_be_positive(mock_gui: MagicMock) -> None:
    with pytest.raises(ValueError, match="duration_seconds must be greater than 0"):
        handle_save_screen_recording_sync({"duration_seconds": 0})


def test_save_screen_recording_fps_must_be_positive(mock_gui: MagicMock) -> None:
    with pytest.raises(ValueError, match="fps must be greater than 0"):
        handle_save_screen_recording_sync({"fps": 0})


def test_save_screen_recording_requires_ffmpeg(mock_gui: MagicMock) -> None:
    with patch("computer_control_mcp.runtime._has_ffmpeg", return_value=False):
        with pytest.raises(RuntimeError, match="ffmpeg is required"):
            handle_save_screen_recording_sync({})
