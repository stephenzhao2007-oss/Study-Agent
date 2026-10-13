"""Build bounded source context from verified IDs; never silently discard slides."""

from .lesson_types import LessonPlan, LessonUnit, SourceDocument


def page_index(documents: list[SourceDocument]):
    return {page.source_id: page for doc in documents for page in doc.pages}


def plan_context(course_id: str, topic: str | None, documents: list[SourceDocument], max_lessons: int):
    return {
        "course_id": course_id,
        "requested_scope": topic or "Teach all substantive content in the supplied lecture material.",
        "max_lessons": max_lessons,
        "source_pages": [page.model_dump() for doc in documents for page in doc.pages],
    }


def lesson_context(course_id: str, unit: LessonUnit, plan: LessonPlan, documents: list[SourceDocument]):
    pages = page_index(documents)
    return {
        "course_id": course_id,
        "lecture_overview": plan.overview,
        "lesson_sequence": [item.title for item in plan.units],
        "selected_unit": unit.model_dump(),
        "source_pages": [pages[ref].model_dump() for ref in unit.source_ids],
    }
