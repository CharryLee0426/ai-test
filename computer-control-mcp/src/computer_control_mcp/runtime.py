"""Synchronous computer actions (PyAutoGUI), mirroring computer-use-mcp behavior."""

from __future__ import annotations

import io
import os
import time
import shutil
import subprocess
import sys
import tempfile
from typing import Any

import pyautogui
from PIL import Image, ImageDraw

from computer_control_mcp.keymap import InvalidKeyError, to_pyautogui_keys

# Match computer-use-mcp nut-js delays (mouse ~100ms); PyAutoGUI uses one global pause.
pyautogui.PAUSE = 0.1
pyautogui.FAILSAFE = False

KEYBOARD_TYPE_INTERVAL = 0.01

MAX_LONG_EDGE = 1568
MAX_PIXELS = 1.15 * 1024 * 1024

_xdotool_available: bool | None = None


def _has_xdotool() -> bool:
    global _xdotool_available
    if _xdotool_available is None:
        _xdotool_available = shutil.which("xdotool") is not None
    return _xdotool_available


def _xdotool_type(text: str) -> None:
    delay_ms = int(KEYBOARD_TYPE_INTERVAL * 1000) or 1
    env = {**os.environ, "DISPLAY": os.environ.get("DISPLAY", ":1")}
    subprocess.run(
        ["xdotool", "type", "--clearmodifiers", "--delay", str(delay_ms), "--", text],
        check=True,
        env=env,
    )


def get_size_to_api_scale(width: float, height: float) -> float:
    long_edge = max(width, height)
    total_pixels = width * height
    long_edge_scale = MAX_LONG_EDGE / long_edge if long_edge > MAX_LONG_EDGE else 1.0
    pixel_scale = (MAX_PIXELS / total_pixels) ** 0.5 if total_pixels > MAX_PIXELS else 1.0
    return min(long_edge_scale, pixel_scale)


def get_api_to_logical_scale() -> float:
    w, h = pyautogui.size()
    return 1.0 / get_size_to_api_scale(w, h)


def _grab_screen_pil() -> Image.Image:
    try:
        img = pyautogui.screenshot()
    except Exception:
        if sys.platform == "darwin":
            fd, path = tempfile.mkstemp(suffix=".png")
            os.close(fd)
            try:
                subprocess.run(["screencapture", "-x", path], check=True)
                img = Image.open(path)
            finally:
                try:
                    os.unlink(path)
                except OSError:
                    pass
        else:
            raise
    return img.convert("RGBA")


def _draw_crosshair(img: Image.Image, cx: int, cy: int, size: int = 20) -> None:
    draw = ImageDraw.Draw(img)
    w, h = img.size
    red = (255, 0, 0, 255)
    x0, x1 = max(0, cx - size), min(w - 1, cx + size)
    y0, y1 = max(0, cy - size), min(h - 1, cy + size)
    for lw in range(3):
        o = lw - 1
        if 0 <= cy + o < h:
            draw.line([(x0, cy + o), (x1, cy + o)], fill=red, width=1)
        if 0 <= cx + o < w:
            draw.line([(cx + o, y0), (cx + o, y1)], fill=red, width=1)


def _pixels_to_scroll_clicks(amount: int) -> int:
    """Map API pixel-like amounts to PyAutoGUI scroll units (OS-dependent)."""
    return max(1, min(500, int(round(amount / 10))))


def _scale_coordinate(
    coordinate: list[float] | tuple[float, float],
) -> tuple[int, int]:
    scale = get_api_to_logical_scale()
    x = int(round(coordinate[0] * scale))
    y = int(round(coordinate[1] * scale))
    w, h = pyautogui.size()
    if x < 0 or x >= w or y < 0 or y >= h:
        raise ValueError(f"Coordinates ({x}, {y}) are outside display bounds of {w}x{h}")
    return x, y


