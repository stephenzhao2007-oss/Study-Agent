"""One bounded, observable boundary around LiteLLM; injectable for offline tests."""

import json
import math
import os
import re
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Callable, TypeVar

from pydantic import BaseModel, ValidationError

from .config import Settings

T = TypeVar("T", bound=BaseModel)


class GenerationError(RuntimeError):
    pass


class ProviderJSONError(GenerationError):
    """A provider-side JSON failure eligible for the existing bounded repair."""


def safe_message(error: object) -> str:
    text = str(error)
    key = os.environ.get("GROQ_API_KEY", "")
    if key:
        text = text.replace(key, "[REDACTED]")
    text = re.sub(r"(?:gsk_|sk-)[A-Za-z0-9_-]+", "[REDACTED]", text)
    return re.sub(r"(?i)Bearer\s+[^\s\"']+", "Bearer [REDACTED]", text)


def provider_details(exc):
    """Read only the provider's error code/message, never its request or failed_generation."""
    candidates = [getattr(exc, "body", None)]
    response = getattr(exc, "response", None)
    if response is not None:
        try:
            candidates.append(response.json())
        except (ValueError, AttributeError, TypeError):
            pass
    candidates.append(str(exc))
    for item in candidates:
        if isinstance(item, str):
            # LiteLLM may prefix the provider JSON with an exception name.
            start = item.find("{")
            if start == -1:
                continue
            try:
                item, _ = json.JSONDecoder().raw_decode(item[start:])
            except ValueError:
                continue
        if not isinstance(item, dict):
            continue
        error = item.get("error", item)
        if not isinstance(error, dict):
            continue
        code, message = error.get("code"), error.get("message")
        if isinstance(message, str):
            return str(code or ""), safe_message(" ".join(message.split()))[:700]
    return "", "No structured provider error details were available."


def retry_after_seconds(exc):
    for holder in (getattr(exc, "response", None), exc):
        headers = getattr(holder, "headers", None)
        if not headers:
            continue
        lowered = {str(k).lower(): str(v) for k, v in headers.items()}
        value = lowered.get("retry-after")
        if value is None:
            continue
        try:
            seconds = float(value)
        except ValueError:
            try:
                moment = parsedate_to_datetime(value)
                if moment.tzinfo is None:
                    moment = moment.replace(tzinfo=timezone.utc)
                seconds = (moment - datetime.now(timezone.utc)).total_seconds()
            except (ValueError, TypeError, OverflowError):
                continue
        if math.isfinite(seconds):
            return max(0, seconds)
    return None


