"""Ask the model for conceptual lesson boundaries, then check page coverage."""

from .lesson_context_builder import plan_context
from .lesson_types import LessonPlan
from .lesson_validator import validate_plan
from .prompts import PLAN_PROMPT


def segment_lessons(client, course_id, topic, documents, max_lessons):
    return client.complete_json(
        LessonPlan, PLAN_PROMPT, plan_context(course_id, topic, documents, max_lessons),
        stage="Organizing lecture concepts",
        check=lambda plan: validate_plan(plan, documents, max_lessons),
    )
