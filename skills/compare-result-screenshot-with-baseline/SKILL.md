---
name: compare-result-screenshot-with-baseline
description: Compare a result screenshot in `reports/` against a baseline screenshot in `tests/` by matching the test case markdown filename stem, applying user-provided pass/fail criteria, and generating a final annotated review image. Use when Codex needs to review UI or visual test output, decide whether a screenshot passes based on a natural-language criterion, and save a composite artifact that combines the screenshots with the LLM verdict.
---

# Compare Result Screenshot With Baseline

Compare a baseline image from `tests/` with a result image from `reports/`, judge the result against the user's acceptance criteria, and save a final review image into `reports/`.

## Workflow

1. Identify the test case markdown file in `tests/` and derive its stem.
2. Resolve the paired screenshots using the same stem:
   - baseline screenshot: `tests/<stem>.<image-ext>`
   - result screenshot: `reports/<stem>.<image-ext>`
3. Read the user's pass criteria carefully. Treat the criteria as the source of truth for what matters.
4. Inspect both images before deciding. Use `view_image` for local files when you need a direct visual read.
5. Make an explicit pass/fail call and write short findings:
   - what matches the baseline
   - what differs
   - why the result passes or fails under the given criteria
6. Generate a final review image in `reports/` that includes:
   - the baseline screenshot
   - the result screenshot
   - a diff panel when the dimensions match
   - the criteria
   - the verdict
   - concise notes from the review

## File Conventions

- The markdown test case lives in `tests/` and determines the filename stem.
- The baseline screenshot must use the same stem as the markdown file and live in `tests/`.
- The result screenshot must use the same stem and live in `reports/`.
- Prefer `.png`. The helper script also accepts `.jpg`, `.jpeg`, and `.webp`.
- Save the final review image as `reports/<stem>.review.png` unless the user asks for a different output path.

## Commands

Resolve the expected files first:

```bash
python3 skills/compare-result-screenshot-with-baseline/scripts/resolve_screenshot_paths.py \
  --test-case tests/<case>.md
```

After reviewing the images, generate the final review image:

```bash
python3 skills/compare-result-screenshot-with-baseline/scripts/generate_review_image.py \
  --baseline tests/<case>.png \
  --result reports/<case>.png \
  --criteria "User-provided pass criteria" \
  --verdict pass \
  --summary "Short explanation of why the result passed." \
  --output reports/<case>.review.png
```

Add `--finding` multiple times when there are several observations.

## Review Rules

- Do not infer stricter standards than the user provided.
- If the criteria are ambiguous, state the assumption you used in the verdict notes.
- Call out material visual regressions plainly: layout shifts, missing elements, clipped content, wrong text, broken styling, or state mismatches.
- If the screenshots differ only in ways the user explicitly allowed, mark the result as pass.
- If you cannot find one of the required files, stop and report the missing path instead of inventing a verdict.

## Resources

- Read [references/file-conventions.md](references/file-conventions.md) when the path mapping or output naming needs clarification.
- Use `scripts/resolve_screenshot_paths.py` to locate the markdown, baseline, result, and default review image path from a single test case input.
- Use `scripts/generate_review_image.py` to build the final composite image after the LLM review is complete.
