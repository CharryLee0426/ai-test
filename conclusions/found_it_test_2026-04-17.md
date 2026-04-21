# Found It Test Report

- Date: 2026-04-17
- Test case: `cases/test.md`
- App: `TTEH-test_591`
- Result screenshot: `reports/found_it.png`
- Baseline screenshot: `tests/found_it.png`
- Review image: `reports/found_it.review.png`
- Verdict: `PASS`

## Steps Executed

1. Opened `TTEH-test_591`.
2. Clicked `Create with AI`.
3. Opened the `Effect Type` dropdown.
4. Selected `Found It`.
5. Saved the result screenshot as `reports/found_it.png`.
6. Compared the result against `tests/found_it.png` using the `compare-result-screenshot-with-baseline` workflow.

## Acceptance Criteria

Pass if the default prompt in the input field is the same as the baseline.

## Findings

- The default prompt text matches exactly: `Create a Found It game in a fruit market. Players tap to find tools within 12 seconds.`
- The selected effect type is `Found It` in both screenshots.
- Other visual differences, including desktop notifications and trending-topic chips, do not affect the stated acceptance criterion.