def handle_computer_sync(arguments: dict[str, Any]) -> dict[str, Any]:
    """
    Returns a dict:
    - {"kind": "json", "data": dict} for JSON-only results
    - {"kind": "screenshot", "meta": dict, "png_bytes": bytes}
    """
    action = arguments["action"]
    coordinate = arguments.get("coordinate")
    text = arguments.get("text")

    scaled: tuple[int, int] | None = None
    if coordinate is not None:
        if len(coordinate) != 2:
            raise ValueError("coordinate must have length 2")
        scaled = _scale_coordinate(coordinate)

    if action == "key":
        if not text:
            raise ValueError("Text required for key")
        try:
            keys = to_pyautogui_keys(text)
        except InvalidKeyError:
            raise
        pyautogui.hotkey(*keys)
        return {"kind": "json", "data": {"ok": True}}

    if action == "type":
        if not text:
            raise ValueError("Text required for type")
        if sys.platform == "linux" and _has_xdotool():
            _xdotool_type(text)
        else:
            pyautogui.write(text, interval=KEYBOARD_TYPE_INTERVAL)
        return {"kind": "json", "data": {"ok": True}}

    if action == "get_cursor_position":
        px, py = pyautogui.position()
        scale = get_api_to_logical_scale()
        return {
            "kind": "json",
            "data": {"x": int(round(px / scale)), "y": int(round(py / scale))},
        }

    if action == "mouse_move":
        if scaled is None:
            raise ValueError("Coordinate required for mouse_move")
        pyautogui.moveTo(scaled[0], scaled[1], duration=0)
        return {"kind": "json", "data": {"ok": True}}

    if action == "left_click":
        if scaled is not None:
            pyautogui.moveTo(scaled[0], scaled[1], duration=0)
        pyautogui.click(button="left")
        return {"kind": "json", "data": {"ok": True}}

    if action == "left_click_drag":
        if scaled is None:
            raise ValueError("Coordinate required for left_click_drag")
        pyautogui.mouseDown(button="left")
        pyautogui.moveTo(scaled[0], scaled[1], duration=0)
        pyautogui.mouseUp(button="left")
        return {"kind": "json", "data": {"ok": True}}

    if action == "right_click":
        if scaled is not None:
            pyautogui.moveTo(scaled[0], scaled[1], duration=0)
        pyautogui.click(button="right")
        return {"kind": "json", "data": {"ok": True}}

    if action == "middle_click":
        if scaled is not None:
            pyautogui.moveTo(scaled[0], scaled[1], duration=0)
        pyautogui.click(button="middle")
        return {"kind": "json", "data": {"ok": True}}

    if action == "double_click":
        if scaled is not None:
            pyautogui.moveTo(scaled[0], scaled[1], duration=0)
        pyautogui.doubleClick()
        return {"kind": "json", "data": {"ok": True}}

    if action == "scroll":
        if scaled is None:
            raise ValueError("Coordinate required for scroll")
        if not text:
            raise ValueError('Text required for scroll (direction like "up", "down:5")')
        parts = text.split(":")
        direction = parts[0].strip()
        amount_str = parts[1] if len(parts) > 1 else None
        amount = 300
        if amount_str is not None:
            amount_str = amount_str.strip()
            if not amount_str:
                raise ValueError(f"Invalid scroll amount: {parts[1]!r}")
            try:
                amount = int(amount_str, 10)
            except ValueError as e:
                raise ValueError(f"Invalid scroll amount: {amount_str}") from e
        if not direction:
            raise ValueError("Scroll direction required")
        if amount <= 0:
            raise ValueError(f"Invalid scroll amount: {amount_str}")

        pyautogui.moveTo(scaled[0], scaled[1], duration=0)
        clicks = _pixels_to_scroll_clicks(amount)
        d = direction.lower()
        if d == "up":
            pyautogui.scroll(clicks)
        elif d == "down":
            pyautogui.scroll(-clicks)
        elif d == "left":
            pyautogui.hscroll(-clicks)
        elif d == "right":
            pyautogui.hscroll(clicks)
        else:
            raise ValueError(f'Invalid scroll direction: {direction}. Use "up", "down", "left", or "right"')
        return {"kind": "json", "data": {"ok": True}}

    if action == "get_screenshot":
        time.sleep(1.0)
        cpx, cpy = pyautogui.position()
        image = _grab_screen_pil()
        api_scale = get_size_to_api_scale(image.width, image.height)
        if api_scale < 1:
            nw = max(1, int(image.width * api_scale))
            nh = max(1, int(image.height * api_scale))
            image = image.resize((nw, nh), Image.Resampling.LANCZOS)

        scale = get_api_to_logical_scale()
        cursor_in_image_x = int(cpx / scale)
        cursor_in_image_y = int(cpy / scale)
        _draw_crosshair(image, cursor_in_image_x, cursor_in_image_y)

        buf = io.BytesIO()
        image.save(buf, format="PNG", optimize=True, compress_level=9)
        png_bytes = buf.getvalue()
        meta = {"image_width": image.width, "image_height": image.height}
        return {"kind": "screenshot", "meta": meta, "png_bytes": png_bytes}

    raise ValueError(f"Unknown action: {action}")
