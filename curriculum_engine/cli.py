"""Windows-friendly command-line entry point with actionable errors and visible progress."""

import argparse
import importlib.metadata
import os
import sqlite3
import sys
from pathlib import Path

from pydantic import ValidationError

from .config import PROJECT_ROOT, Settings
from .database import get_assignment, list_assignments
from .lesson_service import generate_lessons
from .llm_client import GenerationError, JsonModelClient, safe_message
from .source_loader import load_sources


def progress(message):
    print(message, flush=True)


def _positive(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError("Must be a positive integer.")
    return number


def parser():
    root = argparse.ArgumentParser(description="Generate saved lessons from your lecture files.")
    commands = root.add_subparsers(dest="command")
    commands.add_parser("doctor", help="Check dependencies and whether a key is set; makes no API calls.")
    tasks = commands.add_parser("tasks", help="List your existing assignments using their stored priority scores.")
    tasks.add_argument("--db", type=Path, default=PROJECT_ROOT / "curriculum.db")
    inspect = commands.add_parser("inspect", help="Check local lecture extraction without making an API request.")
    inspect.add_argument("--source", type=Path, nargs="+", required=True)
    inspect.add_argument("--pages", help="One source only; e.g. 1-10,12-20.")
    demo = commands.add_parser("demo", help="Run the real file pipeline with prerecorded examples; no key needed.")
    demo.add_argument("--out", type=Path, default=PROJECT_ROOT / "demo_output")
    generate = commands.add_parser("generate", help="Create or resume source-grounded lessons.")
    target = generate.add_mutually_exclusive_group(required=True)
    target.add_argument("--assignment-id", type=_positive, help="ID from the tasks command.")
    target.add_argument("--course", help="Standalone course name, when not linking an assignment.")
    generate.add_argument("--db", type=Path, default=PROJECT_ROOT / "curriculum.db")
    generate.add_argument("--source", type=Path, nargs="+", required=True)
    generate.add_argument("--pages", help="Selected pages from one source, e.g. 1-20,23.")
    generate.add_argument("--topic", help="Narrow lesson scope; omit to cover the supplied lecture material.")
    generate.add_argument("--out", type=Path, default=PROJECT_ROOT / "output")
    generate.add_argument("--max-output-tokens", type=_positive, default=6500)
    generate.add_argument("--max-calls", type=_positive, default=24)
    generate.add_argument("--dry-run", action="store_true", help="Check inputs only; makes no API requests or database writes.")
    generate.add_argument("--regenerate", action="store_true", help="Make a separate fresh run, preserving older outputs.")
    generate.add_argument("--print", dest="print_lesson", action="store_true", help="Also print all lesson text in the terminal.")
    return root


def _doctor():
    progress(f"Python: {sys.version.split()[0]}")
    missing = []
    for package in ("pydantic", "litellm", "pypdf"):
        try:
            progress(f"{package}: {importlib.metadata.version(package)}")
        except importlib.metadata.PackageNotFoundError:
            missing.append(package)
            progress(f"{package}: not installed")
    progress("GROQ_API_KEY: " + ("set (value hidden)" if os.environ.get("GROQ_API_KEY") else "not set"))
    progress(f"Model: {Settings.from_environment().model}")
    progress("This check makes no request and does not verify account/model access.")
    return 1 if missing else 0


def main(argv=None):
    # CMD code pages should not turn an otherwise successful lesson into UnicodeEncodeError.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace")
    arguments = parser()
    args = arguments.parse_args(argv)
    if not args.command:
        arguments.print_help()
        return 0
    try:
        if args.command == "doctor":
            return _doctor()
        if args.command == "tasks":
            rows = list_assignments(args.db)
            progress(f"Database: {args.db.resolve()}")
            if not rows:
                progress("No assignments found. Run your existing priority generator first.")
            for row in rows:
                progress(f"ID {row['id']} | {row['total_score']}/20 | Tier {row['tier']} | "
                         f"Due {row['due_date']} | {row['course_name']} | {row['assignment_name']}"
                         + (" | MANUAL REVIEW" if row['requires_manual_review'] else "")
                         + f" | legacy lesson flag={row['lessons_generated']}")
            progress("These are stored priority scores. Recalculate them in your priority module as dates change.")
            return 0
        if args.command == "demo":
            from .demo import run_demo
            _, directory = run_demo(args.out, progress)
            progress(f"OFFLINE DEMO COMPLETE. Open: {directory / 'lessons.md'}")
            return 0
        progress("[load] Reading lecture sources.")
        documents = load_sources(args.source, args.pages)
        progress(f"[load] {len(documents)} file(s), {sum(len(doc.pages) for doc in documents)} readable page/section(s).")
        for document in documents:
            for warning in document.warnings:
                progress(f"[source note] {warning}")
        if args.command == "inspect":
            for document in documents:
                for page in document.pages:
                    progress(f"{page.source_id} | {page.document_name}, page/section {page.page_number} | "
                             + " ".join(page.text.split())[:180])
            progress("No API calls made. Check formulas and diagrams against the original PDF.")
            return 0
        database_path = None
        if args.assignment_id:
            task = get_assignment(args.db, args.assignment_id)
            if task["requires_manual_review"]:
                raise ValueError("This assignment is flagged for manual review in your priority database. "
                                 "Correct its data there, or use --course for standalone lesson generation.")
            course = task["course_name"]
            if not course or not course.strip():
                raise ValueError("Assignment has no course name. Correct it in the priority database.")
            database_path = args.db
            progress(f"[task] ID {args.assignment_id}: {course} / {task['assignment_name']}")
        else:
            course = args.course.strip()
            if not course:
                raise ValueError("--course cannot be empty.")
        settings = Settings.from_environment(max_calls=args.max_calls, max_output_tokens=args.max_output_tokens)
        if args.dry_run:
            progress(f"READY: {course}; scope: {args.topic or 'all supplied lecture material'}; model: {settings.model}.")
            progress("Generation normally uses one planning call plus one call per lesson. "
                     f"This run allows at most {settings.max_calls} request attempts including retries.")
            progress("No API requests, output writes, or database updates were made.")
            return 0
        client = JsonModelClient(settings, progress)
        bundle, directory = generate_lessons(
            client=client, settings=settings, course_id=course, documents=documents,
            output_root=args.out, topic=args.topic, assignment_id=args.assignment_id,
            db_path=database_path, regenerate=args.regenerate, progress=progress,
        )
        progress(f"DONE: {len(bundle.lessons)} lesson(s); status: {bundle.status}; API requests: {client.call_count}.")
        progress(f"Read: {directory / 'lessons.md'}")
        progress(f"Structured data: {directory / 'lessons.json'}")
        if bundle.warnings:
            progress("Review the source/review notes in lessons.md.")
        if args.print_lesson:
            progress((directory / "lessons.md").read_text(encoding="utf-8"))
        return 0
    except KeyboardInterrupt:
        progress("Stopped. Rerun the same command to resume saved lessons.")
        return 130
    except (GenerationError, ValueError, OSError, sqlite3.Error, ValidationError) as exc:
        print("ERROR: " + safe_message(exc), file=sys.stderr, flush=True)
        return 1
