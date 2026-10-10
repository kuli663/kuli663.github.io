# -*- coding: utf-8 -*-
"""将 thesis/预演毕业论文.md 转换为带封面的 Word 文档（需 python-docx）。"""
import os
import re
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD = os.path.join(BASE, "thesis", "预演毕业论文.md")
OUT = os.path.join(BASE, "thesis", "预演毕业论文.docx")


def set_font(run, name="宋体", size=12, bold=False):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)


def add_par(doc, text, size=12, bold=False, align=None, name="宋体"):
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    # 处理 **加粗** 行内标记
    parts = re.split(r"(\*\*[^*]+\*\*)", text)
    for part in parts:
        if part.startswith("**") and part.endswith("**"):
            r = p.add_run(part[2:-2])
            set_font(r, name, size, True)
        elif part:
            r = p.add_run(part)
            set_font(r, name, size, bold)
    return p


def flush_table(doc, rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    if len(cells) >= 2 and all(set(c) <= set("-: ") for c in cells[1]):
        cells = [cells[0]] + cells[2:]
    ncol = max(len(r) for r in cells)
    table = doc.add_table(rows=len(cells), cols=ncol)
    table.style = "Table Grid"
    for i, row in enumerate(cells):
        for j in range(ncol):
            txt = row[j] if j < len(row) else ""
            cell = table.cell(i, j)
            cell.text = ""
            r = cell.paragraphs[0].add_run(re.sub(r"\*\*", "", txt))
            set_font(r, "宋体", 10.5, bold=(i == 0))


def main():
    doc = Document()
    for section in doc.sections:
        section.top_margin = section.bottom_margin = Cm(2.54)
        section.left_margin = section.right_margin = Cm(3.17)

    lines = open(MD, encoding="utf-8").read().splitlines()
    table_buf = []
    title_done = False
    for line in lines:
        if line.strip().startswith("|"):
            table_buf.append(line)
            continue
        if table_buf:
            flush_table(doc, table_buf)
            table_buf = []
        s = line.strip()
        if not s:
            continue
        if s == "---":
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            level, text = len(m.group(1)), m.group(2)
            if level == 1 and not title_done:
                add_par(doc, text, size=18, bold=True,
                        align=WD_ALIGN_PARAGRAPH.CENTER, name="黑体")
                title_done = True
            else:
                sizes = {1: 16, 2: 14, 3: 12, 4: 12}
                add_par(doc, text, size=sizes.get(level, 12), bold=True, name="黑体")
        elif s.startswith("- "):
            add_par(doc, "  " + s[2:], size=11)
        else:
            p = add_par(doc, s, size=12)
            p.paragraph_format.first_line_indent = Pt(24)
            p.paragraph_format.line_spacing = 1.5
    if table_buf:
        flush_table(doc, table_buf)
    doc.save(OUT)
    print("已生成:", OUT)


if __name__ == "__main__":
    main()
