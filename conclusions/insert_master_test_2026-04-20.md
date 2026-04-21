# Insert Master Test Report

- Date: 2026-04-20
- Test case: `cases/test2.md`
- App: `TTEH-test_591`
- Result screenshot: `reports/insert_master.png`
- Baseline screenshot: `tests/insert_master.png`
- Review image: `reports/insert_master.review.png`
- Verdict: `PASS`

## Steps Executed

1. Used the already open `TTEH-test_591` app on the `Create with AI` screen.
2. Opened the `Effect Type` dropdown.
3. Selected `Insert Master`.
4. Saved the result screenshot as `reports/insert_master.png`.
5. Compared the result against `tests/insert_master.png` using the `compare-result-screenshot-with-baseline` workflow.
6. Returned to the home screen.

## Acceptance Criteria

Pass if the default prompt in the input field is the same as the baseline.

## Findings

- The default prompt text matches the baseline: `Create insert master effect,shoot an arrow at the target in 15 seconds`
- The selected effect type is `Insert Master` in both screenshots.
- Other visual differences, including cursor position and desktop overlays, do not affect the stated acceptance criterion.

## Notes

- The repository contains the baseline image `tests/insert_master.png` but does not contain a matching `tests/insert_master.md`. The comparison used the `insert_master` stem specified by `cases/test2.md`.
