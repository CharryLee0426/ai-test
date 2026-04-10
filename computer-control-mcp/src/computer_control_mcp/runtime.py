"""Synchronous computer actions (PyAutoGUI), mirroring computer-use-mcp behavior."""

from __future__ import annotations

import io
import os
import time
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import pyautogui
from PIL import Image, ImageDraw

from computer_control_mcp.keymap import InvalidKeyError, to_pyautogui_keys

_DEFAULT_SCREENSHOT_DIR = Path(__file__).resolve().parent / "screenshots"

# Match computer-use-mcp nut-js delays (mouse ~100ms); PyAutoGUI uses one global pause.
pyautogui.PAUSE = 0.1
pyautogui.FAILSAFE = False

KEYBOARD_TYPE_INTERVAL = 0.01

MAX_LONG_EDGE = 1568
MAX_PIXELS = 1.15 * 1024 * 1024

_xdotool_available: bool | None = None

# (move_w, move_h, api_w, api_h, capture_w, capture_h) — move_* match pyautogui.moveTo / size();
# api_* are the downsampled screenshot sent to the model; capture_* are raw bitmap size before resize.
# On macOS, screencapture / Pillow return backing-store pixels (often 2× logical), while
# CGDisplayBounds + CGEventGetLocation share one logical/global space — map with proportional scale
# (see _darwin_pointer_bitmap_xy_quartz).
_screen_mapping: tuple[int, int, int, int, int, int] | None = None

# Set True for the whole pytest session (conftest) so unit tests keep using pyautogui ratio mapping.
_pytest_active: bool = False


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


def _api_output_dimensions(capture_width: int, capture_height: int) -> tuple[int, int]:
    """Size of the downsampled image sent to the model (same rules as get_screenshot)."""
    api_scale = get_size_to_api_scale(capture_width, capture_height)
    if api_scale < 1:
        nw = max(1, int(capture_width * api_scale))
        nh = max(1, int(capture_height * api_scale))
        return nw, nh
    return capture_width, capture_height


def _mapping_from_fresh_capture() -> tuple[int, int, int, int, int, int]:
    lw, lh = pyautogui.size()
    raw = _grab_screen_pil()
    iw, ih = raw.width, raw.height
    aw, ah = _api_output_dimensions(iw, ih)
    return lw, lh, aw, ah, iw, ih


def _active_screen_mapping() -> tuple[int, int, int, int, int, int]:
    global _screen_mapping
    if _screen_mapping is None:
        _screen_mapping = _mapping_from_fresh_capture()
    return _screen_mapping


def _darwin_quartz_desktop_union() -> tuple[float, float, float, float]:
    """
    Union of all active displays in Quartz global space (same units as CGEventGetLocation / CGDisplayBounds).
    Returns min_x, min_y_bottom, total_w, total_h where y increases upward (Core Graphics).
    """
    import Quartz

    err, displays, count = Quartz.CGGetActiveDisplayList(32, None, None)
    if err != 0 or count == 0:
        displays = (Quartz.CGMainDisplayID(),)
    min_x = min_y = float("inf")
    max_x = max_y = float("-inf")
    for d in displays:
        b = Quartz.CGDisplayBounds(d)
        x0, y0 = float(b.origin.x), float(b.origin.y)
        x1 = x0 + float(b.size.width)
        y1 = y0 + float(b.size.height)
        min_x = min(min_x, x0)
        min_y = min(min_y, y0)
        max_x = max(max_x, x1)
        max_y = max(max_y, y1)
    total_w = max_x - min_x
    total_h = max_y - min_y
    return min_x, min_y, total_w, total_h


def _darwin_pointer_bitmap_xy_quartz(iw: int, ih: int) -> tuple[int, int]:
    """
    Map cursor to top-left PNG/screencapture pixel coordinates. Screencapture is often 2× the
    width/height of CGDisplayBounds; proportional scaling fixes LLM vs cursor mismatch.
    """
    import Quartz

    min_x, min_y, total_w, total_h = _darwin_quartz_desktop_union()
    if total_w <= 0 or total_h <= 0:
        raise ValueError("invalid Quartz desktop union")
    ev = Quartz.CGEventCreate(None)
    loc = Quartz.CGEventGetLocation(ev)
    mx, my = float(loc.x), float(loc.y)
    rel_x = max(0.0, min(mx - min_x, total_w))
    # Quartz y increases upward; PNG row 0 is the top of the virtual desktop.
    max_y = min_y + total_h
    dist_from_top = max(0.0, min(max_y - my, total_h))
    bx = int(round(rel_x * iw / total_w))
    by = int(round(dist_from_top * ih / total_h))
    bx = max(0, min(bx, iw - 1))
    by = max(0, min(by, ih - 1))
    return bx, by


def _cocoa_desktop_point_rect() -> tuple[float, float, float, float]:
    """Union of all NSScreen frames (AppKit points, bottom-left) — fallback only."""
    import AppKit

    screens = AppKit.NSScreen.screens()
    min_left = min(float(s.frame().origin.x) for s in screens)
    min_bottom = min(float(s.frame().origin.y) for s in screens)
    max_right = max(float(s.frame().origin.x + s.frame().size.width) for s in screens)
    max_top = max(float(s.frame().origin.y + s.frame().size.height) for s in screens)
    return min_left, min_bottom, max_right - min_left, max_top - min_bottom


