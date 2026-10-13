"""Orchestrate selection -> plan -> lessons -> files -> optional database ledger."""

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .database import record_run
from .lesson_generator import generate_lesson
from .lesson_renderer import render_bundle, render_lesson
from .lesson_segmenter import segment_lessons
from .lesson_types import GeneratedLesson, LessonBundle, LessonPlan
from .lesson_validator import validate_lesson, validate_plan
from .prompts import PROMPT_VERSION
from .storage import atomic_text, read_checkpoint, save_checkpoint, write_json


def generate_lessons(*, client, settings, course_id, documents, output_root: Path,
                     topic=None, assignment_id=None, db_path=None, regenerate=False, progress=print):
    identity = {
        "version": __version__, "prompt_version": PROMPT_VERSION, "course": course_id,
        "topic": topic, "assignment": assignment_id,
        "database": str(db_path.resolve()) if db_path else None,
        "model": settings.model, "max_lessons": settings.max_lessons,
        "max_output_tokens": settings.max_output_tokens,
        "sources": [{"name": doc.document_name, "sha256": doc.sha256,
                     "pages": [page.page_number for page in doc.pages],
                     "text_sha256": hashlib.sha256("\n".join(page.text for page in doc.pages).encode()).hexdigest()}
                    for doc in documents],
    }
    if regenerate:
        identity["regeneration"] = uuid.uuid4().hex
    run_id = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:24]
    slug = re.sub(r"[^a-z0-9]+", "-", course_id.lower()).strip("-")[:35] or "course"
    directory = output_root.resolve() / f"{slug}-{run_id}"
    checkpoint_dir = directory / "checkpoints"
    directory.mkdir(parents=True, exist_ok=True)
    progress(f"[output] {directory}")
    plan_file = checkpoint_dir / "plan.json"
    plan = read_checkpoint(plan_file, LessonPlan)
    if plan is None:
        progress("[plan] Organizing the supplied material into coherent lessons.")
        plan = segment_lessons(client, course_id, topic, documents, settings.max_lessons)
        save_checkpoint(plan_file, plan)
    else:
        errors = validate_plan(plan, documents, settings.max_lessons)
        if errors:
            raise ValueError("Saved plan is invalid: " + "; ".join(errors))
        progress("[cache] Reusing saved lesson plan.")
    for index, unit in enumerate(plan.units, 1):
        progress(f"[plan] {index}. {unit.title}")
    if plan.excluded_sources:
        progress(f"[plan] {len(plan.excluded_sources)} page(s) explicitly excluded; reasons are saved in plan.json.")
    write_json(directory / "plan.json", plan)
    write_json(directory / "sources.json", [doc.model_dump(mode="json") for doc in documents])
    write_json(directory / "manifest.json", {"run_id": run_id, "status": "in_progress", "request": identity})
    lessons = []
    for index, unit in enumerate(plan.units, 1):
        checkpoint = checkpoint_dir / f"lesson-{index:02d}.json"
        lesson = read_checkpoint(checkpoint, GeneratedLesson)
        if lesson is not None:
            if (lesson.unit != unit or lesson.course_id != course_id or lesson.assignment_id != assignment_id
                    or lesson.lesson_id != f"{run_id}-{index:02d}"):
                raise ValueError("Saved lesson does not match this run. Use --regenerate.")
            report = validate_lesson(lesson.content, unit, documents)
            if report.errors:
                raise ValueError("Saved lesson failed validation: " + "; ".join(report.errors))
            lesson.validation = report
            progress(f"[cache] Reusing lesson {index}/{len(plan.units)}: {unit.title}")
        else:
            progress(f"[generate] Lesson {index}/{len(plan.units)}: {unit.title}")
            lesson = generate_lesson(client, run_id=run_id, index=index, course_id=course_id,
                                     assignment_id=assignment_id, unit=unit, plan=plan, documents=documents)
            save_checkpoint(checkpoint, lesson)
        lessons.append(lesson)
        write_json(directory / f"lesson-{index:02d}.json", lesson)
        markdown = render_lesson(lesson, documents)
        if settings.model == "offline-fixture":
            markdown = "> OFFLINE DEMO: Prerecorded example; no AI request was made.\n\n" + markdown
        atomic_text(directory / f"lesson-{index:02d}.md", markdown)
        progress(f"[saved] lesson-{index:02d}.md and lesson-{index:02d}.json")
    warnings = [warning for doc in documents for warning in doc.warnings]
    warnings.extend(f"{lesson.title}: {warning}" for lesson in lessons for warning in lesson.validation.warnings)
    bundle = LessonBundle(
        run_id=run_id, created_at=datetime.now(timezone.utc).isoformat(), course_id=course_id,
        assignment_id=assignment_id, topic=topic, model=settings.model,
        status="needs_review" if warnings else "complete", plan=plan,
        sources=documents, lessons=lessons, warnings=warnings,
    )
    write_json(directory / "lessons.json", bundle)
    atomic_text(directory / "lessons.md", render_bundle(bundle))
    # Only publish completed run state after all lesson files are written successfully.
    if db_path is not None and assignment_id is not None:
        record_run(db_path, assignment_id, bundle, directory)
        progress("[database] Recorded this lecture run; assignment scores and the legacy completion flag are unchanged.")
    write_json(directory / "manifest.json", {
        "run_id": run_id, "status": bundle.status, "request": identity,
        "lesson_count": len(lessons), "json_path": "lessons.json", "markdown_path": "lessons.md",
    })
    return bundle, directory
