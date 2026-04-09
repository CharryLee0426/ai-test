"""Tests for scaling helpers and small utilities (no real GUI)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from PIL import Image

import computer_control_mcp.runtime as runtime_mod
from computer_control_mcp.runtime import (
    _draw_crosshair,
    _grab_screen_pil,
    _pixels_to_scroll_clicks,
    _scale_coordinate,
    get_api_to_logical_scale,
    get_size_to_api_scale,
)


def test_get_size_to_api_scale_small_screen() -> None:
    assert get_size_to_api_scale(800, 600) == 1.0


def test_get_size_to_api_scale_long_edge_over_limit() -> None:
    s = get_size_to_api_scale(2000, 1000)
    assert 0 < s < 1.0
    assert int(2000 * s) <= 1568


def test_get_api_to_logical_scale() -> None:
    with patch("computer_control_mcp.runtime.pyautogui.size", return_value=(800, 600)):
        with patch(
            "computer_control_mcp.runtime._grab_screen_pil",
            return_value=Image.new("RGBA", (800, 600)),
        ):
            runtime_mod._screen_mapping = None
            scale = get_api_to_logical_scale()
    assert scale == 1.0


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (0, 1),
        (5, 1),
        (300, 30),
        (100_000, 500),
    ],
)
def test_pixels_to_scroll_clicks(amount: int, expected: int) -> None:
    assert _pixels_to_scroll_clicks(amount) == expected


def test_scale_coordinate_inside_bounds() -> None:
    with patch("computer_control_mcp.runtime.pyautogui.size", return_value=(100, 100)):
        with patch(
            "computer_control_mcp.runtime._grab_screen_pil",
            return_value=Image.new("RGBA", (100, 100)),
        ):
            runtime_mod._screen_mapping = None
            assert _scale_coordinate([50.0, 49.6]) == (50, 50)


def test_scale_coordinate_maps_capture_to_logical_pixels() -> None:
    """HiDPI: bitmap may be 2x logical size; API coords are in bitmap space, clicks use logical."""
    with patch("computer_control_mcp.runtime.pyautogui.size", return_value=(400, 300)):
        with patch(
            "computer_control_mcp.runtime._grab_screen_pil",
            return_value=Image.new("RGBA", (800, 600)),
        ):
            runtime_mod._screen_mapping = None
            assert _scale_coordinate([0.0, 0.0]) == (0, 0)
            assert _scale_coordinate([200.0, 150.0]) == (100, 75)
            assert _scale_coordinate([798.0, 598.0]) == (399, 299)


def test_scale_coordinate_outside_bounds() -> None:
    with patch("computer_control_mcp.runtime.pyautogui.size", return_value=(100, 100)):
        with patch(
            "computer_control_mcp.runtime._grab_screen_pil",
            return_value=Image.new("RGBA", (100, 100)),
        ):
            runtime_mod._screen_mapping = None
            with pytest.raises(ValueError, match="outside display bounds"):
                _scale_coordinate([150, 50])


def test_draw_crosshair_sets_red_pixel() -> None:
    img = Image.new("RGBA", (50, 50), (0, 0, 0, 255))
    _draw_crosshair(img, 25, 25, size=5)
    assert img.getpixel((25, 25))[:3] == (255, 0, 0)


def test_grab_screen_pil_linux_raises_without_display() -> None:
    import sys

    with patch.object(sys, "platform", "linux"):
        with patch("computer_control_mcp.runtime.pyautogui.screenshot", side_effect=RuntimeError("no display")):
            with pytest.raises(RuntimeError, match="no display"):
                _grab_screen_pil()
