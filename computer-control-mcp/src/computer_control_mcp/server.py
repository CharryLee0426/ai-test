"""MCP stdio server: registers `computer` and `save_screenshot` tools."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import sys
from io import TextIOWrapper
from typing import Any

import anyio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server

from computer_control_mcp.keymap import InvalidKeyError
from computer_control_mcp.runtime import handle_computer_sync, handle_save_screenshot_sync

logger = logging.getLogger(__name__)

ACTION_DESCRIPTION = """The action to perform. The available actions are:
* key: Press a key or key-combination on the keyboard.
* type: Type a string of text on the keyboard.
* get_cursor_position: Get cursor (x, y) in the same coordinate system as the last get_screenshot image (see image_width/image_height in that result), not raw monitor pixels.
* mouse_move: Move the cursor; (x, y) must use the last screenshot's image_width x image_height space (top-left origin).
* left_click: Click the left mouse button. If coordinate is provided, moves to that position first.
* left_click_drag: Click and drag the cursor to a specified (x, y) pixel coordinate on the screen.
* right_click: Click the right mouse button. If coordinate is provided, moves to that position first.
* middle_click: Click the middle mouse button. If coordinate is provided, moves to that position first.
* double_click: Double-click the left mouse button. If coordinate is provided, moves to that position first.
* scroll: Scroll the screen in a specified direction. Requires coordinate (moves there first) and text parameter with direction: "up", "down", "left", or "right". Optionally append ":N" to scroll N pixels (default 300), e.g. "down:500".
* get_screenshot: Take a screenshot of the screen."""

TOOL_DESCRIPTION = """Use a mouse and keyboard to interact with a computer, and take screenshots.

Coordinate system (critical for vision models, e.g. Claude):
* After get_screenshot, every coordinate you pass (mouse_move, click, scroll, drag, get_cursor_position output) is in the PNG pixel grid from that screenshot: x in [0, image_width), y in [0, image_height), origin top-left. Use the numeric image_width and image_height from the JSON printed with the screenshot — not your physical display resolution.
* The host downsamples screenshots to stay within Anthropic vision limits (~1.15MP, long edge ≤1568px) so the API should not resize the image again; still, always anchor clicks to the reported image_width/image_height.
* The MCP server maps these coordinates to real desktop pixels; you must not "scale up" to monitor size yourself.

* This is an interface to a desktop GUI. You do not have access to a terminal or applications menu. You must click on desktop icons to start applications.
* Always prefer using keyboard shortcuts rather than clicking, where possible.
* If you see boxes with two letters in them, typing these letters will click that element. Use this instead of other shortcuts or clicking, where possible.
* Some applications may take time to start or process actions, so you may need to wait and take successive screenshots to see the results of your actions. E.g. if you click on Firefox and a window doesn't open, try taking another screenshot.
* Whenever you intend to move the cursor to click on an element like an icon, you should consult a screenshot to determine the coordinates of the element before moving the cursor.
* If you tried clicking on a program or link but it failed to load, even after waiting, try adjusting your cursor position so that the tip of the cursor visually falls on the element that you want to click.
* Make sure to click any buttons, links, icons, etc with the cursor tip in the center of the element. Don't click boxes on their edges unless asked.

Using the crosshair:
* Screenshots show a red crosshair at the current cursor position.
* After clicking, check where the crosshair appears vs your target. If it missed, adjust coordinates proportionally to the distance - start with large adjustments and refine. Avoid small incremental changes when the crosshair is far from the target (distances are often further than you expect).
* Consider display dimensions when estimating positions. E.g. if it's 90% to the bottom of the screen, the coordinates should reflect this."""

ACTIONS = [
    "key",
    "type",
    "mouse_move",
    "left_click",
    "left_click_drag",
    "right_click",
    "middle_click",
    "double_click",
    "scroll",
    "get_screenshot",
    "get_cursor_position",
]

COMPUTER_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ACTIONS, "description": ACTION_DESCRIPTION},
        "coordinate": {
            "type": "array",
            "items": {"type": "number"},
            "minItems": 2,
            "maxItems": 2,
            "description": (
                "[x, y] in the pixel space of the most recent get_screenshot PNG: "
                "0≤x<image_width, 0≤y<image_height from that tool's JSON (top-left origin). "
                "Not monitor native resolution."
            ),
        },
        "text": {"type": "string", "description": "Text to type or key command to execute"},
    },
    "required": ["action"],
    "additionalProperties": False,
}

