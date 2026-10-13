"""Check structure and reference membership. These checks do not prove factual correctness."""

import re

from .lesson_context_builder import page_index
from .lesson_types import LessonContent, LessonPlan, LessonUnit, SourceDocument, ValidationReport


def validate_plan(plan: LessonPlan, documents: list[SourceDocument], max_lessons: int) -> list[str]:
    known = set(page_index(documents))
    used = {ref for unit in plan.units for ref in unit.source_ids}
    excluded = {item.source_id for item in plan.excluded_sources}
    errors = []
    if len(plan.units) > max_lessons:
        errors.append(f"Use at most {max_lessons} coherent lessons.")
    if (used | excluded) - known:
        errors.append(f"Unknown source IDs: {sorted((used | excluded) - known)}")
    if known - (used | excluded):
        errors.append(f"Unaccounted source pages: {sorted(known - (used | excluded))}")
    if used & excluded:
        errors.append("A page cannot be both used and excluded.")
    if len(excluded) != len(plan.excluded_sources):
        errors.append("Duplicate excluded source IDs.")
    for unit in plan.units:
        if len(unit.source_ids) != len(set(unit.source_ids)):
            errors.append(f"Duplicate source IDs in unit {unit.title}.")
    return errors


def validate_lesson(content: LessonContent, unit: LessonUnit, documents: list[SourceDocument]) -> ValidationReport:
    available = set(page_index(documents)) & set(unit.source_ids)
    groups = [content.big_picture.source_ids, content.core_explanation.source_ids]
    groups += [definition.source_ids for definition in content.definitions_and_notation]
    groups += [example.source_ids for example in content.worked_examples]
    references = {ref for group in groups for ref in group}
    errors, warnings = [], []
    if references - available:
        errors.append(f"References were not supplied to this lesson: {sorted(references - available)}")
    # Deliberately narrow placeholder check. C++ <T>, a[0], and mathematical intervals are valid.
    text = content.model_dump_json()
    if re.search(r"\[\s*(?:insert (?:formula|explanation|example)(?: here)?|TODO|TBD)\s*\]", text, re.I):
        errors.append("Remove unresolved authoring placeholders and report unavailable source content explicitly.")
    uncited = available - references
    if uncited:
        warnings.append("Some planned context pages were not cited: " + ", ".join(sorted(uncited)))
    if len(content.core_explanation.markdown.split()) < 120:
        warnings.append("The core explanation is short; review whether it teaches the objective sufficiently.")
    warnings.extend(content.unresolved_source_problems)
    return ValidationReport(structural_checks_passed=not errors, errors=errors, warnings=warnings)
