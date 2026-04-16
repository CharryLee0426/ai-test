#!/usr/bin/env python3
"""Generate an annotated screenshot review image."""

from __future__ import annotations

import argparse
import textwrap
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

PADDING = 24
GAP = 18
HEADER_HEIGHT = 88
TEXT_WIDTH = 58
BG = "#f3f4f6"
CARD = "#ffffff"
BORDER = "#d1d5db"
TEXT = "#111827"
MUTED = "#4b5563"
PASS = "#166534"
FAIL = "#991b1b"
PASS_BG = "#dcfce7"
FAIL_BG = "#fee2e2"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a composite review image.")
    parser.add_argument("--baseline", required=True, help="Path to the baseline screenshot.")
    parser.add_argument("--result", required=True, help="Path to the result screenshot.")
    parser.add_argument("--criteria", required=True, help="Natural-language pass criteria.")
    parser.add_argument(
        "--verdict",
        required=True,
        choices=("pass", "fail"),
        help="Final review verdict.",
    )
    parser.add_argument("--summary", required=True, help="One-paragraph summary of the verdict.")
    parser.add_argument(
        "--finding",
        action="append",
        default=[],
        help="A concise observation to list in the final image. Repeat for multiple findings.",
    )
    parser.add_argument("--output", required=True, help="Output path for the review image.")
    return parser.parse_args()


def get_font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []
    if bold:
        candidates.extend(
            [
                "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
                "/Library/Fonts/Arial Bold.ttf",
            ]
        )
    candidates.extend(
        [
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/Library/Fonts/Arial.ttf",
        ]
    )
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def wrap_lines(prefix: str, text: str) -> list[str]:
    wrapped = textwrap.wrap(text, width=TEXT_WIDTH) or [""]
    lines = [f"{prefix}{wrapped[0]}"]
    lines.extend(f"  {line}" for line in wrapped[1:])
    return lines


def build_notes(criteria: str, summary: str, findings: list[str]) -> list[str]:
    lines = ["Criteria:"]
    lines.extend(wrap_lines("- ", criteria))
    lines.append("")
    lines.append("Summary:")
    lines.extend(wrap_lines("- ", summary))
    if findings:
        lines.append("")
        lines.append("Findings:")
        for finding in findings:
            lines.extend(wrap_lines("- ", finding))
    return lines


def labeled_panel(image: Image.Image, label: str, font: ImageFont.ImageFont) -> Image.Image:
    width, height = image.size
    panel = Image.new("RGB", (width, height + 40), CARD)
    draw = ImageDraw.Draw(panel)
    panel.paste(image, (0, 40))
    draw.rectangle((0, 0, width - 1, height + 39), outline=BORDER, width=1)
    draw.text((12, 10), label, fill=TEXT, font=font)
    return panel


def make_diff(baseline: Image.Image, result: Image.Image) -> Image.Image | None:
    if baseline.size != result.size:
        return None
    return ImageChops.difference(baseline, result)


def main() -> int:
    args = parse_args()
    baseline_path = Path(args.baseline)
    result_path = Path(args.result)
    output_path = Path(args.output)

    baseline = Image.open(baseline_path).convert("RGB")
    result = Image.open(result_path).convert("RGB")
    diff = make_diff(baseline, result)

    title_font = get_font(28, bold=True)
    section_font = get_font(20, bold=True)
    body_font = get_font(18)
    small_font = get_font(16)

    panels = [
        labeled_panel(baseline, f"Baseline: {baseline_path.name}", section_font),
        labeled_panel(result, f"Result: {result_path.name}", section_font),
    ]
    if diff is not None:
        panels.append(labeled_panel(diff, "Pixel Diff", section_font))

    panel_height = max(panel.height for panel in panels)
    panel_width = sum(panel.width for panel in panels) + GAP * (len(panels) - 1)
    canvas_width = panel_width + PADDING * 2

    notes = build_notes(args.criteria, args.summary, args.finding)
    line_height = 28
    notes_height = 48 + line_height * len(notes)

    canvas_height = PADDING * 2 + HEADER_HEIGHT + panel_height + GAP + notes_height
    image = Image.new("RGB", (canvas_width, canvas_height), BG)
    draw = ImageDraw.Draw(image)

    verdict_fill = PASS_BG if args.verdict == "pass" else FAIL_BG
    verdict_text = PASS if args.verdict == "pass" else FAIL

    header_box = (PADDING, PADDING, canvas_width - PADDING, PADDING + HEADER_HEIGHT)
    draw.rounded_rectangle(header_box, radius=18, fill=CARD, outline=BORDER, width=1)
    draw.text((PADDING + 20, PADDING + 18), "Screenshot Review", fill=TEXT, font=title_font)
    badge_box = (canvas_width - 190, PADDING + 18, canvas_width - PADDING - 20, PADDING + 58)
    draw.rounded_rectangle(badge_box, radius=18, fill=verdict_fill)
    draw.text((badge_box[0] + 24, badge_box[1] + 9), args.verdict.upper(), fill=verdict_text, font=section_font)

    x = PADDING
    y = PADDING + HEADER_HEIGHT + 20
    for panel in panels:
        image.paste(panel, (x, y))
        x += panel.width + GAP

    notes_top = y + panel_height + GAP
    draw.rounded_rectangle(
        (PADDING, notes_top, canvas_width - PADDING, canvas_height - PADDING),
        radius=18,
        fill=CARD,
        outline=BORDER,
        width=1,
    )
    draw.text((PADDING + 20, notes_top + 16), "LLM Review Notes", fill=TEXT, font=section_font)
    text_y = notes_top + 52
    for line in notes:
        draw.text((PADDING + 20, text_y), line, fill=MUTED if line.endswith(":") else TEXT, font=body_font if not line.endswith(":") else small_font)
        text_y += line_height

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