class JsonModelClient:
    def __init__(self, settings: Settings, progress: Callable[[str], None], *, transport=None, sleep=time.sleep,
                 clock=time.monotonic, request_interval=None):
        self.settings = settings
        self.progress = progress
        self.transport = transport
        self.sleep = sleep
        self.call_count = 0
        self.clock = clock
        # Conservative spacing for this free-tier terminal workflow. Test transports default to zero.
        self.request_interval = (65 if transport is None else 0) if request_interval is None else request_interval
        self.last_success_at = None

    def _wait(self, seconds, reason):
        remaining = max(0, math.ceil(seconds))
        while remaining:
            self.progress(f"[wait] {reason}; {remaining}s remaining. Ctrl+C stops safely.")
            step = min(30, remaining)
            self.sleep(step)
            remaining -= step

    def preflight(self):
        if self.transport is not None:
            return
        if not self.settings.model.startswith("groq/"):
            raise GenerationError("This version uses your Groq connection. STUDY_MODEL must start with groq/.")
        key = os.environ.get("GROQ_API_KEY", "").strip()
        if not key:
            raise GenerationError('GROQ_API_KEY is missing. In CMD use: set "GROQ_API_KEY=your_key"')
        if key != key.strip('"\''):
            raise GenerationError('GROQ_API_KEY contains quote characters. In CMD use: set "GROQ_API_KEY=your_key"')
        try:
            # Keep help, database inspection, and the demo usable without LiteLLM installed.
            from litellm import completion
        except ImportError as exc:
            raise GenerationError("Install dependencies first: py -m pip install -r requirements.txt") from exc
        self.transport = completion

    def _request(self, messages, stage):
        self.preflight()
        if self.last_success_at is not None:
            delay = self.request_interval - (self.clock() - self.last_success_at)
            if delay > 0:
                self._wait(delay, "Spacing Groq requests")
        for attempt in range(self.settings.transport_attempts):
            if self.call_count >= self.settings.max_calls:
                raise GenerationError(
                    "Model request limit reached for this run. Completed lessons are saved; rerun to resume, "
                    "or explicitly increase --max-calls. This is a request limit, not a dollar spending cap."
                )
            self.call_count += 1
            self.progress(f"[model] {stage}; request {self.call_count}/{self.settings.max_calls}")
            try:
                response = self.transport(
                    model=self.settings.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    max_tokens=self.settings.max_output_tokens,
                    temperature=0.2,
                    timeout=self.settings.timeout_seconds,
                    num_retries=0,
                )
                self.last_success_at = self.clock()
                return response
            except Exception as exc:
                code = getattr(exc, "status_code", None)
                name = type(exc).__name__
                error_code, detail = provider_details(exc)
                details = f" Provider code: {error_code}." if error_code else ""
                details += f" Provider message: {detail}"
                if code == 400 and error_code == "json_validate_failed":
                    raise ProviderJSONError(f"{stage}: provider rejected generated JSON.{details}") from None
                transient = code in {408, 429, 500, 502, 503, 504} or name in {
                    "Timeout", "APITimeoutError", "APIConnectionError", "RateLimitError", "ServiceUnavailableError"
                }
                if transient and attempt + 1 < self.settings.transport_attempts:
                    delay = retry_after_seconds(exc)
                    if delay is None:
                        delay = 65 if code == 429 or name == "RateLimitError" else 3 * (2 ** attempt)
                    else:
                        delay += 1  # Avoid retrying exactly on a reset boundary.
                    if delay > 120:
                        raise GenerationError(
                            f"{stage}: {name} (HTTP {code or 'unknown'}). Provider asks to wait about "
                            f"{math.ceil(delay)}s; stopping instead of retrying early. "
                            f"Saved lessons can be resumed later.{details}"
                        ) from None
                    self.progress(f"[retry] {name} (HTTP {code or 'unknown'}).{details}")
                    self._wait(delay, "Waiting before retry")
                    continue
                hints = {
                    400: "The provider rejected this request. See its error details below; waiting alone may not fix it.",
                    401: "Check the GROQ_API_KEY in this terminal.",
                    403: "Your key may not have access to this model.",
                    404: "Check STUDY_MODEL against your provider's available model IDs.",
                    413: "The provider rejected the request size; select fewer pages with --pages.",
                    429: "Your provider quota/rate limit was reached. Wait and rerun to resume.",
                }
                hint = hints.get(code, "Check the provider/model configuration or retry later.")
                raise GenerationError(f"{stage}: {name} (HTTP {code or 'unknown'}). {hint}{details}") from None

    def complete_json(self, schema: type[T], system_prompt: str, payload: dict, *, stage: str,
                      check: Callable[[T], list[str]] | None = None) -> T:
        instructions = system_prompt + "\nReturn a single JSON object matching this JSON Schema:\n"
        instructions += json.dumps(schema.model_json_schema(), ensure_ascii=False)
        base_messages = [
            {"role": "system", "content": instructions},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]
        messages = list(base_messages)
        for attempt in range(self.settings.format_attempts):
            char_count = sum(len(m["content"]) for m in messages)
            if char_count > self.settings.max_input_chars:
                raise GenerationError(
                    f"{stage}: prompt is {char_count:,} characters; configured limit is "
                    f"{self.settings.max_input_chars:,}. Select fewer pages with --pages or adjust config.py. "
                    "No source text was silently truncated."
                )
            try:
                response = self._request(messages, stage)
            except ProviderJSONError as exc:
                if attempt + 1 == self.settings.format_attempts:
                    raise GenerationError(str(exc)) from None
                self.progress("[repair] Provider rejected malformed JSON; one corrected generation will be attempted.")
                self._wait(65, "Spacing JSON repair request")
                messages = base_messages + [{
                    "role": "user", "content": "The provider rejected the previous generated JSON. Return a complete "
                    "valid JSON object matching the supplied schema. Escape backslashes and newlines in strings correctly."
                }]
                continue
            choices = getattr(response, "choices", None)
            if not choices:
                raise GenerationError(f"{stage}: provider returned no choices.")
            choice = choices[0]
            if getattr(choice, "finish_reason", None) == "length":
                raise GenerationError(
                    f"{stage}: output was cut off by the token limit. Increase --max-output-tokens "
                    "or select a smaller topic/page range; truncated output has not been accepted."
                )
            raw = getattr(getattr(choice, "message", None), "content", None)
            issues = []
            if not isinstance(raw, str) or not raw.strip():
                issues = ["The response was empty or did not contain text."]
            else:
                cleaned = raw.strip()
                # Remove only one complete outer code fence; never extract an arbitrary JSON fragment.
                match = re.fullmatch(r"```(?:json)?\s*\n?(.*?)\n?```", cleaned, flags=re.S | re.I)
                if match:
                    cleaned = match.group(1).strip()
                try:
                    parsed = schema.model_validate_json(cleaned)
                    issues = check(parsed) if check else []
                    if not issues:
                        return parsed
                except ValidationError as exc:
                    issues = [f"{'.'.join(map(str, e['loc'])) or 'response'}: {e['msg']}"
                              for e in exc.errors(include_input=False, include_url=False)][:12]
            if attempt + 1 == self.settings.format_attempts:
                raise GenerationError(f"{stage}: response failed validation: " + "; ".join(issues))
            self.progress(f"[repair] {stage}: requesting one corrected response ({'; '.join(issues[:3])}).")
            # Resubmit source context and errors, without accumulating long invalid answers.
            messages = base_messages + [{
                "role": "user", "content": "The previous response failed validation. Generate a fresh complete "
                "JSON response addressing these errors: " + "; ".join(issues)
            }]
        raise GenerationError(f"{stage}: no valid response.")
