"""Entry point: `python -m computer_control_mcp` or `computer-control-mcp` console script."""

from __future__ import annotations

import asyncio
import logging
import sys


def main() -> None:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    from computer_control_mcp.server import run_stdio_async

    asyncio.run(run_stdio_async())


if __name__ == "__main__":
    main()
