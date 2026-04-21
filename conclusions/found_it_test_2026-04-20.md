# Found It Test Report

- Date: 2026-04-20
- Test case: `cases/test.md`
- App: `TTEH-test_591`
- Result screenshot: `reports/found_it.png`
- Baseline screenshot: `tests/found_it.png`
- Review image: `reports/found_it.review.png`
- Verdict: `PASS`

## Steps Executed

1. Opened Spotlight search with `Cmd+Space`.
2. Searched for `TTEH-test_591` and opened the app.
3. Clicked `Create with AI`.
4. Opened the `Effect Type` dropdown.
5. Selected `Found It`.
6. Saved the result screenshot as `reports/found_it.png`.
7. Compared the result against `tests/found_it.png` using the `compare-result-screenshot-with-baseline` workflow.
8. Clicked the home button to return to the create screen.

## Acceptance Criteria

Pass if the default prompt in the input field is the same as the baseline.

## Findings

- The default prompt text matches exactly: `Create a Found It game in a fruit market. Players tap to find tools within 12 seconds.`
- The selected effect type is `Found It` in both screenshots.
- Other visual differences, including cursor position, trending-topic chips, and desktop overlays, do not affect the stated acceptance criterion.

## Notes

- The repository contains the baseline image `tests/found_it.png` but does not contain a matching `tests/found_it.md`. The comparison used the `found_it` stem specified by `cases/test.md`.
