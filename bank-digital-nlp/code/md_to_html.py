# -*- coding: utf-8 -*-
"""将论文Markdown转为自包含HTML页面（用于GitHub Pages展示）。"""
import html
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD = os.path.join(BASE, "thesis", "预演毕业论文.md")
OUT = os.path.join(BASE, "site", "thesis.html")

CSS = """
body{font-family:'Songti SC','SimSun',serif;max-width:860px;margin:0 auto;padding:32px 20px;line-height:1.9;color:#1a1a1a}
h1{font-size:1.6em;text-align:center;font-family:'SimHei',sans-serif}
h2{font-size:1.3em;border-bottom:2px solid #2c5f8a;padding-bottom:6px;margin-top:2em;font-family:'SimHei',sans-serif}
h3{font-size:1.1em;font-family:'SimHei',sans-serif}
table{border-collapse:collapse;width:100%;margin:1em 0;font-size:.92em}
th,td{border:1px solid #999;padding:6px 10px;text-align:left}
th{background:#eef3f8}
p{text-indent:2em;margin:.6em 0}
li{margin:.3em 0}
.meta{text-align:center;color:#555}
a{color:#2c5f8a}
"""


def inline(t):
    t = html.escape(t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    return t


def main():
    lines = open(MD, encoding="utf-8").read().splitlines()
    out, table, in_list = [], [], False
    for line in lines:
        if line.strip().startswith("|"):
            table.append(line)
            continue
        if table:
            cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in table]
            if len(cells) >= 2 and all(set(c) <= set("-: ") for c in cells[1]):
                cells = [cells[0]] + cells[2:]
            out.append("<table>")
            for i, row in enumerate(cells):
                tag = "th" if i == 0 else "td"
                out.append("<tr>" + "".join(f"<{tag}>{inline(c)}</{tag}>" for c in row) + "</tr>")
            out.append("</table>")
            table = []
        s = line.strip()
        if s.startswith("- "):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{inline(s[2:])}</li>")
            continue
        if in_list:
            out.append("</ul>")
            in_list = False
        if not s or s == "---":
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            lvl = len(m.group(1))
            out.append(f"<h{lvl}>{inline(m.group(2))}</h{lvl}>")
        else:
            out.append(f"<p>{inline(s)}</p>")
    if in_list:
        out.append("</ul>")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    page = (f"<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>预演毕业论文：商业银行数字化转型测度</title><style>{CSS}</style></head>"
            f"<body>{chr(10).join(out)}<p class='meta'><a href='index.html'>← 返回项目主页</a></p></body></html>")
    open(OUT, "w", encoding="utf-8").write(page)
    print("已生成:", OUT)


if __name__ == "__main__":
    main()
