"""Validated contracts shared by the planner, generator, and persistence layer."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictStr

Text = Annotated[StrictStr, Field(min_length=1)]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SourcePage(Contract):
    source_id: Text
    document_name: Text
    page_number: int = Field(ge=1)
    text: Text


class SourceDocument(Contract):
    document_name: Text
    sha256: Text
    pages: list[SourcePage] = Field(min_length=1)
    warnings: list[str] = Field(default_factory=list)


class LessonUnit(Contract):
    title: Text
    learning_objectives: list[Text] = Field(min_length=1)
    prerequisites: list[Text]
    source_ids: list[Text] = Field(min_length=1)


class ExcludedSource(Contract):
    source_id: Text
    reason: Text


class LessonPlan(Contract):
    overview: Text
    units: list[LessonUnit] = Field(min_length=1)
    excluded_sources: list[ExcludedSource]


class CitedText(Contract):
    markdown: Text
    source_ids: list[Text] = Field(min_length=1)


class Definition(Contract):
    term_or_symbol: Text
    explanation: Text
    source_ids: list[Text] = Field(min_length=1)


class WorkedExample(Contract):
    title: Text
    origin: Literal["source", "generated"]
    problem: Text
    solution: Text
    source_ids: list[Text] = Field(min_length=1)


class LessonContent(Contract):
    learning_objectives: list[Text] = Field(min_length=1)
    prerequisites: Text
    big_picture: CitedText
    definitions_and_notation: list[Definition]
    core_explanation: CitedText
    worked_examples: list[WorkedExample] = Field(min_length=1)
    common_mistakes: list[Text] = Field(min_length=1)
    method_guide: Text | None
    recap: Text
    unresolved_source_problems: list[Text]


class ValidationReport(Contract):
    structural_checks_passed: bool
    errors: list[str]
    warnings: list[str]


class GeneratedLesson(Contract):
    lesson_id: Text
    course_id: Text
    assignment_id: int | None
    title: Text
    unit: LessonUnit
    content: LessonContent
    validation: ValidationReport


class LessonBundle(Contract):
    schema_version: int = 1
    run_id: Text
    created_at: Text
    course_id: Text
    assignment_id: int | None
    topic: str | None
    model: Text
    status: Literal["complete", "needs_review"]
    plan: LessonPlan
    sources: list[SourceDocument]
    lessons: list[GeneratedLesson] = Field(min_length=1)
    warnings: list[str]
