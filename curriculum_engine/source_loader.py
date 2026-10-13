"""Extract text with stable page IDs and explicit extraction limitations."""

import hashlib
import re
from pathlib import Path

from .lesson_types import SourceDocument, SourcePage


def parse_page_selection(spec: str | None) -> set[int] | None:
    if spec is None:
        return None
    pages = set()
    for item in spec.split(","):
        item = item.strip()
        if not re.fullmatch(r"[1-9]\d*(?:-[1-9]\d*)?", item):
            raise ValueError("Use page numbers such as --pages 1-12,15,18-20.")
        ends = [int(n) for n in item.split("-")]
        first, last = ends[0], ends[-1]
        if first > last or last - first > 10000:
            raise ValueError(f"Invalid page range: {item}")
        pages.update(range(first, last + 1))
    return pages


def _text_pages(path: Path) -> list[tuple[int, str]]:
    raw = path.read_bytes()
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        text = raw.decode("utf-16")
    else:
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValueError(f"Save {path.name} as UTF-8 in Notepad and try again.") from exc
    markers = list(re.finditer(r"(?mi)^\s*<!--\s*page:\s*([1-9]\d*)\s*-->\s*$", text))
    if markers:
        if text[:markers[0].start()].strip():
            raise ValueError(f"{path.name}: move introductory text after the first page marker.")
        result = []
        for i, marker in enumerate(markers):
            end = markers[i + 1].start() if i + 1 < len(markers) else len(text)
            result.append((int(marker.group(1)), text[marker.end():end]))
        if len({n for n, _ in result}) != len(result):
            raise ValueError(f"{path.name}: duplicate page markers.")
        return result
    return list(enumerate(text.split("\f"), 1))


def load_sources(paths: list[Path], page_selection: str | None = None) -> list[SourceDocument]:
    selected = parse_page_selection(page_selection)
    if selected and len(paths) != 1:
        raise ValueError("--pages applies to one source file. Supply one PDF or text file.")
    documents = []
    seen = set()
    for path in paths:
        path = path.expanduser().resolve()
        if not path.is_file():
            raise ValueError(f"Source file not found: {path}")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in seen:
            raise ValueError(f"Duplicate source content: {path.name}. Supply each file once.")
        seen.add(digest)
        warnings = []
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            try:
                from pypdf import PdfReader
            except ImportError as exc:
                raise ValueError("PDF support needs pypdf. Run: py -m pip install -r requirements.txt") from exc
            try:
                reader = PdfReader(path)
                if reader.is_encrypted and not reader.decrypt(""):
                    raise ValueError("The PDF is password protected. Supply an unlocked copy.")
                pairs = [(i, page.extract_text() or "") for i, page in enumerate(reader.pages, 1)
                         if not selected or i in selected]
                available = set(range(1, len(reader.pages) + 1))
            except Exception as exc:
                raise ValueError(f"Could not extract {path.name}: {exc}") from exc
            warnings.append(
                f"{path.name}: PDF text extraction does not interpret diagrams, images, or handwritten "
                "annotations and may lose mathematical notation. Check these against the original slides."
            )
        elif suffix in {".txt", ".md"}:
            pairs = _text_pages(path)
            available = {number for number, _ in pairs}
            if selected:
                pairs = [(number, text) for number, text in pairs if number in selected]
        else:
            raise ValueError(f"Unsupported source: {path.name}. Use PDF, UTF-8 TXT, or Markdown; export PPT/PPTX to PDF.")
        if selected and not selected <= available:
            raise ValueError(f"Pages do not exist in {path.name}: {sorted(selected - available)}")
        pages = []
        for number, text in pairs:
            text = text.strip()
            if not text:
                raise ValueError(
                    f"{path.name}, page {number}: no readable text. Supply an OCR/text export, "
                    "or exclude this page explicitly with --pages if it contains no teaching material."
                )
            if "\ufffd" in text or "(cid:" in text:
                warnings.append(f"{path.name}, page {number}: possible damaged character or formula extraction.")
            pages.append(SourcePage(source_id=f"s{digest[:12]}p{number}", document_name=path.name,
                                    page_number=number, text=text))
        if not pages:
            raise ValueError(f"No selected source text in {path.name}.")
        documents.append(SourceDocument(document_name=path.name, sha256=digest,
                                        pages=pages, warnings=warnings))
    if not documents:
        raise ValueError("Supply at least one lecture source.")
    return documents
