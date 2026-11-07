#!/usr/bin/env python3
"""
Builds ONE self-contained HTML handbook from all 32 markdown parts.

Output: output/PostgreSQL_Master_Handbook.html
  - Single file, no dependencies, works offline.
  - Screen: sidebar TOC + main content, light/dark theme, syntax-highlighted code.
  - Print (Ctrl+P -> Save as PDF): compact ~200-page textbook layout.

Run from the project root:
  python scripts/build_handbook.py
"""
import os
import re
import html as h
import glob

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(BASE, "content")
OUT = os.path.join(BASE, "output", "PostgreSQL_Master_Handbook.html")

# ----------------------------------------------------------------- order ---
PART_LABELS = {
    "01": "Foundations of Databases & SQL",
    "02": "PostgreSQL DDL — Creating Everything",
    "02b": "DML, DQL, DCL & TCL",
    "03": "Every SQL Keyword, Clause & Operator",
    "04": "All Types of Joins",
    "05": "Subqueries & Advanced Querying",
    "06": "Aggregates, Strings, Dates & Numbers",
    "07": "Window Functions — Advanced",
    "08": "Data Types — Complete Reference",
    "09": "Constraints & Data Integrity",
    "10": "Database Design & Normalization",
    "11": "Indexing — Professional Level",
    "12": "Query Performance & Optimization",
    "13": "Transactions & ACID",
    "14": "Locking & Concurrency Control",
    "15": "PL/pgSQL, Functions & Triggers",
    "16": "JSON, JSONB & Semi-Structured Data",
    "17": "Partitioning & Large Databases",
    "18": "Security in PostgreSQL",
    "19": "Administration & DBA Commands",
    "20": "Backup, Restore & Disaster Recovery",
    "21": "Replication & Distributed Databases",
    "22": "AWS Database Engineering",
    "23": "Other Database Technologies",
    "24": "PostgreSQL Extensions",
    "25": "Backend Development & Databases",
    "26": "Real-World Architecture Case Studies",
    "27": "SQL Interview Preparation",
    "28": "SQL Practice Problems",
    "29": "Advanced PostgreSQL Internals",
    "30": "Monitoring & Production Troubleshooting",
    "31": "Complete Keyword Glossary",
    "32": "SQL Quick Reference",
}

def part_key(filename):
    m = re.search(r"part_(\d+)(b?)[^0-9]*", filename)
    if not m:
        return 999
    num, suffix = int(m.group(1)), m.group(2)
    return num + (0.5 if suffix == "b" else 0.0)

def files_in_order():
    files = [f for f in os.listdir(CONTENT) if f.endswith(".md")]
    return sorted(files, key=part_key)

