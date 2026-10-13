"""Atomic UTF-8 writes and validated checkpoints for interrupted lesson runs."""

import hashlib
import json
import os
import tempfile
from pathlib import Path


def atomic_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_json(path: Path, value):
    payload = value.model_dump(mode="json") if hasattr(value, "model_dump") else value
    atomic_text(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def save_checkpoint(path: Path, value):
    payload = value.model_dump(mode="json")
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    write_json(path, {"sha256": digest, "payload": payload})


def read_checkpoint(path: Path, schema):
    if not path.exists():
        return None
    try:
        envelope = json.loads(path.read_text(encoding="utf-8"))
        payload = envelope["payload"]
        expected_digest = envelope["sha256"]
    except (ValueError, KeyError, TypeError) as exc:
        raise ValueError(f"Unreadable checkpoint: {path}. Use --regenerate for a separate fresh run.") from exc
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    if digest != expected_digest:
        raise ValueError(f"Checkpoint changed or is damaged: {path}. Use --regenerate for a separate fresh run.")
    return schema.model_validate(payload)
