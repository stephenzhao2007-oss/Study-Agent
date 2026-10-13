"""Read the existing assignments schema; add a separate per-run lesson ledger."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def _connect(path: Path, *, readonly=True):
    path = path.expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"Database not found: {path}. Use --db with the existing curriculum.db path.")
    connection = sqlite3.connect(path.as_uri() + ("?mode=ro" if readonly else "?mode=rw"), uri=True)
    connection.row_factory = sqlite3.Row
    try:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(assignments)")}
        required = {"id", "course_name", "assignment_name", "due_date", "total_score", "tier",
                    "requires_manual_review", "lessons_generated"}
        if not required <= columns:
            raise ValueError("This is not the expected priority database; missing assignments fields: "
                             + ", ".join(sorted(required - columns)))
        yield connection
    finally:
        connection.close()


def list_assignments(path: Path) -> list[dict]:
    with _connect(path) as connection:
        return [dict(row) for row in connection.execute(
            "SELECT id, course_name, assignment_name, due_date, total_score, tier, "
            "requires_manual_review, lessons_generated FROM assignments "
            "ORDER BY total_score DESC, due_date ASC, id ASC"
        )]


def get_assignment(path: Path, assignment_id: int) -> dict:
    with _connect(path) as connection:
        row = connection.execute("SELECT * FROM assignments WHERE id = ?", (assignment_id,)).fetchone()
    if row is None:
        raise ValueError(f"Assignment ID {assignment_id} is not in {path}. Run the tasks command first.")
    return dict(row)


def record_run(path: Path, assignment_id: int, bundle, output_directory: Path):
    # A single lecture never implies that an entire exam has been covered.
    # Preserve the old flag and every priority score; record this exact input separately.
    with _connect(path, readonly=False) as connection:
        with connection:
            if connection.execute("SELECT id FROM assignments WHERE id = ?", (assignment_id,)).fetchone() is None:
                raise ValueError("Assignment disappeared before the lesson run could be recorded.")
            connection.execute("""
                CREATE TABLE IF NOT EXISTS lesson_runs (
                    run_id TEXT PRIMARY KEY,
                    assignment_id INTEGER NOT NULL,
                    course_id TEXT NOT NULL,
                    topic TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    output_directory TEXT NOT NULL,
                    lesson_count INTEGER NOT NULL
                )
            """)
            connection.execute("""
                INSERT INTO lesson_runs
                (run_id, assignment_id, course_id, topic, status, created_at, output_directory, lesson_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    status=excluded.status, output_directory=excluded.output_directory,
                    lesson_count=excluded.lesson_count
            """, (bundle.run_id, assignment_id, bundle.course_id, bundle.topic, bundle.status,
                  bundle.created_at, str(output_directory.resolve()), len(bundle.lessons)))
