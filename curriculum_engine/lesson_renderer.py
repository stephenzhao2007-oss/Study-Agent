"""Render every lesson field as readable Markdown, including verifiable page references."""

from .lesson_context_builder import page_index


def render_lesson(lesson, documents):
    pages = page_index(documents)
    content = lesson.content

    def citations(ids):
        return "Sources: " + "; ".join(
            f"{pages[ref].document_name}, page/section {pages[ref].page_number} (`{ref}`)"
            for ref in dict.fromkeys(ids)
        )

    lines = [f"# {lesson.title}", f"Course: {lesson.course_id} | Lesson ID: {lesson.lesson_id}",
             "## Learning objectives", "\n".join(f"- {item}" for item in content.learning_objectives),
             "## Prerequisites", content.prerequisites, "## Big picture", content.big_picture.markdown,
             citations(content.big_picture.source_ids), "## Definitions and notation"]
    if content.definitions_and_notation:
        for definition in content.definitions_and_notation:
            lines += [f"**{definition.term_or_symbol}**", definition.explanation, citations(definition.source_ids)]
    else:
        lines += ["No additional notation is introduced in this lesson."]
    lines += ["## Explanation", content.core_explanation.markdown, citations(content.core_explanation.source_ids),
              "## Worked examples"]
    for index, example in enumerate(content.worked_examples, 1):
        origin = "Source example" if example.origin == "source" else "Generated supplementary example"
        lines += [f"### {index}. {example.title}", f"Origin: {origin}", "**Problem**", example.problem,
                  "**Solution**", example.solution, citations(example.source_ids)]
    lines += ["## Common mistakes", "\n".join(f"- {item}" for item in content.common_mistakes),
              "## Method guide", content.method_guide or "This lesson does not require a separate procedural guide.",
              "## Recap", content.recap]
    if lesson.validation.warnings:
        lines += ["## Review notes", "\n".join(f"- {note}" for note in lesson.validation.warnings)]
    lines += ["## Source references", "\n".join(
        f"- {pages[ref].document_name}, page/section {pages[ref].page_number}; source ID `{ref}`."
        for ref in lesson.unit.source_ids
    )]
    return "\n\n".join(lines) + "\n"


def render_bundle(bundle):
    lines = [f"# {bundle.course_id} — Lecture lessons", f"Status: {bundle.status}"]
    if bundle.model == "offline-fixture":
        lines += ["> OFFLINE DEMO: These are prerecorded example lessons. No AI request was made."]
    lines += [bundle.plan.overview,
              "Content is generated study material, not an official course handout. Structural checks do not "
              "verify every mathematical claim, proof, code example, or objective's coverage."]
    if bundle.warnings:
        lines += ["## Source and review notes", "\n".join(f"- {note}" for note in bundle.warnings)]
    if bundle.plan.excluded_sources:
        lines += ["## Excluded source pages", "\n".join(
            f"- `{item.source_id}`: {item.reason}" for item in bundle.plan.excluded_sources
        )]
    for lesson in bundle.lessons:
        lines += ["---", render_lesson(lesson, bundle.sources)]
    lines += ["## Source versions", "\n".join(
        f"- {source.document_name}: SHA-256 `{source.sha256}`" for source in bundle.sources
    )]
    return "\n\n".join(lines) + "\n"