# --------------------------------------------------------------- converters --
SQL_KW = (r"\b(SELECT|FROM|WHERE|AND|OR|NOT|NULL|IS|IN|LIKE|ILIKE|BETWEEN|CASE|WHEN|THEN|ELSE|END|AS|"
          r"GROUP|BY|HAVING|ORDER|LIMIT|OFFSET|UNION|ALL|DISTINCT|EXCEPT|INTERSECT|JOIN|INNER|LEFT|RIGHT|FULL|CROSS|OUTER|ON|USING|"
          r"INSERT|INTO|VALUES|UPDATE|SET|DELETE|TRUNCATE|MERGE|UPSERT|CONFLICT|DO|RETURNING|"
          r"CREATE|ALTER|DROP|RENAME|ADD|TABLE|VIEW|INDEX|MATERIALIZED|UNIQUE|PRIMARY|KEY|FOREIGN|REFERENCES|CONSTRAINT|CHECK|DEFAULT|IF|EXISTS|"
          r"BEGIN|COMMIT|ROLLBACK|SAVEPOINT|TRANSACTION|WORK|ISOLATION|LEVEL|SERIALIZABLE|READ|WRITE|"
          r"EXPLAIN|ANALYZE|BUFFERS|VERBOSE|COSTS|FORMAT|TEXT|JSON|YAML|GENERIC|PLANNER|"
          r"GRANT|REVOKE|WITH|ADMIN OPTION|TO|ROLE|ON|DATABASE|SCHEMA|PRIVILEGES|"
          r"CAST|COALESCE|NULLIF|GREATEST|LEAST|POSITION|OVERLAY|SUBSTRING|TRIM|UPPER|LOWER|LENGTH|ABS|ROUND|FLOOR|CEIL|"
          r"NOW|CURRENT_TIMESTAMP|CURRENT_DATE|INTERVAL|GENERATE_SERIES|UNNEST|ARRAY|JSONB|JSON|BOOLEAN|INT|INTEGER|BIGINT|SMALLINT|"
          r"NUMERIC|DECIMAL|REAL|DOUBLE|PRECISION|TEXT|CHAR|VARCHAR|BYTEA|DATE|TIMESTAMP|TIMESTAMPTZ|TIME|TIMETZ|UUID|ENUM|SERIAL|IDENTITY|"
          r"ASC|DESC|PARTITION|WINDOW|ROWS|RANGE|GROUPS|UNBOUNDED|PRECEDING|FOLLOWING|CURRENT|ROW|FOR|UPDATE|DELETE|SHARE|NO|KEY|NOWAIT|SKIP|LOCKED|"
          r"RECURSIVE|LATERAL|NATURAL|FILTER|INCLUDE|OVERLAPS|EXCLUDE|WITHIN|GROUP|SET|LEADING|TRAILING|COLLATE|DESCRIBE|CALL|PROCEDURE|FUNCTION|LANGUAGE|VOLATILE|IMMUTABLE|STABLE|RETURNS|SETOF|OUT|INOUT|DECLARE|LOOP|WHILE|EXIT|RAISE|EXCEPTION|PLPGSQL|TRIGGER|AFTER|BEFORE|INSTEAD|EACH|ROW|TABLE|CASCADE|RESTRICT|NO ACTION|SET NULL|SET DEFAULT|CLUSTER|REINDEX|VACUUM|FULL|FREEZE|VERBOSE|VERBOSE|STATISTICS|"
          r"LIBRARY|EXTENSION|OWNED|DEPENDS|TABLESPACE|TEMPORARY|TEMP|UNLOGGED|BULK|OIDS|WITHOUT|OIDS|SEQUENCE|MINVALUE|MAXVALUE|START|INCREMENT|CYCLE|OWNED|CACHE|RESPECT|IGNORES|TZ|TYPING|TYPE|COLLATION|DOMAIN|ASSERTION|PROCEDURAL|ROUTINES|AGGREGATE|CAST|CONVERSION|ACCESS|METHOD|OPERATOR|OPERATORS|CLASS|AGGREGATE|TEXTORANGE)")

def highlight_sql(code: str) -> str:
    esc = h.escape(code)
    # comments
    esc = re.sub(r"(--[^\n]*)", r'<span class="c-com">\1</span>', esc)
    # strings
    esc = re.sub(r"('[^'\n]*')", r'<span class="c-str">\1</span>', esc)
    # keywords
    esc = re.sub(SQL_KW, lambda m: f'<span class="c-kw">{m.group(0)}</span>', esc)
    # numbers
    esc = re.sub(r"\b(\d+\.?\d*)\b", r'<span class="c-num">\1</span>', esc)
    return esc

def highlight_generic(code: str) -> str:
    esc = h.escape(code)
    esc = re.sub(r"(#[^\n]*)", r'<span class="c-com">\1</span>', esc)
    return esc

def highlight(code, lang):
    if lang.lower() in ("sql", ""):
        return highlight_sql(code)
    if lang.lower() in ("bash", "sh", "shell", "postgres"):
        # bash: highlight commands
        esc = h.escape(code)
        esc = re.sub(r"(#[^\n]*)", r'<span class="c-com">\1</span>', esc)
        esc = re.sub(r"(\$\w+)", r'<span class="c-var">\1</span>', esc)
        return esc
    return highlight_generic(code)

