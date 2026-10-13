# Retrospective debugging log

Prepared 2026-10-11 from the conversation, supplied code, saved package, and terminal output. Most observed incidents occurred on 2026-10-08; retesting/setup discussion continued on 2026-10-11. These entries are retrospective notes, not backdated Git commits or GitHub issue numbers.

**Status meanings:** Resolved = the observed failure has confirming evidence of resolution. Mitigated = handling improved but the condition can recur. Open = not yet fixed or not yet verified. Static finding = identified by reviewing code rather than by a reproduced runtime trace.

## Setup and execution

| ID | Symptom and evidence | Cause | Change or resolution | Status |
|---|---|---|---|---|
| D01 | `requirements.txt` and `study.py` not found from the user's home directory | CMD's working directory was not the extracted project | Navigate to the folder containing both files or open CMD from Explorer there; demo later ran | Resolved for observed setup |
| D02 | Explorer showed compressed-size/ratio columns; extraction resulted in nested folders | ZIP already contained a project folder and Explorer was still showing archive contents in one screenshot | Extract the archive and open the inner actual project folder | Resolved for observed setup |
| D03 | Original `ModuleNotFoundError: lesson_types`; silent runs of `lesson_types.py`/`lesson_generator.py`; misspelled `lesson_serivce.py` | Filename mismatch, definitions-only modules, and entry-point confusion | Package-relative imports and a single root `study.py` command; no-argument run shows help | Resolved in new package and demonstrated locally |
| D04 | CMD syntax error after pasting `C:\Users\...>`; `unrecognized arguments: study.py tasks` | Shell prompt copied as a command, or command pasted twice on one line | Paste only one command; the subsequent tasks command returned the expected assessment | Resolved for observed commands |
| D05 | Source file not found for `lecture.pdf` | File was not at the supplied path/name | Place/select the actual file; later reader extracted all 33 physical pages | Resolved for observed input |
| D06 | Replacement client copy command could not find the downloaded file | Expected Downloads path did not locate the file; exact actual download path was not established | Browser's Show in folder, then manually replace the client inside `curriculum_engine` | Resolved operationally: subsequent run showed the new waiting behaviour |

These setup issues belong in troubleshooting documentation. They are not all application defects, but repeated confusion exposed usability problems that the entry point and instructions needed to address.

## Model integration and output persistence

### D07 — Provider/model configuration during the earlier prototype

- **Evidence:** The prior project history showed failed provider/model attempts, including an earlier Gemini HTTP 503, before switching to the user's working Groq configuration.
- **Diagnosis:** Provider availability and configuration were both involved across attempts. Do not assign one root cause to every earlier error.
- **Change:** Current package reuses `GROQ_API_KEY`, LiteLLM, and the working Groq model string rather than silently selecting another model.
- **Verification:** The user later generated a real lecture plan and lessons using that connection.
- **Status:** Working connection demonstrated; universal model access and provider uptime are not guaranteed.

### D08 — JSON instructions named a schema without showing it

- **Evidence:** Static review of the initial generated `lesson_generator.py` found a prompt requesting the `LessonContent` schema by name without supplying its fields.
- **Cause:** A model cannot infer the application's exact contract reliably from a Python class name.
- **Change:** The shared client inserts `schema.model_json_schema()` into the instructions and validates returned JSON with Pydantic. It permits one corrected response.
- **Verification:** Regression test checks the schema is sent and an invalid response can be repaired. Live missing-field correction is recorded in D12.
- **Status:** Structural contract handling implemented. Schema compliance does not prove factual accuracy.

### D09 — Initial generator did not load real sources or save complete lessons

- **Evidence:** Earlier curriculum code generated from course/assessment names, printed brief content, and set a database flag. Later proposed source-loading/segmentation files were named but not implemented. Demo printing omitted multiple content fields.
- **Cause:** Demonstration snippets had not become a complete integrated application.
- **Change:** Implement source extraction and planning, render every content field, save individual and combined Markdown/JSON, and provide visible output paths.
- **Verification:** Offline regression tests exercise the complete pipeline; user's live run saved all three lessons.
- **Status:** Execution/persistence resolved for the observed run. Source-faithful content remains under evaluation.