SAVE_SCREENSHOT_DESCRIPTION = """Save a full-resolution screenshot of the screen to disk as a PNG file.
The file name is always screenshot-YYYY-MM-DD-HH-MM-SS.png (local time)."""

SAVE_SCREENSHOT_INPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "path": {
            "type": "string",
            "description": (
                "Directory where the PNG will be written. "
                "If omitted, the file is saved under src/computer_control_mcp/screenshots "
                "(package screenshots folder)."
            ),
        },
    },
    "additionalProperties": False,
}


def _json_result(data: dict[str, Any]) -> types.CallToolResult:
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=json.dumps(data, indent=2))],
        structuredContent=data,
    )


def build_server() -> Server:
    server = Server("computer-control-mcp")

    @server.list_tools()
    async def _list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="computer",
                description=TOOL_DESCRIPTION,
                inputSchema=COMPUTER_INPUT_SCHEMA,
                annotations=types.ToolAnnotations(title="Computer Control", readOnlyHint=False),
            ),
            types.Tool(
                name="save_screenshot",
                description=SAVE_SCREENSHOT_DESCRIPTION,
                inputSchema=SAVE_SCREENSHOT_INPUT_SCHEMA,
                annotations=types.ToolAnnotations(title="Save Screenshot", readOnlyHint=False),
            ),
        ]

    @server.call_tool()
    async def _call_tool(name: str, arguments: dict[str, Any] | None) -> types.CallToolResult:
        args = arguments or {}
        if name == "save_screenshot":
            try:
                raw = await asyncio.to_thread(handle_save_screenshot_sync, args)
            except Exception as e:
                logger.exception("save_screenshot tool failed")
                return types.CallToolResult(
                    content=[types.TextContent(type="text", text=str(e))],
                    isError=True,
                )
            if raw["kind"] == "json":
                return _json_result(raw["data"])
            raise RuntimeError(f"Unexpected save_screenshot result: {raw!r}")

        if name != "computer":
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=f"Unknown tool: {name}")],
                isError=True,
            )
        try:
            raw = await asyncio.to_thread(handle_computer_sync, args)
        except InvalidKeyError as e:
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=str(e))],
                isError=True,
            )
        except Exception as e:
            logger.exception("computer tool failed")
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=str(e))],
                isError=True,
            )

        if raw["kind"] == "json":
            return _json_result(raw["data"])
        if raw["kind"] == "screenshot":
            meta = raw["meta"]
            b64 = base64.b64encode(raw["png_bytes"]).decode("ascii")
            return types.CallToolResult(
                content=[
                    types.TextContent(
                        type="text",
                        text=json.dumps(meta, separators=(",", ":")),
                    ),
                    types.ImageContent(type="image", data=b64, mimeType="image/png"),
                ],
            )
        raise RuntimeError(f"Unknown result kind: {raw!r}")

    return server


async def run_stdio_async() -> None:
    server = build_server()
    init = InitializationOptions(
        server_name="computer-control-mcp",
        server_version="1.0.0",
        capabilities=server.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )
    # When stdin/stdout are pipes (Cursor, IDEs), CPython uses block-buffered stdout by default.
    # The stock stdio_server() wraps sys.stdout without line buffering, so the first JSON-RPC
    # lines (e.g. initialize response) may not reach the client until the buffer fills — the
    # client then reports "connection closed: initialize response". Match the SDK's encodings
    # but force line buffering + write-through on stdout.
    stdin_async = anyio.wrap_file(
        TextIOWrapper(sys.stdin.buffer, encoding="utf-8", errors="replace"),
    )
    stdout_async = anyio.wrap_file(
        TextIOWrapper(
            sys.stdout.buffer,
            encoding="utf-8",
            line_buffering=True,
            write_through=True,
        ),
    )
    async with stdio_server(stdin=stdin_async, stdout=stdout_async) as (read_stream, write_stream):
        await server.run(read_stream, write_stream, init)
