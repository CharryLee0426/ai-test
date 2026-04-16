# Screenshot Comparison Conventions

## Expected inputs

- Test case markdown: `tests/<stem>.md`
- Baseline screenshot: `tests/<stem>.<ext>`
- Result screenshot: `reports/<stem>.<ext>`

`<ext>` may be `png`, `jpg`, `jpeg`, or `webp`. Prefer `png` when creating new files.

## Resolution behavior

The helper script accepts either:

- a markdown path such as `tests/login-page.md`
- a bare stem such as `login-page`

It searches `tests/` for the markdown file, then looks for matching screenshots in `tests/` and `reports/`.

## Default output

The default final artifact path is:

`reports/<stem>.review.png`

Override it only when the user asks for a different location or filename.
