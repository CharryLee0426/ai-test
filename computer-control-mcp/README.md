# computer-control-mcp

A **Model Context Protocol (MCP)** server that exposes a **`computer`** tool plus companion save helpers so LLM clients can drive the desktop: keyboard, mouse, scrolling, screenshots, and short saved screen recordings. The tool’s contract (actions, parameters, coordinate scaling, screenshot metadata) is aligned with **[domdomegg/computer-use-mcp](https://github.com/domdomegg/computer-use-mcp)**; this implementation uses **Python**, **PyAutoGUI**, and **Pillow** instead of Node and nut.js.

> **Warning:** This grants full GUI control to whatever model or client calls the tool. Use only on machines you trust, preferably under supervision or in an isolated account, and be aware of prompt-injection risks.

## Tech stack

| Layer | Technology |
|--------|------------|
| Protocol | [MCP](https://modelcontextprotocol.io/) over **stdio** (`mcp` Python SDK) |
| Automation | **PyAutoGUI** (mouse, keyboard, basic scrolling) |
| Images | **Pillow** (screenshots, resize, PNG export, on-image crosshair) |
| Video encoding | **ffmpeg** (MP4 assembly for saved screen recordings) |
| Linux typing | Optional **`xdotool type`** when available (layout-friendly, same idea as upstream) |
| macOS screenshot fallback | **`screencapture`** if `pyautogui.screenshot()` fails |
| Packaging | **setuptools** + `pyproject.toml` (Python ≥ 3.11) |
| Tests | **pytest**, **pytest-asyncio** (optional `[dev]` extra) |

## Architecture

```text
┌─────────────────┐     stdio (JSON-RPC)      ┌──────────────────────────────┐
│  MCP client     │ ◄──────────────────────────► │  computer_control_mcp        │
│  (Cursor, etc.) │                            │  ┌────────────────────────┐  │
└─────────────────┘                            │  │ server.py              │  │
                                               │  │  • list_tools → tools   │  │
                                               │  │  • call_tool → dispatch │  │
                                               │  └──────────┬─────────────┘  │
                                               │             │                 │
                                               │  ┌──────────▼─────────────┐  │
                                               │  │ runtime.py             │  │
                                               │  │  • handle_computer_sync│  │
                                               │  │  • PyAutoGUI + Pillow  │  │
                                               │  └──────────┬─────────────┘  │
                                               │             │                 │
                                               │  ┌──────────▼─────────────┐  │
                                               │  │ keymap.py              │  │
                                               │  │  • xdotool-style keys  │  │
                                               │  └────────────────────────┘  │
                                               └──────────────────────────────┘
                                                            │
                                                            ▼
                                               OS display / input APIs
```

- **`server.py`** — Registers the MCP server, defines the `computer`, `save_screenshot`, and `save_screen_recording` tools (JSON Schema, descriptions, annotations), validates inputs, and maps results to `CallToolResult`.
- **`runtime.py`** — Implements all `action` branches (`key`, `type`, mouse operations, `scroll`, `get_screenshot`, `get_cursor_position`), coordinate scaling for vision APIs, screenshot downsampling, red crosshair overlay, PNG saving, and MP4 screen-recording capture via `ffmpeg`.
- **`keymap.py`** — Parses `+`-separated key names (same vocabulary as upstream) into PyAutoGUI key names; maps platform meta/super keys sensibly (e.g. Command on macOS).
- **`__main__.py`** — Starts the **stdio** transport so clients can spawn the process and speak MCP over stdin/stdout.

There is **no HTTP transport** in this port (the upstream project can optionally use HTTP); everything runs as a single stdio subprocess.

## Tools

- **`computer`**: interactive desktop control plus inline screenshots.
- **`save_screenshot`**: saves a full-resolution PNG under an optional directory.
- **`save_screen_recording`**: saves a short full-resolution MP4 recording. Requires `ffmpeg` on `PATH`. Optional inputs:
  - `path`: output directory.
  - `duration_seconds`: approximate recording length, default `3`, max `30`.
  - `fps`: capture rate, default `2`, max `10`.

## Install

Clone the repository first (venv and Conda both assume you are in the project root):

```bash
git clone <your-repo-url> computer-control-mcp
cd computer-control-mcp
```

### Using Conda (Miniconda / Anaconda / Mambaforge)

Create an environment with **Python ≥ 3.11**, activate it, then install this package with **pip** (the project is distributed via `pyproject.toml`; Conda does not ship a `conda-forge` recipe for it by default):

```bash
conda create -n computer-control-mcp python=3.12 -y
conda activate computer-control-mcp
pip install -e .
```

With test dependencies:

```bash
pip install -e ".[dev]"
```

To use **mamba** instead of `conda` for faster solving, replace `conda create` with `mamba create` (same arguments).

**Windows (Command Prompt / PowerShell):** use `conda activate computer-control-mcp` after `conda init` for your shell.

### Using venv + pip

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

With test dependencies:

```bash
pip install -e ".[dev]"
```

### Editable vs non-editable

- `pip install -e .` — Editable install: code changes under `src/` are picked up immediately.
- `pip install .` — Regular install: copies the package into the environment.

## Run

**Activate your environment** (`conda activate …` or `source .venv/bin/activate`), then:

### As a module

```bash
python -m computer_control_mcp
```

### Console script (after install)

```bash
computer-control-mcp
```

The process waits on **stdin** for MCP messages; it is meant to be launched by an MCP-capable host, not run interactively in a terminal for normal use.

### Cursor (example `mcp.json`)

Point `command` at the **Python executable inside the environment** that has this package installed.

**Conda** (after `conda activate computer-control-mcp`, run `which python` or `where python` to copy the real path):

```json
{
  "mcpServers": {
    "computer-control": {
      "command": "/absolute/path/to/miniconda3/envs/computer-control-mcp/bin/python",
      "args": ["-m", "computer_control_mcp"]
    }
  }
}
```

**venv:**

```json
{
  "mcpServers": {
    "computer-control": {
      "command": "/absolute/path/to/computer-control-mcp/.venv/bin/python",
      "args": ["-m", "computer_control_mcp"]
    }
  }
}
```

On Windows, use paths such as `C:\\Users\\you\\miniconda3\\envs\\computer-control-mcp\\python.exe`.

### Troubleshooting

**`handshaking with MCP server failed: connection closed: initialize response` (Cursor / other stdio clients)**  
The host runs the server with **pipes** instead of a TTY, so Python’s stdout can be **fully block-buffered**. The MCP SDK’s default `stdio_server()` did not enable line buffering, which delayed the first JSON-RPC lines until the buffer filled; the client then closed the connection during initialization. This project’s `run_stdio_async()` wraps `stdout` with **`line_buffering=True`** and **`write_through=True`** so each response line is flushed immediately. Update to the latest code from this repo if you still see this error.

You can still add **`-u`** (unbuffered) in `args` if your client supports it, e.g. `["-u", "-m", "computer_control_mcp"]`, but it should no longer be required for a correct handshake.

### Permissions

- **macOS:** Grant **Accessibility** (and related screen/input permissions) to the terminal or app that launches Python, or automation will fail.
- **Linux:** An X11 session (and `DISPLAY`) is typically required; `xdotool` is optional but improves `type` with non-US layouts when installed.

## Build

This is a standard Python package. There is no separate compile step.

### Source / wheel artifacts (for distribution)

Install the build frontend once (inside your venv or Conda env):

```bash
pip install build
```

From the repository root:

```bash
python -m build
```

This creates `dist/*.tar.gz` (sdist) and `dist/*.whl` under `dist/`. Upload or install with `pip install dist/computer_control_mcp-*.whl`.

### Tests

With your environment activated:

```bash
pip install -e ".[dev]"
pytest
```

Pytest is configured in `pyproject.toml` for **verbose output** (`-vv`), **long tracebacks**, **slowest 10 durations**, **INFO-level live logging** during tests, and a short **summary of skips/xfails** (`-ra`). Each run also appends a structured session report under:

`tests/reports/YYYY-MM-DD-HH-MM-SS.log`

(The exact filename is printed at the start of the run.) Log files are ignored by Git via `tests/reports/.gitignore`.

## Relationship to computer-use-mcp

Feature parity targets the upstream **`computer`** tool (actions and schema). Minor differences remain (e.g. scroll units are mapped to PyAutoGUI’s wheel steps; Unicode typing may differ when `xdotool` is not used). See the upstream project for original behavior and safety discussion: [github.com/domdomegg/computer-use-mcp](https://github.com/domdomegg/computer-use-mcp).

## Known Issue
This MCP doesn't work well on claude code. It is because claude code's auto downsample for images which larger than 1,600 tokens. Please refer to this section [https://docs.anthropic.com/en/docs/build-with-claude/vision#evaluate-image-size](https://docs.anthropic.com/en/docs/build-with-claude/vision#evaluate-image-size). Even though the mcp can make sure uploaded screenshot size is under the automatically downsample limit, claude code still can't handle them correctly. But it works well on other agents such as cursor or codex.

## License

Add a `LICENSE` file if you publish the project; the upstream inspiration uses MIT.
