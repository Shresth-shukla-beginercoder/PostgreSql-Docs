import os
import re
import html

# Configuration
CONTENT_DIR = "content"
OUTPUT_FILE = "output/THE_POSTGRESQL_MASTER_HANDBOOK.html"

# Ensure output directory exists
os.makedirs("output", exist_ok=True)

def md_to_html(md_text):
    # Escape HTML characters first
    text = html.escape(md_text)

    # Code blocks (```sql ... ```)
    def code_block_repl(match):
        code = match.group(2).strip()
        return f'<pre><code>{code}</code></pre>'
    text = re.sub(r'```(\w*)\n(.*?)\n```', code_block_repl, text, flags=re.DOTALL)

    # Inline code (`code`)
    text = re.sub(r'`([^`]+)`', r'<code>\1</code>', text)

    # Headings
    text = re.sub(r'^# (.*)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.*)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^### (.*)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^#### (.*)$', r'<h4>\1</h4>', text, flags=re.MULTILINE)

    # Bold
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)

    # Lists (Unordered)
    text = re.sub(r'^\* (.*)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    text = re.sub(r'^- (.*)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    # Wrap li in ul (simple hack)
    text = re.sub(r'((<li>.*</li>\n?)+)', r'<ul>\1</ul>', text)

    # Tables
    def table_repl(match):
        rows = match.group(0).strip().split('\n')
        html_table = '<table>'
        for i, row in enumerate(rows):
            if '|---' in row: continue
            cells = [c.strip() for c in row.split('|') if c.strip()]
            tag = 'th' if i == 0 else 'td'
            html_table += '<tr>' + ''.join(f'<{tag}>{c}</{tag}>' for c in cells) + '</tr>'
        html_table += '</table>'
        return html_table
    text = re.sub(r'(\|.*\|.*\n)+', table_repl, text)

    # Paragraphs (everything else)
    # This is a basic split by double newline
    parts = text.split('\n\n')
    new_parts = []
    for p in parts:
        p = p.strip()
        if not p: continue
        if p.startswith('<h') or p.startswith('<pre') or p.startswith('<ul') or p.startswith('<table'):
            new_parts.append(p)
        else:
            new_parts.append(f'<p>{p.replace("\n", "<br>")}</p>')

    return '\n'.join(new_parts)

def generate():
    files = sorted([f for f in os.listdir(CONTENT_DIR) if f.endswith(".md")])

    # Order files logically by part number
    def sort_key(f):
        match = re.search(r'part_(\d+)', f)
        if match: return int(match.group(1))
        if '02b' in f: return 2.5
        return 999
    files.sort(key=sort_key)

    full_html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PostgreSQL Master Handbook</title>
    <style>
        body { font-family: 'Segoe UI', system-ui, sans-serif; line-height: 1.6; color: #1f2937; max-width: 1000px; margin: 0 auto; padding: 40px; background: #fff; }
        h1 { color: #336791; font-size: 3.5em; text-align: center; border-bottom: 8px solid #336791; padding-bottom: 20px; margin-top: 100px; }
        h2 { color: #336791; font-size: 2.2em; border-bottom: 2px solid #e2e8f0; margin-top: 60px; padding-bottom: 10px; page-break-before: always; }
        h3 { color: #475569; font-size: 1.6em; margin-top: 40px; }
        p { margin-bottom: 1.2em; font-size: 1.1em; }
        pre { background: #0f172a; color: #f8fafc; padding: 20px; border-radius: 8px; overflow-x: auto; font-family: 'Consolas', 'Monaco', monospace; line-height: 1.4; margin: 20px 0; }
        code { background: #f1f5f9; color: #e11d48; padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 0.9em; }
        pre code { background: transparent; color: inherit; padding: 0; }
        table { width: 100%; border-collapse: collapse; margin: 30px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        th, td { border: 1px solid #e2e8f0; padding: 12px 15px; text-align: left; }
        th { background: #336791; color: white; font-weight: 600; }
        tr:nth-child(even) { background: #f8fafc; }
        ul { margin-bottom: 1.2em; padding-left: 25px; }
        li { margin-bottom: 0.5em; font-size: 1.1em; }
        .cover { text-align: center; height: 90vh; display: flex; flex-direction: column; justify-content: center; border: 20px solid #336791; margin-bottom: 50px; }
        @media print {
            body { padding: 0; width: 100%; }
            .no-print { display: none; }
        }
    </style>
</head>
<body>
    <div class="cover">
        <p style="font-size: 1.5em; letter-spacing: 0.3em; color: #64748b;">THE COMPLETE</p>
        <h1 style="border:none; margin: 0;">POSTGRESQL & DATABASE ENGINEERING</h1>
        <h2 style="border:none; margin: 0; page-break-before: auto;">MASTER HANDBOOK</h2>
        <p style="margin-top: 50px; font-size: 1.4em; color: #475569;">Expert Level • PostgreSQL 17+ • SQL Mastery</p>
    </div>
"""

    for filename in files:
        path = os.path.join(CONTENT_DIR, filename)
        print(f"Processing {filename}...")
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
            html_content = md_to_html(content)
            full_html += f'<div class="section">{html_content}</div>'

    full_html += "</body></html>"

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(full_html)

    print(f"Success! Handbook generated at {OUTPUT_FILE}")

if __name__ == "__main__":
    generate()
