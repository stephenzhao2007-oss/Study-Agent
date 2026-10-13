"""Generate one complete lesson at a time and validate its reference structure."""

from .lesson_context_builder import lesson_context
from .lesson_types import GeneratedLesson, LessonContent
from .lesson_validator import validate_lesson
from .prompts import LESSON_PROMPT


def generate_lesson(client, *, run_id, index, course_id, assignment_id, unit, plan, documents):
    content = client.complete_json(
        LessonContent, LESSON_PROMPT, lesson_context(course_id, unit, plan, documents),
        stage=f"Writing lesson {index}: {unit.title}",
        check=lambda result: validate_lesson(result, unit, documents).errors,
    )
    return GeneratedLesson(
        lesson_id=f"{run_id}-{index:02d}", course_id=course_id, assignment_id=assignment_id,
        title=unit.title, unit=unit, content=content, validation=validate_lesson(content, unit, documents),
    )
