#!/usr/bin/env python3
"""Resolve baseline/result screenshot paths from a test case markdown name."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve markdown, baseline, result, and review image paths."
    )
    parser.add_argument(
        "--test-case",
        required=True,
        help="Markdown path in tests/ or a bare filename stem such as login-page.",
    )
    parser.add_argument("--tests-dir", default="tests", help="Directory containing test cases.")
    parser.add_argument(
        "--reports-dir", default="reports", help="Directory containing result screenshots."
    )
    return parser.parse_args()


def resolve_markdown(test_case: str, tests_dir: Path) -> Path:
    candidate = Path(test_case)
    if candidate.suffix == ".md" and candidate.exists():
        return candidate.resolve()

    stem = candidate.stem or candidate.name
    direct = tests_dir / f"{stem}.md"
    if direct.exists():
        return direct.resolve()

    matches = sorted(tests_dir.rglob(f"{stem}.md"))
    if not matches:
        raise FileNotFoundError(f"No markdown test case found for stem '{stem}' in {tests_dir}")
    if len(matches) > 1:
        joined = ", ".join(str(path) for path in matches)
        raise FileExistsError(f"Multiple markdown test cases found for stem '{stem}': {joined}")
    return matches[0].resolve()


def resolve_image(root: Path, stem: str, label: str) -> Path:
    for ext in IMAGE_EXTENSIONS:
        candidate = root / f"{stem}{ext}"
        if candidate.exists():
            return candidate.resolve()

    matches = []
    for ext in IMAGE_EXTENSIONS:
        matches.extend(root.rglob(f"{stem}{ext}"))

    unique = sorted({path.resolve() for path in matches})
    if not unique:
        raise FileNotFoundError(f"No {label} screenshot found for stem '{stem}' in {root}")
    if len(unique) > 1:
        joined = ", ".join(str(path) for path in unique)
        raise FileExistsError(f"Multiple {label} screenshots found for stem '{stem}': {joined}")
    return unique[0]


def main() -> int:
    args = parse_args()
    tests_dir = Path(args.tests_dir)
    reports_dir = Path(args.reports_dir)

    markdown = resolve_markdown(args.test_case, tests_dir)
    stem = markdown.stem
    baseline = resolve_image(tests_dir, stem, "baseline")
    result = resolve_image(reports_dir, stem, "result")
    review = (reports_dir / f"{stem}.review.png").resolve()

    payload = {
        "stem": stem,
        "markdown": str(markdown),
        "baseline": str(baseline),
        "result": str(result),
        "review_output": str(review),
    }
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
