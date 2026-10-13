# Study Agent

A modular Python study-workflow prototype that turns selected lecture material into saved, source-referenced lessons. The wider project aims to connect assessment priorities, teaching, active recall, practice exams, and progress tracking in one application.

**Status: terminal prototype.** A live five-page lecture test produced three saved lessons and recovered from an interrupted run. Human review identified content errors and damaged notation, so lesson accuracy remains under evaluation. This is not yet a deployed web app or a validated tutoring product.

## What works today

- Load PDF, UTF-8 text, or Markdown with stable source-page identifiers.
- Organize selected material into conceptual lesson units and record excluded pages.
- Generate explanations, definitions, worked examples, common mistakes, and recaps.
- Validate response structure and source-ID membership with Pydantic and Python.
- Save readable Markdown and structured JSON, with checkpoints for interrupted runs.
- Reuse unchanged-input checkpoints instead of generating the same lessons again.
- Read an existing SQLite assignments table and optionally record linked lesson runs.
- Space live model calls, respect provider retry timing, and bound correction attempts.
- Run an explicitly prerecorded offline demo without an API key.

The earlier priority-extraction script is a separate working prototype. It extracts one deliverable, computes urgency/impact, and writes `curriculum.db`. The lesson package reads its schema; automatic assessment-to-lecture mapping has not been implemented. The original priority script is not included in the initial lesson-package ZIP.

## Quick start

From the project directory on Windows CMD:

```bat
py -m pip install -r requirements.txt
py study.py demo
```

The demo uses bundled illustrative notes and prerecorded responses. It prints the output path and makes no model request.

For live generation, set `GROQ_API_KEY` in your environment, then run:

```bat
py study.py doctor
py study.py generate --course "CS 245" --source "lecture.pdf" --pages 1-5 --max-output-tokens 3000
```

Supply your own permitted lecture material. The sample PDF is not part of the repository. Windows may hide filename extensions.

The default model is `groq/openai/gpt-oss-20b`, accessed through LiteLLM. `STUDY_MODEL` overrides the model string. Availability and quotas depend on the provider/account; the code does not change billing settings. The current client conservatively spaces live requests by 65 seconds after successful calls, so visible waits are expected.

To connect an existing priority database:

```bat
py study.py tasks --db "%USERPROFILE%\curriculum.db"
py study.py generate --db "%USERPROFILE%\curriculum.db" --assignment-id 1 --source "lecture.pdf"
```

Use the correct assignment ID and matching course material. Standalone `--course` runs do not update the assignment database.

## Architecture

The command interface calls a Python orchestration service. Source extraction and database/file operations use ordinary Python. The conceptual planner and lesson generator call the model through a shared client. Modules are units of code responsibility, not independent running agents.

See the [architecture and file map](docs/architecture.md) for the exact flow and comparison with the original scripts.

## Tests and evidence

```bat
py -m unittest discover -s tests -v
```

The original package contains 23 regression tests. `tests/test_rate_limits.py`, supplied with this documentation kit, retains six additional client checks previously run separately, bringing the suite to 29 when used with the patched client. Tests simulate model responses and do not require a live key.

These tests cover pipeline execution and failure handling, not the correctness of generated teaching. Live generation was demonstrated in a user-reported Windows run with Python 3.14.5, Pydantic 2.13.4, LiteLLM 1.100.1, and pypdf 6.19.0. This is one observed environment, not a broad compatibility guarantee. A GitHub-hosted test run has not yet been configured or claimed.

## Known limitations

- The PDF reader extracts text; it does not interpret diagrams or handwriting, and mathematical notation can be damaged.
- A source ID verifies which page was supplied, not whether that page supports a claim.
- Generated output has contained false mathematical statements and incorrect law labels. Human content review is required.
- Lesson grouping can be too fine-grained. The observed five-page test excluded two pages and made three one-page lessons; the exclusions still need comparison with the original slides.
- Rate limits are mitigated, not eliminated. Long lectures may need smaller selections. No automatic token-aware batching or usage-cost ledger exists yet.
- `needs_review` includes a general PDF extraction warning and is not a measure of mastery. `complete` refers to artifact generation, not educational correctness.
- Active-recall interaction, grading, mastery/review scheduling, practice exams, UI, and hosting remain planned work.

## Documentation

- [Product scope and milestones](docs/project_scope.md)
- [Architecture, file responsibilities, and data flow](docs/architecture.md)
- [Retrospective debugging log](docs/debugging.md)
- [Git/GitHub publishing and daily workflow](docs/development.md)
- [Candidate issues and acceptance criteria](docs/backlog.md)
- [Terminal commands](docs/running.md)

## Development approach

This project has been developed with AI assistance for implementation, explanations, and debugging. Development records distinguish observed failures, suspected causes, verified changes, and open questions. The history documented before the first Git commit is retrospective; it is not fabricated commit history.
