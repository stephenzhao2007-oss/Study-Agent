"""Small, explicit configuration; credentials are read only by the live client."""

import os
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "groq/openai/gpt-oss-20b"


@dataclass(frozen=True)
class Settings:
    model: str = DEFAULT_MODEL
    timeout_seconds: int = 90
    max_output_tokens: int = 6500
    max_input_chars: int = 100_000
    max_lessons: int = 12
    max_calls: int = 24
    transport_attempts: int = 3
    format_attempts: int = 2

    @classmethod
    def from_environment(cls, **overrides):
        model = os.environ.get("STUDY_MODEL", DEFAULT_MODEL).strip()
        return cls(model=model, **overrides)
