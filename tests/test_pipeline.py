import json
import sqlite3
import subprocess
import sys
import tempfile
from contextlib import closing
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from curriculum_engine.config import PROJECT_ROOT, Settings
from curriculum_engine.database import get_assignment, list_assignments
from curriculum_engine.demo import DemoClient
from curriculum_engine.lesson_renderer import render_bundle
from curriculum_engine.lesson_service import generate_lessons
from curriculum_engine.lesson_types import LessonBundle, LessonContent, LessonPlan
from curriculum_engine.lesson_validator import validate_lesson, validate_plan
from curriculum_engine.llm_client import GenerationError, JsonModelClient
from curriculum_engine.source_loader import load_sources, parse_page_selection
from curriculum_engine.storage import read_checkpoint


def response(text, finish_reason="stop"):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=text), finish_reason=finish_reason)])


def create_database(path):
    connection = sqlite3.connect(path)
    connection.execute("""CREATE TABLE assignments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_name TEXT, assignment_name TEXT, due_date TEXT, weight_percentage REAL,
        urgency_score INTEGER, impact_score INTEGER, total_score INTEGER, tier INTEGER,
        requires_manual_review BOOLEAN, lessons_generated BOOLEAN DEFAULT 0
    )""")
    connection.execute("""INSERT INTO assignments
        (course_name, assignment_name, due_date, weight_percentage, urgency_score, impact_score,
         total_score, tier, requires_manual_review, lessons_generated)
        VALUES ('CS 245', 'Midterm', '2026-10-20', 25, 1, 10, 11, 2, 0, 1)""")
    connection.commit()
    connection.close()


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.documents = load_sources([PROJECT_ROOT / "examples" / "demo_lecture.md"])
        self.client = DemoClient(self.documents)
        self.settings = Settings(model="offline-fixture")
        self.db = self.root / "curriculum.db"
        create_database(self.db)

    def tearDown(self):
        self.temporary.cleanup()

    def run_pipeline(self, client=None, **overrides):
        kwargs = dict(client=client or self.client, settings=self.settings, course_id="CS 245",
                      documents=self.documents, output_root=self.root / "output", assignment_id=1,
                      db_path=self.db, progress=lambda _: None)
        kwargs.update(overrides)
        return generate_lessons(**kwargs)

    def test_all_sections_saved_and_legacy_database_preserved(self):
        before = get_assignment(self.db, 1)
        bundle, directory = self.run_pipeline()
        reloaded = LessonBundle.model_validate_json((directory / "lessons.json").read_text(encoding="utf-8"))
        self.assertEqual(reloaded, bundle)
        markdown = (directory / "lessons.md").read_text(encoding="utf-8")
        for heading in ("Learning objectives", "Prerequisites", "Big picture", "Definitions and notation",
                        "Explanation", "Worked examples", "Common mistakes", "Method guide", "Recap", "Source references"):
            self.assertIn("## " + heading, markdown)
        self.assertIn("OFFLINE DEMO", markdown)
        self.assertEqual(before, get_assignment(self.db, 1))
        with closing(sqlite3.connect(self.db)) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM lesson_runs").fetchone()[0], 1)
        self.assertEqual(json.loads((directory / "manifest.json").read_text())["status"], "complete")

    def test_cached_run_needs_zero_model_requests_and_restores_rendered_files(self):
        _, directory = self.run_pipeline()
        (directory / "lessons.md").unlink()
        resumed = DemoClient(self.documents)
        _, second_directory = self.run_pipeline(resumed)
        self.assertEqual(directory, second_directory)
        self.assertEqual(resumed.call_count, 0)
        self.assertTrue((directory / "lessons.md").is_file())

    def test_failed_second_lesson_resumes_and_does_not_mark_complete(self):
        original = self.client.complete_json

        def fail_second(*args, **kwargs):
            if kwargs["stage"].startswith("Writing lesson 2"):
                raise GenerationError("simulated provider outage")
            return original(*args, **kwargs)

        self.client.complete_json = fail_second
        with self.assertRaisesRegex(GenerationError, "simulated"):
            self.run_pipeline()
        directory = next((self.root / "output").iterdir())
        self.assertTrue((directory / "lesson-01.md").is_file())
        self.assertFalse((directory / "lessons.json").exists())
        self.assertEqual(json.loads((directory / "manifest.json").read_text())["status"], "in_progress")
        with closing(sqlite3.connect(self.db)) as connection:
            self.assertIsNone(connection.execute("SELECT name FROM sqlite_master WHERE name='lesson_runs'").fetchone())
        resumed = DemoClient(self.documents)
        self.run_pipeline(resumed)
        self.assertEqual(resumed.call_count, 1)

    def test_changed_sources_are_not_reused(self):
        _, old_directory = self.run_pipeline()
        modified = self.documents[0].model_copy(deep=True)
        modified.pages[0].text += " Additional context."
        _, new_directory = self.run_pipeline(DemoClient([modified]), documents=[modified])
        self.assertNotEqual(old_directory, new_directory)

    def test_regeneration_preserves_prior_run(self):
        _, first = self.run_pipeline()
        _, second = self.run_pipeline(DemoClient(self.documents), regenerate=True)
        self.assertNotEqual(first, second)
        self.assertTrue((first / "lessons.json").is_file())

    def test_failed_file_write_creates_no_success_record(self):
        before = get_assignment(self.db, 1)
        with patch("curriculum_engine.lesson_service.atomic_text", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(OSError, "disk full"):
                self.run_pipeline()
        self.assertEqual(before, get_assignment(self.db, 1))
        with closing(sqlite3.connect(self.db)) as connection:
            self.assertIsNone(connection.execute("SELECT name FROM sqlite_master WHERE name='lesson_runs'").fetchone())

    def test_missing_database_is_not_created(self):
        missing = self.root / "wrong.db"
        with self.assertRaisesRegex(ValueError, "Database not found"):
            list_assignments(missing)
        self.assertFalse(missing.exists())

    def test_tampered_checkpoint_not_accepted(self):
        _, directory = self.run_pipeline()
        checkpoint = directory / "checkpoints" / "plan.json"
        value = json.loads(checkpoint.read_text())
        value["payload"]["overview"] = "changed"
        checkpoint.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, "changed or is damaged"):
            read_checkpoint(checkpoint, LessonPlan)

    def test_unknown_references_are_rejected_but_math_brackets_are_valid(self):
        plan = LessonPlan.model_validate(self.client.responses["plan"])
        content = LessonContent.model_validate(self.client.responses["lessons"][plan.units[0].title])
        content.core_explanation.markdown += " Valid syntax includes a[0], [0, 1], and std::vector<T>."
        self.assertFalse(validate_lesson(content, plan.units[0], self.documents).errors)
        content.big_picture.source_ids = ["invented-page"]
        self.assertTrue(validate_lesson(content, plan.units[0], self.documents).errors)

    def test_omitted_source_page_rejected(self):
        plan = LessonPlan.model_validate(self.client.responses["plan"])
        plan.units[1].source_ids.remove(self.documents[0].pages[5].source_id)
        self.assertTrue(any("Unaccounted" in error for error in validate_plan(plan, self.documents, 12)))

    def test_extraction_and_selected_page_identity(self):
        self.assertEqual(len(self.documents[0].pages), 6)
        selected = load_sources([PROJECT_ROOT / "examples" / "demo_lecture.md"], "2-3,6")
        self.assertEqual([p.page_number for p in selected[0].pages], [2, 3, 6])
        self.assertEqual(selected[0].pages[0].source_id, self.documents[0].pages[1].source_id)
        with self.assertRaisesRegex(ValueError, "do not exist"):
            load_sources([PROJECT_ROOT / "examples" / "demo_lecture.md"], "99")

    def test_empty_source_blocked(self):
        empty = self.root / "empty.txt"
        empty.write_text("\n   ")
        with self.assertRaisesRegex(ValueError, "no readable text"):
            load_sources([empty])

    def test_page_range_validation(self):
        self.assertEqual(parse_page_selection("1-3,5"), {1, 2, 3, 5})
        for bad in ("0", "3-1", "abc", "-1", ""):
            with self.assertRaises(ValueError):
                parse_page_selection(bad)

    def test_cli_help_and_demo_from_different_working_directory(self):
        command = [sys.executable, str(PROJECT_ROOT / "study.py")]
        help_run = subprocess.run(command, cwd=self.root, capture_output=True, text=True)
        self.assertEqual(help_run.returncode, 0, help_run.stderr)
        self.assertIn("generate", help_run.stdout)
        demo = subprocess.run(command + ["demo", "--out", str(self.root / "demo")],
                              cwd=self.root, capture_output=True, text=True)
        self.assertEqual(demo.returncode, 0, demo.stderr)
        self.assertIn("OFFLINE DEMO COMPLETE", demo.stdout)

    def test_cli_dry_run_does_not_write_outputs(self):
        output = self.root / "unused"
        command = [sys.executable, str(PROJECT_ROOT / "study.py"), "generate", "--course", "CS 245",
                   "--source", str(PROJECT_ROOT / "examples" / "demo_lecture.md"),
                   "--out", str(output), "--dry-run"]
        result = subprocess.run(command, cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(output.exists())


class ModelBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.documents = load_sources([PROJECT_ROOT / "examples" / "demo_lecture.md"])
        self.valid = json.dumps(DemoClient(self.documents).responses["plan"])

    def test_schema_is_in_prompt_and_invalid_json_is_repaired_once(self):
        calls = []

        def transport(**kwargs):
            calls.append(kwargs)
            return response("{}" if len(calls) == 1 else self.valid)

        client = JsonModelClient(Settings(), lambda _: None, transport=transport)
        result = client.complete_json(LessonPlan, "Plan lessons.", {}, stage="test")
        self.assertEqual(len(result.units), 2)
        self.assertIn('"excluded_sources"', calls[0]["messages"][0]["content"])
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0]["num_retries"], 0)

    def test_truncated_output_is_not_accepted(self):
        client = JsonModelClient(Settings(), lambda _: None,
                                 transport=lambda **_: response(self.valid, "length"))
        with self.assertRaisesRegex(GenerationError, "cut off"):
            client.complete_json(LessonPlan, "", {}, stage="test")

    def test_repeated_empty_output_fails_after_two_calls(self):
        client = JsonModelClient(Settings(), lambda _: None, transport=lambda **_: response(None))
        with self.assertRaisesRegex(GenerationError, "empty"):
            client.complete_json(LessonPlan, "", {}, stage="test")
        self.assertEqual(client.call_count, 2)

    def test_retry_limit_counts_transport_attempts_and_hides_provider_body(self):
        class RateLimitError(Exception):
            status_code = 429

        def transport(**kwargs):
            raise RateLimitError("sensitive response body")

        client = JsonModelClient(Settings(), lambda _: None, transport=transport, sleep=lambda _: None)
        with self.assertRaises(GenerationError) as caught:
            client.complete_json(LessonPlan, "", {}, stage="test")
        self.assertIn("429", str(caught.exception))
        self.assertNotIn("sensitive", str(caught.exception))
        self.assertEqual(client.call_count, 3)

    def test_request_budget_prevents_unbounded_retry(self):
        client = JsonModelClient(Settings(max_calls=1), lambda _: None, transport=lambda **_: response("{}"))
        with self.assertRaisesRegex(GenerationError, "request limit"):
            client.complete_json(LessonPlan, "", {}, stage="test")
        self.assertEqual(client.call_count, 1)

    def test_context_limit_is_explicit_not_silent_truncation(self):
        client = JsonModelClient(Settings(max_input_chars=10), lambda _: None,
                                 transport=lambda **_: response(self.valid))
        with self.assertRaisesRegex(GenerationError, "No source text was silently truncated"):
            client.complete_json(LessonPlan, "", {}, stage="test")
        self.assertEqual(client.call_count, 0)

    def test_outer_json_fence_is_supported(self):
        client = JsonModelClient(Settings(), lambda _: None,
                                 transport=lambda **_: response("```json\n" + self.valid + "\n```"))
        self.assertEqual(len(client.complete_json(LessonPlan, "", {}, stage="test").units), 2)

    def test_missing_key_is_actionable_without_importing_litellm(self):
        client = JsonModelClient(Settings(), lambda _: None)
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(GenerationError, "GROQ_API_KEY is missing"):
                client.preflight()


if __name__ == "__main__":
    unittest.main()