def inline(text: str) -> str:
    """Convert inline markdown (bold, italic, code) inside already-escaped text."""
    t = h.escape(text)
    t = re.sub(r"`([^`]+)`", lambda m: f'<code>{m.group(1)}</code>', t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", t)
    return t

def parse_md(md: str) -> str:
    lines = md.split("\n")
    out = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]

        # fenced code
        m = re.match(r"^```(\w*)\s*$", line)
        if m:
            lang = m.group(1)
            i += 1
            buf = []
            while i < n and not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1  # closing fence
            code = "\n".join(buf)
            out.append(f'<pre class="code"><span class="c-lang">{lang or "sql"}</span><code>{highlight(code, lang)}</code></pre>')
            continue

        # table
        if line.lstrip().startswith("|") and i + 1 < n and re.match(r"^\s*\|[\s\-:|]+\|", lines[i + 1]):
            header = [c.strip() for c in line.strip().strip("|").split("|")]
            i += 2
            rows = []
            while i < n and lines[i].lstrip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            out.append('<div class="tblwrap"><table><thead><tr>' +
                       "".join(f"<th>{inline(c)}</th>" for c in header) + "</tr></thead><tbody>")
            for r in rows:
                out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
            out.append("</tbody></table></div>")
            continue

        # heading
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            lvl = len(m.group(1))
            txt = m.group(2)
            out.append(f'<h{lvl} id="h">{h.escape(txt)}</h{lvl}>')
            i += 1
            continue

        # blockquote / callout
        if line.lstrip().startswith(">"):
            buf = []
            while i < n and lines[i].lstrip().startswith(">"):
                buf.append(re.sub(r"^\s*>\s?", "", lines[i]))
                i += 1
            body = "<br>".join(inline(b) for b in buf if b.strip())
            kind = "note"
            first = buf[0].lstrip() if buf else ""
            low = first.lower()
            if first.startswith("NOTE"):
                kind = "note"
            elif first.startswith("WARNING"):
                kind = "warn"
            elif first.startswith("INTERVIEW"):
                kind = "intv"
            elif first.startswith("PRACTICAL"):
                kind = "pract"
            elif low.startswith("version-specific"):
                kind = "note"
            out.append(f'<div class="callout co-{kind}"><b class="co-tag">{kind.upper()}</b><div>{body}</div></div>')
            continue

        # list (collect consecutive bullets/numbers)
        if re.match(r"^\s*[-*]\s+", line) or re.match(r"^\s*\d+\.\s+", line):
            ordered = bool(re.match(r"^\s*\d+\.\s+", line))
            buf = []
            while i < n and (re.match(r"^\s*[-*]\s+", lines[i]) or re.match(r"^\s*\d+\.\s+", lines[i])):
                buf.append(re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", lines[i]))
                i += 1
            tag = "ol" if ordered else "ul"
            out.append(f'<{tag}>' + "".join(f"<li>{inline(b)}</li>" for b in buf) + f"</{tag}>")
            continue

        # horizontal rule
        if re.match(r"^\s*-{3,}\s*$", line):
            out.append('<hr>')
            i += 1
            continue

        # paragraph
        if line.strip():
            buf = [line]
            i += 1
            while i < n and lines[i].strip() and not re.match(r"^(#{1,4}\s|```|\||>|\s*[-*]\s|\s*\d+\.\s|-{3,}\s*$)", lines[i]):
                buf.append(lines[i])
                i += 1
            out.append(f"<p>{inline(' '.join(b.strip() for b in buf))}</p>")
            continue

        i += 1
    return "\n".join(out)

# ---------------------------------------------------------------- template ---
CSS = r"""
:root{
  --bg:#ffffff; --fg:#1e293b; --muted:#64748b; --accent:#336791; --accent-dk:#244b6c;
  --code-bg:#0f172a; --code-fg:#e2e8f0; --line:#e2e8f0; --soft:#f1f5f9;
  --warn:#b45309; --ok:#047857;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --bg:#0f172a; --fg:#e2e8f0; --muted:#94a3b8; --accent:#60a5fa; --accent-dk:#93c5fd;
    --code-bg:#0b1220; --code-fg:#e2e8f0; --line:#293548; --soft:#1e293b;
    --warn:#fbbf24; --ok:#34d399;
  }
}
:root[data-theme="dark"]{
  --bg:#0f172a; --fg:#e2e8f0; --muted:#94a3b8; --accent:#60a5fa; --accent-dk:#93c5fd;
  --code-bg:#0b1220; --code-fg:#e2e8f0; --line:#293548; --soft:#1e293b;
  --warn:#fbbf24; --ok:#34d399;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.65 "Segoe UI",system-ui,-apple-system,sans-serif}
body{padding-left:264px}
/* ---------- sidebar ---------- */
#nav{position:fixed;top:0;left:0;width:264px;height:100vh;overflow-y:auto;background:var(--soft);border-right:1px solid var(--line);padding:20px 12px;z-index:10}
#nav .brand{font:700 15px/1.3 "Segoe UI",sans-serif;color:var(--accent);padding:4px 10px 14px;border-bottom:2px solid var(--accent);margin-bottom:12px}
#nav a{display:block;color:var(--fg);text-decoration:none;font-size:13.5px;padding:5px 10px;border-radius:6px;line-height:1.35}
#nav a small{display:block;color:var(--muted);font-size:11px}
#nav a:hover{background:var(--accent);color:#fff}
#nav a:hover small{color:#fff}
#nav .top{color:var(--muted);text-transform:uppercase;letter-spacing:.08em;font-size:11px;padding:12px 10px 4px}
#themeBtn{position:fixed;right:16px;top:14px;z-index:20;background:var(--soft);color:var(--fg);border:1px solid var(--line);border-radius:8px;padding:6px 12px;font-size:13px;cursor:pointer}
#themeBtn:hover{border-color:var(--accent);color:var(--accent)}
/* ---------- content ---------- */
main{max-width:920px;margin:0 auto;padding:40px 48px 120px}
.part{padding-top:8px}
h1.part-title{font-size:34px;line-height:1.15;color:var(--accent);margin:36px 0 6px;border-bottom:4px solid var(--accent);padding-bottom:14px}
.part:first-of-type h1.part-title{margin-top:0}
.subtitle{color:var(--muted);font-size:15px;margin:0 0 26px;font-style:italic}
h2{font-size:23px;margin:34px 0 12px;color:var(--fg);border-bottom:1px solid var(--line);padding-bottom:6px}
h2::before{content:"§ ";color:var(--accent)}
h3{font-size:18px;margin:24px 0 8px;color:var(--accent-dk)}
h4{font-size:15.5px;margin:18px 0 6px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
p{margin:10px 0}
strong{color:var(--accent-dk)}
hr{border:none;border-top:1px solid var(--line);margin:28px 0}
/* inline code */
code{font-family:"Cascadia Code",Consolas,"Courier New",monospace;font-size:.86em;background:var(--soft);border:1px solid var(--line);border-radius:4px;padding:1px 5px;color:#0f766e}
:root[data-theme="dark"] code, :root:not([data-theme="light"]) code{color:#5eead4}
/* code blocks */
pre.code{position:relative;background:var(--code-bg);color:var(--code-fg);border-radius:8px;padding:14px 16px;overflow-x:auto;margin:14px 0;font-size:13.5px;line-height:1.5}
pre.code code{background:none;border:none;padding:0;color:inherit;font-size:inherit}
.c-lang{position:absolute;top:8px;right:12px;font-size:10px;color:#64748b;text-transform:uppercase;letter-spacing:.1em}
.c-kw{color:#7dd3fc;font-weight:600}
.c-str{color:#86efac}
.c-num{color:#fcd34d}
.c-com{color:#64748b;font-style:italic}
.c-var{color:#c084fc}
:root[data-theme="dark"] .c-kw, :root:not([data-theme="dark"]) .c-kw{color:#7dd3fc}
:root:not([data-theme="dark"]) .c-kw{color:#0369a1}
:root:not([data-theme="dark"]) .c-str{color:#15803d}
:root:not([data-theme="dark"]) .c-num{color:#b45309}
/* tables */
.tblwrap{overflow-x:auto;margin:14px 0}
table{border-collapse:collapse;width:100%;font-size:14px}
th{background:var(--accent);color:#fff;text-align:left;padding:8px 10px;font-weight:600}
td{border:1px solid var(--line);padding:8px 10px;vertical-align:top}
tr:nth-child(even) td{background:var(--soft)}
/* callouts */
.callout{border-radius:8px;padding:12px 16px;margin:16px 0;border-left:4px solid var(--accent);background:var(--soft);font-size:14.5px}
.co-tag{font-size:11px;letter-spacing:.1em;color:var(--accent);display:block;margin-bottom:4px}
.co-warn{border-left-color:var(--warn)}
.co-warn .co-tag{color:var(--warn)}
.co-intv{border-left-color:var(--ok)}
.co-intv .co-tag{color:var(--ok)}
ul,ol{padding-left:24px;margin:10px 0}
li{margin:4px 0}
/* lists containing sub-tables etc */
/* cover */
.cover{border:3px solid var(--accent);border-radius:14px;padding:56px 40px;margin:20px 0 40px;text-align:center;background:var(--soft)}
.cover .k{color:var(--muted);letter-spacing:.25em;font-size:13px;text-transform:uppercase}
.cover h1{font-size:40px;margin:14px 0 6px;color:var(--accent);line-height:1.1}
.cover h2{font-size:24px;color:var(--fg);margin:0;font-weight:400}
.cover .meta{margin-top:26px;font-size:14px;color:var(--muted)}
/* ---------- PRINT: compact ~200-page textbook ---------- */
@media print{
  :root{--bg:#fff;--fg:#111;--muted:#555;--accent:#336791;--code-bg:#f5f5f5;--code-fg:#111;--line:#bbb;--soft:#f7f7f7}
  body{background:#fff;color:#111;padding:0;font-size:10.5pt;line-height:1.42}
  #nav,#themeBtn{display:none!important}
  main{max-width:100%;padding:0;margin:0}
  .cover{border:none;padding:0;margin:0;text-align:left;height:220mm;display:flex;align-items:center;background:#fff}
  .cover .k{font-size:11pt}.cover h1{font-size:30pt;margin:8pt 0 4pt}.cover h2{font-size:15pt}.cover .meta{margin-top:14pt;font-size:9pt}
  .part{page-break-before:always;padding-top:0}
  .part:first-of-type{page-break-before:auto}
  h1.part-title{font-size:20pt;margin:0 0 4pt;padding-bottom:8pt}
  h2{font-size:13pt;margin:14pt 0 6pt}
  h3{font-size:11.5pt;margin:10pt 0 4pt}
  h4{font-size:10pt;margin:8pt 0 3pt}
  p,li{font-size:10.5pt;margin:5pt 0}
  ul,ol{margin:5pt 0;padding-left:16pt}
  pre.code{font-size:8.5pt;line-height:1.35;padding:8pt 10pt;border-radius:4pt;background:#f5f5f5;page-break-inside:avoid}
  .c-lang{display:none}
  code{border:none;background:#f0f0f0;padding:0 2pt;font-size:.92em;color:#333}
  pre.code code{background:none;padding:0}
  .c-kw{color:#0369a1}.c-str{color:#15803d}.c-num{color:#b45309}.c-com{color:#777}
  table{font-size:9pt;margin:8pt 0}
  th,td{padding:4pt 6pt}
  th{background:#336791;color:#fff}
  .callout{padding:6pt 10pt;margin:8pt 0;font-size:9.5pt;background:#f7f7f7}
  .tblwrap{margin:8pt 0}
  @page{size:letter;margin:12mm 11mm}
}
@media (max-width:860px){
  body{padding-left:0}
  #nav{position:static;width:100%;height:auto;border-right:none;border-bottom:1px solid var(--line)}
  main{padding:24px 18px 80px}
}
"""

JS = r"""
const btn=document.getElementById('themeBtn');
const root=document.documentElement;
try{const t=localStorage.getItem('pg-theme');if(t)root.setAttribute('data-theme',t);}catch(e){}
btn.addEventListener('click',()=>{
  const cur=root.getAttribute('data-theme');
  const next=cur==='dark'?'light':'dark';
  root.setAttribute('data-theme',next);
  try{localStorage.setItem('pg-theme',next);}catch(e){}
  btn.textContent=next==='dark'?'☀ Light':'◐ Dark';
});
// sidebar active highlight on scroll
const links=[...document.querySelectorAll('#nav a[data-part]')];
const obs=new IntersectionObserver(es=>{
  es.forEach(e=>{if(e.isIntersecting){links.forEach(l=>l.classList.remove('on'));const l=links.find(l=>l.getAttribute('data-part')===e.target.id);if(l){l.classList.add('on');l.scrollIntoView({block:'nearest'});}}});
},{rootMargin:'-20% 0px -70% 0px'});
document.querySelectorAll('.part').forEach(p=>obs.observe(p));
"""

def build():
    files = files_in_order()
    nav_items = []
    body_parts = []

    for idx, fname in enumerate(files):
        num_suffix = re.match(r"part_(\d+)(b?)", fname).group(0)
        key = num_suffix[5:]
        label = PART_LABELS.get(key, fname.replace("part_", "").replace(".md", "").replace("_", " ").title())
        anchor = f"part-{key}"
        with open(os.path.join(CONTENT, fname), "r", encoding="utf-8") as f:
            raw = f.read()

        # strip the leading "# PART N: ..." heading; we render our own title
        raw_body = re.sub(r"^#\s+PART\s+\d+[^\n]*\n", "", raw, count=1)
        html_body = parse_md(raw_body)

        body_parts.append(
            f'<section class="part" id="{anchor}">'
            f'<h1 class="part-title">{label}</h1>'
            f'<p class="subtitle">Part {key} — {h.escape(label.lower())}</p>'
            f'{html_body}</section>'
        )
        nav_items.append(f'<a data-part="{anchor}" href="#{anchor}"><small>Part {key}</small>{h.escape(label)}</a>')

    toc_screen = "".join(nav_items)
    # print TOC: two-column list of links
    toc_print_html = (
        '<div class="tocprint"><div class="tpcol">' + "".join(nav_items[:16]) + "</div>"
        '<div class="tpcol">' + "".join(nav_items[16:]) + "</div></div>"
    )

    html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>PostgreSQL Master Handbook</title>
<style>{CSS}</style>
</head>
<body>
<nav id="nav">
  <div class="brand">PostgreSQL<br>Master Handbook</div>
  <div class="top">On this page</div>
  <a href="#top">Contents & Cover</a>
  <div class="top">Parts</div>
  {toc_screen}
</nav>
<button id="themeBtn" title="Toggle theme">◐ Dark</button>
<main id="top">
  <div class="cover">
    <div class="k">The Complete</div>
    <h1>PostgreSQL &amp; Database Engineering</h1>
    <h2>Master Handbook</h2>
    <div class="meta">32 parts · Beginner to Expert · PostgreSQL 17+<br>Print this page (Ctrl/Cmd+P) for the ~200-page PDF edition</div>
  </div>
  {toc_print_html}
  {"".join(body_parts)}
</main>
<script>{JS}</script>
</body>
</html>"""
    # fix broken leftover line above (toc_print variable was unused placeholder)
    html_doc = html_doc  # no-op

    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html_doc)
    size_kb = os.path.getsize(OUT) // 1024
    print(f"OK  wrote {OUT}  ({size_kb} KB, {len(files)} parts)")

if __name__ == "__main__":
    build()
