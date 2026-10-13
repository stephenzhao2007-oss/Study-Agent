# Backlog

These are proposed tasks, not completed capabilities. Convert them into GitHub issues as work begins.

1. **Correctness evaluation:** create a small, manually checked synthetic logic dataset. Evaluate generated explanations and transformation labels, including conjunction distributing over disjunction. Structural validation alone cannot do this.
2. **Notation investigation:** compare the original PDF, extracted source text, JSON lesson, and Markdown to locate where symbols are lost. Add a regression fixture after finding the cause.
3. **Lesson grouping:** assess whether related pages should form one lesson. Audit excluded-page reasons and coverage against the source. Avoid a fixed one-page/one-lesson rule.
4. **Priority module integration:** identify and include the original script; separate extraction, scoring, and persistence if useful. Recalculate scores as dates change, validate dates, and prevent duplicate ingestion. Define overdue/completed assignment handling.
5. **Measured API usage:** capture provider-reported input/output token usage and durations. Do not infer token costs from file counts or request counts alone.
6. **Larger lecture trial:** test a representative full lecture after the smaller run is reliable. Measure coverage, quality, runtime, and retries. The five-page trial does not validate all 33 pages.
7. **Continuous integration:** configure GitHub Actions to run offline tests after repository creation. No hosted CI run is claimed yet.
8. **Later learning loop:** design question generation, answer assessment, and spaced review as separate features after lesson quality is dependable.
9. **Later interface:** consider a UI after the command-line behavior and data contracts stabilize.

Success criteria should state observable behavior. For example: interrupted generation preserves completed lessons; resuming unchanged input does not call the API for those lessons; malformed output produces a clear failure or bounded repair.
