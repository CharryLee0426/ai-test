"""Shared fixtures and per-session report logging to tests/reports/."""

from __future__ import annotations

import datetime as dt
import sys
import time
from pathlib import Path
from typing import Any

import pytest

import computer_control_mcp.runtime as runtime

# TestReport does not carry a Config reference; set in pytest_configure.
_active_pytest_config: pytest.Config | None = None


def _reports_dir() -> Path:
    return Path(__file__).resolve().parent / "reports"


def _log_line(config: pytest.Config, text: str, *, end: str = "\n") -> None:
    fp: Any = getattr(config, "_session_report_fp", None)
    if fp is None or fp.closed:
        return
    fp.write(text + end)
    fp.flush()


@pytest.fixture(autouse=True)
def reset_xdotool_cache() -> None:
    runtime._xdotool_available = None
    yield
    runtime._xdotool_available = None


def pytest_configure(config: pytest.Config) -> None:
    global _active_pytest_config
    _active_pytest_config = config
    reports = _reports_dir()
    reports.mkdir(parents=True, exist_ok=True)
    # yyyy-mm-dd-hh-mm-ss.log (seconds avoid clobbering within the same clock minute)
    stamp = dt.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    log_path = reports / f"{stamp}.log"
    config._session_report_path = log_path
    config._session_report_fp = open(log_path, "w", encoding="utf-8")
    config._session_report_started = time.perf_counter()


def pytest_unconfigure(config: pytest.Config) -> None:
    global _active_pytest_config
    fp: Any = getattr(config, "_session_report_fp", None)
    if fp is not None and not fp.closed:
        fp.close()
    _active_pytest_config = None


def pytest_sessionstart(session: pytest.Session) -> None:
    config = session.config
    path = getattr(config, "_session_report_path", None)
    _log_line(config, "=" * 72)
    _log_line(config, "computer-control-mcp — pytest session")
    _log_line(config, f"started (local): {dt.datetime.now().isoformat(timespec='seconds')}")
    _log_line(config, f"report file: {path}")
    _log_line(config, f"python: {sys.version.replace(chr(10), ' ')}")
    _log_line(config, f"pytest: {pytest.__version__}")
    _log_line(config, f"cwd: {Path.cwd()}")
    _log_line(config, "=" * 72)

    tr = config.pluginmanager.get_plugin("terminalreporter")
    if tr is not None and path is not None:
        tr.write_sep("=", "test session report")
        tr.write_line(f"Writing detailed log to: {path}", bold=True)
        tr.write_line("")


def pytest_collection_finish(session: pytest.Session) -> None:
    config = session.config
    items = session.items
    _log_line(config, f"collected {len(items)} test item(s)")
    if items:
        _log_line(config, "test node ids:")
        for item in items:
            _log_line(config, f"  - {item.nodeid}")
    _log_line(config, "-" * 72)


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    config = _active_pytest_config
    if config is None:
        return

    lines: list[str] = []
    lines.append("")
    lines.append(f"[{report.when}] {report.nodeid}")
    dur = getattr(report, "duration", None)
    dur_s = f"{dur:.4f}s" if isinstance(dur, (int, float)) else "n/a"
    lines.append(f"  outcome: {report.outcome}    duration: {dur_s}")
    if report.longreprtext:
        lines.append("  ----- longrepr -----")
        for lr in report.longreprtext.rstrip().splitlines():
            lines.append(f"  {lr}")
    for title, body in getattr(report, "sections", ()) or ():
        lines.append(f"  ----- {title} -----")
        for bl in body.rstrip().splitlines():
            lines.append(f"  {bl}")
    block = "\n".join(lines) + "\n"
    _log_line(config, block.rstrip("\n"), end="\n")


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    config = session.config
    started = getattr(config, "_session_report_started", None)
    elapsed = time.perf_counter() - started if started is not None else None
    es = (
        "OK (all passed)"
        if exitstatus == 0
        else f"exit status {exitstatus} (see pytest docs for codes)"
    )
    _log_line(config, "=" * 72)
    _log_line(config, f"session finished: {es}")
    if elapsed is not None:
        _log_line(config, f"wall time (pytest process): {elapsed:.2f}s")
    _log_line(config, f"ended (local): {dt.datetime.now().isoformat(timespec='seconds')}")
    _log_line(config, "=" * 72)