def _darwin_pointer_bitmap_xy_union_desktop_points(iw: int, ih: int) -> tuple[int, int]:
    """Fallback: NSScreen frame union in points (no Quartz / wrong when bitmap is 2×)."""
    import AppKit

    mouse = AppKit.NSEvent.mouseLocation()
    mx, my = float(mouse.x), float(mouse.y)
    min_left, min_bottom, dw, dh = _cocoa_desktop_point_rect()
    if dw <= 0 or dh <= 0:
        raise ValueError("invalid Cocoa desktop rect")
    rel_x = mx - min_left
    rel_y_bl = my - min_bottom
    rel_y_top = dh - rel_y_bl
    rel_x = max(0.0, min(rel_x, dw))
    rel_y_top = max(0.0, min(rel_y_top, dh))
    bx = int(round(rel_x * iw / dw))
    by = int(round(rel_y_top * ih / dh))
    bx = max(0, min(bx, iw - 1))
    by = max(0, min(by, ih - 1))
    return bx, by


def _pointer_to_bitmap_xy(iw: int, ih: int) -> tuple[int, int]:
    """
    Cursor position in the same pixel grid as _grab_screen_pil() / PNG sent to the model (before API resize).
    """
    if sys.platform == "darwin" and not _pytest_active:
        try:
            return _darwin_pointer_bitmap_xy_quartz(iw, ih)
        except Exception:
            try:
                return _darwin_pointer_bitmap_xy_union_desktop_points(iw, ih)
            except Exception:
                pass
    px, py = pyautogui.position()
    lw, lh = pyautogui.size()
    return (
        int(round(px * iw / lw)),
        int(round(py * ih / lh)),
    )


def _bitmap_xy_to_api(ax: int, ay: int, iw: int, ih: int, aw: int, ah: int) -> tuple[int, int]:
    return int(round(ax * aw / iw)), int(round(ay * ah / ih))


def get_api_to_logical_scale() -> float:
    """Legacy single-axis scale: move_space_width / api_width (prefer _active_screen_mapping for clicks)."""
    lw, _lh, aw, _ah, _iw, _ih = _active_screen_mapping()
    return lw / aw if aw else 1.0


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
    lw, lh, aw, ah, _iw, _ih = _active_screen_mapping()
    x = int(round(coordinate[0] * lw / aw))
    y = int(round(coordinate[1] * lh / ah))
    if x < 0 or x >= lw or y < 0 or y >= lh:
        raise ValueError(f"Coordinates ({x}, {y}) are outside display bounds of {lw}x{lh}")
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
        lw, lh, aw, ah, iw, ih = _active_screen_mapping()
        bx, by = _pointer_to_bitmap_xy(iw, ih)
        api_x, api_y = _bitmap_xy_to_api(bx, by, iw, ih, aw, ah)
        return {"kind": "json", "data": {"x": api_x, "y": api_y}}

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
        global _screen_mapping
        time.sleep(1.0)
        lw, lh = pyautogui.size()
        raw = _grab_screen_pil()
        iw, ih = raw.width, raw.height
        image = raw
        api_scale = get_size_to_api_scale(image.width, image.height)
        if api_scale < 1:
            nw = max(1, int(image.width * api_scale))
            nh = max(1, int(image.height * api_scale))
            image = image.resize((nw, nh), Image.Resampling.LANCZOS)

        _screen_mapping = (lw, lh, image.width, image.height, iw, ih)
        bx, by = _pointer_to_bitmap_xy(iw, ih)
        cursor_in_image_x, cursor_in_image_y = _bitmap_xy_to_api(bx, by, iw, ih, image.width, image.height)
        _draw_crosshair(image, cursor_in_image_x, cursor_in_image_y)

        buf = io.BytesIO()
        image.save(buf, format="PNG", optimize=True, compress_level=9)
        png_bytes = buf.getvalue()
        meta = {
            "image_width": image.width,
            "image_height": image.height,
            "mouse_coordinate_space": (
                "Use these image_width/image_height for all mouse coordinates until the next get_screenshot; "
                "origin top-left; same grid as the attached PNG. Server maps to desktop pixels."
            ),
            "vision_limits_note": (
                "Screenshot is pre-sized to reduce Anthropic API-side resizing "
                "(see https://docs.anthropic.com/en/docs/build-with-claude/vision#evaluate-image-size )."
            ),
        }
        return {"kind": "screenshot", "meta": meta, "png_bytes": png_bytes}

    raise ValueError(f"Unknown action: {action}")


def handle_save_screenshot_sync(arguments: dict[str, Any]) -> dict[str, Any]:
    """
    Capture a full-resolution screenshot (with crosshair) and write PNG to disk.

    Returns {"kind": "json", "data": {"ok": True, "path": str, "filename": str}}.
    """
    raw_path = arguments.get("path")
    if raw_path is not None and not isinstance(raw_path, str):
        raise ValueError("path must be a string when provided")
    dest_dir = Path(raw_path).expanduser().resolve() if raw_path else _DEFAULT_SCREENSHOT_DIR
    if dest_dir.exists() and not dest_dir.is_dir():
        raise ValueError(f"path must be a directory: {dest_dir}")
    dest_dir.mkdir(parents=True, exist_ok=True)

    time.sleep(1.0)
    image = _grab_screen_pil()
    iw, ih = image.width, image.height
    bx, by = _pointer_to_bitmap_xy(iw, ih)
    _draw_crosshair(image, bx, by)

    ts = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    filename = f"screenshot-{ts}.png"
    out_path = dest_dir / filename
    image.save(out_path, format="PNG", optimize=True, compress_level=9)

    return {"kind": "json", "data": {"ok": True, "path": str(out_path), "filename": filename}}