### D10 — Repeated HTTP 429 and ineffective short retries

- **Evidence:** Full-material planning initially failed with HTTP 429. A smaller five-page run later planned successfully and saved lesson 1, then hit HTTP 429 while generating lesson 2. Original retry delays were 3 and 6 seconds.
- **Diagnosis:** The provider reported rate limiting. Exact quota dimension and the original full-request size issue were not captured, so neither daily exhaustion nor a particular token threshold was proven from those logs.
- **Change:** Test a smaller selection; patch the client to space live successful calls by 65 seconds, use `Retry-After` when available, wait visibly in chunks, and stop rather than retry early when the requested wait exceeds the automatic threshold.
- **Verification:** User's resumed run showed 65/35/5-second countdowns and completed. Tests cover retry headers, long waits, and pacing.
- **Status:** Mitigated. Single oversized requests, account-wide use by other clients, and longer-period quotas can still fail. Spacing does not reduce token consumption or establish a dollar budget.

### D11 — HTTP 400 appeared after the 429s but diagnostics hid the cause

- **Evidence:** The final original error was `BadRequestError (HTTP 400)` with only generic advice.
- **Cause:** The client intentionally suppressed provider bodies but removed too much diagnostic information.
- **Change:** Extract only structured provider error code/message, redact credential-shaped values and the known key, avoid dumping raw request/failed-generation fields, and recognize `json_validate_failed` as eligible for bounded correction.
- **Verification:** Simulated 429-then-400 test exposes the specific supplied reason; redaction and bounded JSON repair are tested. The next observed live run completed.
- **Status:** Diagnostic defect addressed. The exact cause of that historical HTTP 400 is still unknown; do not claim it was definitely invalid JSON or definitely a rate limit.

### D12 — Lesson 3 omitted required fields

- **Evidence:** Live validation reported missing `method_guide`, `recap`, and `unresolved_source_problems`.
- **Cause:** Model output did not conform to the full schema. Token truncation was not established by this message.
- **Change:** Existing Pydantic checks rejected it, then the bounded correction path requested a complete response after pacing.
- **Verification:** Corrected lesson saved and the run printed `DONE: 3 lesson(s)`.
- **Status:** Observed incident recovered automatically. Recurrence remains possible; retain validation and correction.

### D13 — Interrupted run risked losing work / legacy flag hid provenance

- **Evidence:** Earlier code marked an assignment's lessons generated after printing output. New live run stopped after saving lesson 1.
- **Change:** Save each lesson immediately with checkpoints; on rerun validate/reuse saved plan and lessons. Record specific linked runs separately rather than treating the legacy flag as proof of complete assessment coverage.
- **Verification:** User log shows plan and lesson 1 reused, then only remaining lessons generated. Tests cover interruption, zero-call reuse, file reconstruction, and preservation of old assignment fields.
- **Status:** Observed recovery works. Whole-exam coverage mapping and concurrent-job handling are still absent.

### D14 — Original bracket validator produced misleading results

- **Evidence:** Static review found a regex treating arbitrary `[...]` or `<...>` as bad placeholders and a `missing_symbols` list that was never populated.
- **Cause:** Broad text patterns were presented as stronger validation than implemented.
- **Change:** Use a narrow authoring-placeholder check and validate structured source IDs. Do not claim to verify all symbol definitions or mathematical correctness.
- **Verification:** Tests accept `a[0]`, `[0, 1]`, and `std::vector<T>` while rejecting unknown source IDs.
- **Status:** Specific false-positive design corrected; semantic validation remains open.

## Content and evidence problems still open

### D15 — Mathematical errors despite structurally valid output

