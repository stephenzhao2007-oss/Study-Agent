# Product scope and current position

Snapshot: 2026-10-11. Compiled from the project conversation, supplied terminal logs, original saved code package, and later client patch. This describes the last verified state, not an inspection of every file on the developer's Windows machine.

## The intended product

Build a deployable study application that accepts course materials and assessment information, identifies what needs attention, teaches relevant material, provides active recall and practice exams, and records progress so later study decisions become better informed.

The two motivations are practical personal use and an inspectable software-engineering portfolio project. Success means a useful complete workflow with clear evidence of reliability and limitations. Generating a large volume of text is not the success metric.

The terminal is the current interface. A later UI should call existing services and consume structured outputs. Modular services make that possible, but an API, authentication, jobs, and durable hosted storage still need design and implementation.

## Full scope and status

| Component | Intended behaviour | Last verified state |
|---|---|---|
| Assessment ingestion | Extract deliverables, dates, weights, and ambiguity from course information | Earlier script processes one deliverable from text and writes SQLite; whole-syllabus multi-item ingestion is not demonstrated |
| Priority engine | Rank study needs using assessment urgency and impact; later incorporate learning evidence | Deterministic assignment scoring works; current scores are snapshots and do not refresh automatically |
| Assessment/material mapping | Know which topics and lecture pages support each assessment | Not implemented; caller selects files/pages |
| Source ingestion | Read course material while preserving notation and provenance | PDF/TXT/MD text extraction and page references implemented; OCR/diagram interpretation absent |
| Lesson planning | Group relevant material into coherent teaching units | Live five-page test succeeded; grouping and exclusions need educational review |
| Lesson generation | Teach definitions, reasoning, examples, mistakes, and recap | Live run completed; significant correctness and notation defects found in output |
| Persistence/recovery | Save reusable results, resume after failure, and track inputs | Files, checkpoints, source hashes, and optional DB run ledger implemented |
| Active recall | Present questions, hide answers, capture attempts/hints, provide feedback | Earlier generic MCQ output demo exists; interactive attempt/feedback workflow absent |
| Assessment and mastery | Evaluate reasoning and record demonstrated independent performance | Not implemented; the current priority assessor is not a student-answer grader |
| Review scheduling | Use performance and elapsed time to decide when to retest | Not implemented |
| Practice exams | Create timed, mixed practice matching confirmed scope and format | Not implemented |
| UI/API | Upload, plan, study, practise, and inspect progress from one interface | Not implemented |
| Hosted deployment | Make the application accessible with durable storage and protected credentials | Not implemented; publishing code to GitHub is a separate milestone |

## What was built in sequence

1. **Priority prototype:** extract a structured assessment record with an LLM, validate it, calculate urgency/impact in Python, and store it in SQLite.
2. **Early curriculum prototype:** query pending high-priority assignments and generate broad summaries/MCQs from course and assessment names. It printed results and set a completion flag. It did not use the actual lecture notes as its evidence.
3. **Attempted modular redesign:** separate contracts, generation, validation, and orchestration. Some advertised files were only a proposed structure. Import/entry-point problems and incomplete output handling prevented a useful integrated result.
4. **Current lesson package:** a runnable `study.py` entry point, real source extraction, conceptual planning, schema-guided generation, rendering, checkpoints, and optional database linking.
5. **Live debugging:** resolve local path mistakes, verify dependencies, handle provider limits, retain intermediate lessons, improve diagnostics, and repair missing response fields.
6. **Content review:** identify that successful execution and structured validation do not guarantee correct teaching. Content issues remain open.
7. **Documentation and version control preparation:** document this history, preserve the extra client checks as tests, and prepare exclusions/templates for GitHub.

## Original priority scoring

The supplied priority script assigns urgency out of 10 and impact out of 10. Dates one day away or overdue get urgency 10, dates at least 11 days away get 0, and intervening dates use `11 - days_left`. Assessments worth at least 20% get impact 10; smaller weights use Python's `round(weight / 2)`. Totals at least 14 produce tier 1, at least 9 produce tier 2, and lower totals produce tier 3.

Those are design choices, not a validated optimal study-allocation formula. Current limitations visible in that script include repeated sample inserts, stale stored scores, an invalid-date fallback, and missing information defaulting to low scores. They should be tracked as follow-up work rather than silently presented as solved. The existing script was intentionally not rewritten while building the lesson module.

## Two different planners

The **priority planner** decides which assessment deserves attention. The **lesson segmenter** decides how a selected set of lecture pages should be taught. Both are useful; they operate at different levels. Assessment-to-topic mapping is the missing connection between them.

## Scope of the live test

The reader extracted text from a 33-page CS245 PDF. After provider errors on the full request, the test was limited to physical pages 1-5. The model excluded pages 1 and 2 as administrative and proposed three lessons from pages 3-5. The full 33-page lecture has not been verified as successfully taught.

One lesson was saved before interruption. A resumed run reused the plan and lesson 1, generated lessons 2 and 3, repaired a missing-field response, and saved the combined output with `needs_review`. The resumed run reported three API attempts; that number is not a lifetime total or a token count.

## Next milestones

1. Publish an honest runnable prototype with a synthetic offline demo and documented limitations.
2. Compare sources, extracted text, and generated lessons; address notation, law labels, false claims, and over-fragmentation.
3. Record actual input/output tokens, retries, and timings; then choose batching and model strategies from evidence.
4. Persist course/topic/material relationships and explicitly connect them to assessments.
5. Add a small active-recall loop with attempts, hints, feedback, and stored outcomes.
6. Add broader practice exams and adaptive review scheduling.
7. Expose stable service interfaces through an API/UI, then deploy with suitable authentication and durable storage.

These milestones can evolve. Nothing requires permanently freezing every schema before starting a UI, but the current high-value work is improving the source-to-lesson workflow and its measurable quality.
