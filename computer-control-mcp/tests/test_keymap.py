"""Tests for xdotool-style key name mapping."""

from __future__ import annotations

import pytest

from computer_control_mcp.keymap import InvalidKeyError, to_pyautogui_keys


def test_to_pyautogui_keys_combo() -> None:
    assert to_pyautogui_keys("ctrl+a") == ["ctrl", "a"]
    assert to_pyautogui_keys("Ctrl + Shift + T") == ["ctrl", "shift", "t"]


def test_to_pyautogui_keys_single() -> None:
    assert to_pyautogui_keys("space") == ["space"]
    assert to_pyautogui_keys("f12") == ["f12"]


def test_invalid_key_empty() -> None:
    with pytest.raises(InvalidKeyError, match="Empty string"):
        to_pyautogui_keys("")


def test_invalid_key_unknown() -> None:
    with pytest.raises(InvalidKeyError, match="not_a_real_key"):
        to_pyautogui_keys("ctrl+not_a_real_key")


def test_super_maps_to_something_valid() -> None:
    keys = to_pyautogui_keys("super+t")
    assert len(keys) == 2
    assert keys[1] == "t"
    assert keys[0] in ("command", "win")