- **Evidence:** Human review of the supplied generated text found a warning falsely saying conjunction does not distribute over disjunction. A worked example reached the correct result but labeled factoring/complement reasoning as absorption. CNF/DNF canonical-form claims were overstated. A syntax explanation replaced an informal symbol with another symbol whose admissibility was not established.
- **Diagnosis:** Schema/reference membership validation cannot validate mathematical propositions, proof steps, or notation conventions.
- **Next work:** Compare against source slides, create small independently checked content cases, tighten instructions, and use deterministic checks for supported problem types. Model-based review may help but is not proof of correctness.
- **Status:** Open. No fix to these teaching defects was implemented in the documented generation package.

### D16 — Damaged logical notation

- **Evidence:** Lesson 2 included strings such as `pland q` and `Alandlnot A`.
- **Diagnosis:** Could be source extraction, generation/escaping, or another transformation. Original PDF, extracted `sources.json`, and raw structured lesson output have not yet been compared in this review.
- **Next work:** Locate the first stage at which symbols differ; fix that stage instead of blindly replacing every occurrence of words like `land`.
- **Status:** Open; exact origin unverified.

### D17 — Over-fragmentation and page exclusions

- **Evidence:** Five selected pages became three lessons, each using one substantive page; two pages were labeled administrative.
- **Diagnosis:** Potentially unnecessary lesson splitting and repeated teaching. It is not yet established that the excluded pages were actually administrative.
- **Next work:** Read the actual pages and plan together; choose coherent objective-level units and preserve prerequisite context.
- **Status:** Open. More lessons do not automatically mean more useful learning.

### D18 — Ambiguous success/review status

- **Evidence:** The run completed as `needs_review`; the notes included the generic PDF warning and a short-explanation warning.
- **Diagnosis:** Status combines pipeline completion with review notes. `complete` or `needs_review` does not mean source coverage is correct or the student has mastered the material.
- **Next work:** Present generation status, source-extraction issues, and content-review status separately in a future interface.
- **Status:** Explained and documented; status design not yet redesigned.

### D19 — Credential appeared in an earlier conversation export

- **Evidence:** The supplied project-history document contained a key; the current pasted priority script uses an environment variable.
- **Action:** Exclude private exports and credentials from Git. Revoke the exposed key if still active. Replacement scripts use environment lookup.
- **Status:** Code handling improved. Revocation has not been verified and must not be recorded as completed without evidence.

### D20 — Documentation/test history could overstate reproducibility

- **Evidence:** The first ZIP contains 23 tests; six later client-patch checks were run from an inline script. The claimed total of 29 described those combined checks, not 29 packaged tests.
- **Change in this kit:** Retain those six checks in `tests/test_rate_limits.py` so the normal discovery command can reproduce the combined suite against the patched client.
- **Status:** Addressed in the documentation kit. The original ZIP remains an earlier artifact with its original code and test count.

## Further limitations identified in review, not demonstrated incidents

- Original priority scores are stored at ingestion time; `tasks` does not recalculate them.
- Original ingestion handles one deliverable and repeatedly inserts its sample if rerun as supplied.
- The five-page standalone CS245 run did not update the unrelated CS246 assignment database.
- Per-invocation API attempt counts are not cumulative tokens, charges, or a persistent usage ledger.
- `--regenerate` deliberately bypasses reuse by creating a separate run.
- Checkpoint identity includes source content and prompt/settings/version metadata, but developers must deliberately update versioning when behaviour changes.
- No content benchmark, actual end-to-end learning outcome, multi-user test, or full-lecture success claim has been established.

## Template for future entries

```text
Date and issue link:
Symptom / expected behaviour:
Minimal reproduction:
Environment and commit:
Observed evidence:
Confirmed cause (or explicitly labeled hypothesis):
Change:
Verification and regression test:
Remaining uncertainty:
Status:
```

Keep logs small and redacted. Link to a GitHub issue and the real fix commit once they exist; do not invent IDs for this retrospective history.
