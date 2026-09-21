#!/usr/bin/env python3
"""Convert a Markdown document into a Word .docx file.

Written for the RPCI user manual, so it covers the constructs that document
uses: headings, pipe tables, fenced code blocks, bullet and numbered lists,
horizontal rules, and inline bold and code spans.

Usage, from the repository root:

    backend/.venv/bin/python scripts/md_to_docx.py USER_MANUAL.md
    backend/.venv/bin/python scripts/md_to_docx.py USER_MANUAL.md --out docs/manual.docx
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt, RGBColor

MONOSPACE = "Consolas"
CODE_FILL = "F4F6F8"
INK = RGBColor(0x0F, 0x17, 0x2A)
MUTED = RGBColor(0x64, 0x74, 0x8B)

# Inline spans: **bold** and `code`.
INLINE_PATTERN = re.compile(r"(\*\*.+?\*\*|`[^`]+`)")
BULLET_PATTERN = re.compile(r"^(\s*)[-*]\s+(.*)$")
NUMBER_PATTERN = re.compile(r"^(\s*)\d+\.\s+(.*)$")
TABLE_DIVIDER = re.compile(r"^\|[\s:|-]+\|$")


def add_bottom_border(paragraph) -> None:
    """Draw a thin grey rule under a paragraph, standing in for a horizontal rule."""
    properties = paragraph._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "D6DBE2")
    borders.append(bottom)
    properties.append(borders)


def shade(paragraph, fill: str) -> None:
    """Apply a background fill to a paragraph."""
    properties = paragraph._p.get_or_add_pPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:val"), "clear")
    shading.set(qn("w:color"), "auto")
    shading.set(qn("w:fill"), fill)
    properties.append(shading)


def shade_cell(cell, fill: str) -> None:
    """Apply a background fill to a table cell."""
    properties = cell._tc.get_or_add_tcPr()
    shading = OxmlElement("w:shd")
    shading.set(qn("w:val"), "clear")
    shading.set(qn("w:color"), "auto")
    shading.set(qn("w:fill"), fill)
    properties.append(shading)


def add_inline(paragraph, text: str) -> None:
    """Add text to a paragraph, honouring **bold** and `code` spans."""
    for piece in INLINE_PATTERN.split(text):
        if not piece:
            continue
        if piece.startswith("**") and piece.endswith("**"):
            run = paragraph.add_run(piece[2:-2])
            run.bold = True
        elif piece.startswith("`") and piece.endswith("`"):
            run = paragraph.add_run(piece[1:-1])
            run.font.name = MONOSPACE
            run.font.size = Pt(9.5)
            run.font.color.rgb = RGBColor(0x1D, 0x4E, 0xD8)
        else:
            paragraph.add_run(piece)


def split_row(line: str) -> list[str]:
    """Split a pipe table row into its cells."""
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return [cell.strip() for cell in stripped.split("|")]


def add_table(document: Document, rows: list[list[str]]) -> None:
    """Render a pipe table, treating the first row as a bold header."""
    if not rows:
        return
    width = max(len(row) for row in rows)
    table = document.add_table(rows=0, cols=width)
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.LEFT

    for index, row in enumerate(rows):
        cells = table.add_row().cells
        for position in range(width):
            text = row[position] if position < len(row) else ""
            cell = cells[position]
            cell.text = ""
            paragraph = cell.paragraphs[0]
            add_inline(paragraph, text)
            for run in paragraph.runs:
                run.font.size = Pt(9.5)
                if index == 0:
                    run.bold = True
            if index == 0:
                shade_cell(cell, "F1F5F9")
    document.add_paragraph()


def add_code_block(document: Document, lines: list[str]) -> None:
    """Render a fenced code block in a monospaced, shaded paragraph."""
    paragraph = document.add_paragraph()
    paragraph.paragraph_format.space_before = Pt(6)
    paragraph.paragraph_format.space_after = Pt(10)
    paragraph.paragraph_format.left_indent = Pt(8)
    shade(paragraph, CODE_FILL)

    for position, line in enumerate(lines):
        if position:
            paragraph.add_run().add_break()
        run = paragraph.add_run(line)
        run.font.name = MONOSPACE
        run.font.size = Pt(9)


def add_list_item(document: Document, indent: int, text: str, numbered: bool) -> None:
    """Render a bullet or numbered list item, nesting by indent level."""
    if numbered:
        style = "List Number"
    else:
        style = "List Bullet" if indent == 0 else f"List Bullet {min(indent + 1, 3)}"
    paragraph = document.add_paragraph(style=style)
    paragraph.paragraph_format.space_after = Pt(2)
    add_inline(paragraph, text)


def starts_block(text: str) -> bool:
    """True when a line begins a new block rather than continuing a paragraph.

    Markdown source is often hard-wrapped, so consecutive plain lines belong to
    one paragraph. Anything that opens its own block ends the run.
    """
    if not text:
        return True
    if text.startswith(("#", "```", "|")):
        return True
    if text in {"---", "***", "___"}:
        return True
    return BULLET_PATTERN.match(text) is not None or NUMBER_PATTERN.match(text) is not None


def convert(source: Path, destination: Path) -> None:
    """Read a Markdown file and write the Word equivalent."""
    document = Document()

    normal = document.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10.5)
    normal.paragraph_format.space_after = Pt(6)

    lines = source.read_text(encoding="utf-8").splitlines()
    index = 0

    while index < len(lines):
        line = lines[index]
        stripped = line.strip()

        # Fenced code block
        if stripped.startswith("```"):
            index += 1
            block: list[str] = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                block.append(lines[index])
                index += 1
            index += 1
            add_code_block(document, block)
            continue

        # Table
        if stripped.startswith("|") and index + 1 < len(lines) and TABLE_DIVIDER.match(lines[index + 1].strip()):
            rows: list[list[str]] = [split_row(stripped)]
            index += 2
            while index < len(lines) and lines[index].strip().startswith("|"):
                rows.append(split_row(lines[index]))
                index += 1
            add_table(document, rows)
            continue

        # Horizontal rule
        if stripped in {"---", "***", "___"}:
            paragraph = document.add_paragraph()
            paragraph.paragraph_format.space_before = Pt(2)
            paragraph.paragraph_format.space_after = Pt(8)
            add_bottom_border(paragraph)
            index += 1
            continue

        # Headings. The document's `#` is the title, so `##` becomes Heading 1
        # and `###` becomes Heading 2, keeping the outline levels contiguous.
        if stripped.startswith("### "):
            heading = document.add_heading(level=2)
            add_inline(heading, stripped[4:])
            for run in heading.runs:
                run.font.color.rgb = INK
            index += 1
            continue
        if stripped.startswith("## "):
            heading = document.add_heading(level=1)
            add_inline(heading, stripped[3:])
            for run in heading.runs:
                run.font.color.rgb = INK
            index += 1
            continue
        if stripped.startswith("# "):
            heading = document.add_heading(level=0)
            add_inline(heading, stripped[2:])
            for run in heading.runs:
                run.font.color.rgb = INK
            index += 1
            continue

        # Lists
        bullet = BULLET_PATTERN.match(line)
        if bullet:
            add_list_item(document, len(bullet.group(1)) // 2, bullet.group(2), numbered=False)
            index += 1
            continue
        number = NUMBER_PATTERN.match(line)
        if number:
            add_list_item(document, len(number.group(1)) // 2, number.group(2), numbered=True)
            index += 1
            continue

        # Blank line
        if not stripped:
            index += 1
            continue

        # A run of plain lines forms one reflowable paragraph.
        buffer = []
        while index < len(lines) and not starts_block(lines[index].strip()):
            buffer.append(lines[index].strip())
            index += 1
        paragraph = document.add_paragraph()
        add_inline(paragraph, " ".join(buffer))

    destination.parent.mkdir(parents=True, exist_ok=True)
    document.save(str(destination))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="Markdown file to convert")
    parser.add_argument("--out", help="Destination .docx path")
    args = parser.parse_args()

    source = Path(args.source)
    if not source.is_file():
        print(f"Not found: {source}", file=sys.stderr)
        return 1

    destination = Path(args.out) if args.out else source.with_suffix(".docx")
    convert(source, destination)

    words = len(source.read_text(encoding="utf-8").split())
    print(f"Wrote {destination}  ({words:,} words from {source.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
