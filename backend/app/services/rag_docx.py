"""Dependency-free ``.docx`` (OOXML) export for RAG answers.

A ``.docx`` file is just a ZIP of XML parts, so we emit the minimal set Word /
WPS accept — ``[Content_Types].xml``, ``_rels/.rels`` and ``word/document.xml`` —
using only the standard library. This avoids a ``python-docx`` dependency (which
cannot be installed in the no-pip preview venv) while giving clinicians a Word
document instead of raw Markdown (product fix P2-2). Reviewer-facing content
mirrors the Markdown export's evidence-first core; the technical-audit block is
intentionally omitted (P0-5).
"""

from __future__ import annotations

import io
import re
import zipfile
from xml.sax.saxutils import escape

from app.schemas.rag import RagAnswerResponse

_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_XML_ILLEGAL_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" '
    'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" '
    'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
    "</Types>"
)

_ROOT_RELS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" '
    'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
    'Target="word/document.xml"/>'
    "</Relationships>"
)


def _paragraph(text: str, *, bold: bool = False, size_pt: int | None = None) -> str:
    """One ``<w:p>`` paragraph; ``size_pt`` is in points (OOXML uses half-points)."""

    run_props = ""
    if bold:
        run_props += "<w:b/>"
    if size_pt is not None:
        run_props += f'<w:sz w:val="{size_pt * 2}"/>'
    wrapped_props = f"<w:rPr>{run_props}</w:rPr>" if run_props else ""
    normalized_text = (
        _XML_ILLEGAL_CONTROL_CHARS.sub("", text).replace("\r\n", "\n").replace("\r", "\n")
    )
    lines = normalized_text.split("\n")
    text_runs: list[str] = []
    for index, line in enumerate(lines):
        if index > 0:
            text_runs.append("<w:br/>")
        text_runs.append(f'<w:t xml:space="preserve">{escape(line)}</w:t>')
    return f"<w:p><w:r>{wrapped_props}{''.join(text_runs)}</w:r></w:p>"


def build_answer_docx(answer: RagAnswerResponse) -> bytes:
    """Render a RAG answer payload as a minimal, valid ``.docx`` document."""

    paragraphs: list[str] = [
        _paragraph("Qiyan Nexus RAG 答案导出", bold=True, size_pt=18),
        _paragraph(f"回答模式：{answer.provider_name} / {answer.retrieval.strategy}"),
        _paragraph(f"证据范围：{answer.retrieval.applied_source}"),
        _paragraph(f"引用卡片：{len(answer.citations)}"),
        _paragraph("问题", bold=True, size_pt=14),
        _paragraph(answer.question),
        _paragraph("回答", bold=True, size_pt=14),
        _paragraph(answer.answer),
        _paragraph(answer.disclaimer, bold=True),
        _paragraph("引用证据", bold=True, size_pt=14),
    ]
    if not answer.citations:
        paragraphs.append(_paragraph("（当前回答没有可核对的引用证据。）"))
    else:
        for index, citation in enumerate(answer.citations, start=1):
            paragraphs.append(
                _paragraph(f"{index}. {citation.title}（{citation.source}）", bold=True)
            )
            paragraphs.append(_paragraph(citation.snippet))
            if citation.quote:
                paragraphs.append(_paragraph(f"证据片段引文：{citation.quote}"))

    body = "".join(paragraphs) + "<w:sectPr/>"
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{_W_NS}"><w:body>{body}</w:body></w:document>'
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _CONTENT_TYPES)
        archive.writestr("_rels/.rels", _ROOT_RELS)
        archive.writestr("word/document.xml", document)
    return buffer.getvalue()
