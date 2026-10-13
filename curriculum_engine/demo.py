"""An explicitly offline fixture provider for testing the complete local pipeline."""

import json

from .config import PROJECT_ROOT, Settings
from .lesson_service import generate_lessons
from .lesson_types import LessonContent, LessonPlan
from .source_loader import load_sources


class DemoClient:
    def __init__(self, documents):
        self.call_count = 0
        payload = (PROJECT_ROOT / "examples" / "demo_responses.json").read_text(encoding="utf-8")
        for page in documents[0].pages:
            payload = payload.replace(f"$PAGE_{page.page_number}", page.source_id)
        self.responses = json.loads(payload)

    def complete_json(self, schema, system_prompt, payload, *, stage, check=None):
        self.call_count += 1
        if schema is LessonPlan:
            result = schema.model_validate(self.responses["plan"])
        elif schema is LessonContent:
            result = schema.model_validate(self.responses["lessons"][payload["selected_unit"]["title"]])
        else:
            raise ValueError("Offline demo does not provide this response type.")
        if check:
            issues = check(result)
            if issues:
                raise ValueError("Demo response failed checks: " + "; ".join(issues))
        return result


def run_demo(output_root, progress):
    progress("OFFLINE DEMO: using bundled illustrative notes and prerecorded answers; no network or API key.")
    documents = load_sources([PROJECT_ROOT / "examples" / "demo_lecture.md"])
    return generate_lessons(
        client=DemoClient(documents), settings=Settings(model="offline-fixture"),
        course_id="CS 245 (offline demo)", documents=documents, output_root=output_root, progress=progress,
    )
