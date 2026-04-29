"""Tests for MCP server wiring (tools/list, tools/call)."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from mcp.types import (
    CallToolRequest,
    CallToolRequestParams,
    ListToolsRequest,
)

from computer_control_mcp.keymap import InvalidKeyError
from computer_control_mcp.server import ACTIONS, build_server


@pytest.mark.asyncio
async def test_list_tools_registers_computer() -> None:
    server = build_server()
    r = await server.request_handlers[ListToolsRequest](None)
    tools = r.root.tools
    assert len(tools) == 3
    t0 = tools[0]
    assert t0.name == "computer"
    assert t0.annotations is not None
    assert t0.annotations.title == "Computer Control"
    assert t0.annotations.readOnlyHint is False
    assert t0.inputSchema["properties"]["action"]["enum"] == ACTIONS
    assert t0.inputSchema.get("additionalProperties") is False
    t1 = tools[1]
    assert t1.name == "save_screenshot"
    assert t1.annotations is not None
    assert t1.annotations.title == "Save Screenshot"
    assert t1.inputSchema.get("additionalProperties") is False
    assert "path" in t1.inputSchema["properties"]
    t2 = tools[2]
    assert t2.name == "save_screen_recording"
    assert t2.annotations is not None
    assert t2.annotations.title == "Save Screen Recording"
    assert t2.inputSchema.get("additionalProperties") is False
    assert "path" in t2.inputSchema["properties"]
    assert "duration_seconds" in t2.inputSchema["properties"]
    assert "fps" in t2.inputSchema["properties"]


@pytest.mark.asyncio
async def test_call_tool_unknown_name() -> None:
    server = build_server()
    await server.request_handlers[ListToolsRequest](None)
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name="nope", arguments={"action": "key", "text": "a"}),
    )
    r = await server.request_handlers[CallToolRequest](req)
    assert r.root.isError
    assert "Unknown tool" in r.root.content[0].text


@pytest.mark.asyncio
async def test_call_tool_jsonschema_rejects_missing_action() -> None:
    server = build_server()
    await server.request_handlers[ListToolsRequest](None)
    req = CallToolRequest(
        method="tools/call",
        params=CallToolRequestParams(name="computer", arguments={}),
    )
    r = await server.request_handlers[CallToolRequest](req)
    assert r.root.isError
    assert "Input validation error" in r.root.content[0].text


@pytest.mark.asyncio
async def test_call_tool_json_result() -> None:
    server = build_server()
    await server.request_handlers[ListToolsRequest](None)
    with patch("computer_control_mcp.server.handle_computer_sync", return_value={"kind": "json", "data": {"ok": True}}):
        req = CallToolRequest(
            method="tools/call",
            params=CallToolRequestParams(name="computer", arguments={"action": "left_click"}),
        )
        r = await server.request_handlers[CallToolRequest](req)
    assert not r.root.isError
    assert r.root.structuredContent == {"ok": True}
    assert '"ok": true' in r.root.content[0].text


@pytest.mark.asyncio
async def test_call_tool_save_screenshot_result() -> None:
    server = build_server()
    await server.request_handlers[ListToolsRequest](None)
    with patch(
        "computer_control_mcp.server.handle_save_screenshot_sync",
        return_value={
            "kind": "json",
            "data": {"ok": True, "path": "/tmp/screenshot-2026-04-07-13-06-05.png", "filename": "screenshot-2026-04-07-13-06-05.png"},
        },
    ):
        req = CallToolRequest(
            method="tools/call",
            params=CallToolRequestParams(name="save_screenshot", arguments={}),
        )
        r = await server.request_handlers[CallToolRequest](req)
    assert not r.root.isError
    assert r.root.structuredContent == {
        "ok": True,
        "path": "/tmp/screenshot-2026-04-07-13-06-05.png",
        "filename": "screenshot-2026-04-07-13-06-05.png",
    }


@pytest.mark.asyncio
async def test_call_tool_save_screen_recording_result() -> None:
    server = build_server()
    await server.request_handlers[ListToolsRequest](None)
    with patch(
        "computer_control_mcp.server.handle_save_screen_recording_sync",
        return_value={
            "kind": "json",
            "data": {
                "ok": True,
                "path": "/tmp/screen-recording-2026-04-28-12-00-00.mp4",
                "filename": "screen-recording-2026-04-28-12-00-00.mp4",
                "duration_seconds": 3.0,
                "fps": 2.0,
                "frames": 6,
                "frame_duration_ms": 500,
            },
        },
    ):
        req = CallToolRequest(
            method="tools/call",
            params=CallToolRequestParams(name="save_screen_recording", arguments={}),
        )
        r = await server.request_handlers[CallToolRequest](req)
    assert not r.root.isError
    assert r.root.structuredContent == {
        "ok": True,
        "path": "/tmp/screen-recording-2026-04-28-12-00-00.mp4",
        "filename": "screen-recording-2026-04-28-12-00-00.mp4",
        "duration_seconds": 3.0,
        "fps": 2.0,
        "frames": 6,
        "frame_duration_ms": 500,
    }


@pytest.mark.asyncio
async def test_call_tool_screenshot_result() -> None:
    server = build_server()
    await server.request_handlers[ListToolsRequest](None)
    fake_png = b"\x89PNG\r\n\x1a\nfake"
    with patch(
        "computer_control_mcp.server.handle_computer_sync",
        return_value={"kind": "screenshot", "meta": {"image_width": 10, "image_height": 20}, "png_bytes": fake_png},
    ):
        req = CallToolRequest(
            method="tools/call",
            params=CallToolRequestParams(name="computer", arguments={"action": "get_screenshot"}),
        )
        r = await server.request_handlers[CallToolRequest](req)
    assert not r.root.isError
    assert len(r.root.content) == 2
    assert r.root.content[1].type == "image"
    assert r.root.content[1].mimeType == "image/png"


@pytest.mark.asyncio
async def test_call_tool_invalid_key_error() -> None:
    server = build_server()
    await server.request_handlers[ListToolsRequest](None)

    def boom(_args: object) -> None:
        raise InvalidKeyError("bogus")

    with patch("computer_control_mcp.server.handle_computer_sync", side_effect=boom):
        req = CallToolRequest(
            method="tools/call",
            params=CallToolRequestParams(name="computer", arguments={"action": "key", "text": "x"}),
        )
        r = await server.request_handlers[CallToolRequest](req)
    assert r.root.isError
    assert "Invalid key" in r.root.content[0].text


@pytest.mark.asyncio
async def test_call_tool_generic_exception() -> None:
    server = build_server()
    await server.request_handlers[ListToolsRequest](None)
    with patch("computer_control_mcp.server.handle_computer_sync", side_effect=RuntimeError("display")):
        req = CallToolRequest(
            method="tools/call",
            params=CallToolRequestParams(name="computer", arguments={"action": "key", "text": "a"}),
        )
        r = await server.request_handlers[CallToolRequest](req)
    assert r.root.isError
    assert "display" in r.root.content[0].text
