# PostgreSQL Master Handbook

A comprehensive, professional PDF textbook covering PostgreSQL, SQL, relational
database engineering, database administration, performance optimization,
distributed databases, and cloud (AWS) database technologies.

**Primary reference:** PostgreSQL 17 (latest stable major release at time of
writing).

## Project Structure

```
postgresql-master-handbook/
    content/                        # 32 markdown source files (part_01 … part_32)
    assets/
        diagrams/                  # programmatic diagram outputs
        fonts/                     # optional TTF fonts (Consolas/Cambria)
    scripts/
        generate_pdf.py            # builds both PDFs
        validate_content.py        # checks all 32 parts exist and are non-trivial
        validate_pdf.py           # opens the PDFs and reports page counts
    output/
        PostgreSQL_Database_Engineering_Master_Handbook.pdf
        PostgreSQL_Quick_Reference.pdf
        PostgreSQL_Content_Coverage_Checklist.md
```

## Rebuilding the PDFs

Prerequisites: Python 3.9+ and `reportlab` (and `pymupdf` for validation):

```bash
pip install reportlab
pip install pymupdf        # only needed for validate_pdf.py

python scripts/generate_pdf.py
python scripts/validate_content.py
python scripts/validate_pdf.py
```

`generate_pdf.py` reads every `content/part_*.md` file (except
`part_32_quick_ref.md`, which becomes its own compact PDF) in filename order,
and builds:

1. **PostgreSQL_Database_Engineering_Master_Handbook.pdf** — the full
   textbook: cover, table of contents, all 32 parts, and a references section.
2. **PostgreSQL_Quick_Reference.pdf** — a compact cheat-sheet reference built
   from Part 32.

## Maintaining the Content

- **Edit content** in `content/part_XX_*.md`. Keep headings to `#`–`####`,
  use fenced ``` code blocks, markdown tables, and `>` blockquotes for
  NOTE / WARNING / INTERVIEW callouts.
- **Add a part:** create `content/part_NN_name.md` (two-digit numbering) —
  it is picked up automatically in filename order.
- **Fonts:** the generator uses ReportLab's built-in Helvetica/Courier stack
  (always available). To use Consolas/Cambria, place the `.ttf` files in
  `assets/fonts/` — they are registered automatically if present.
- **The checklist** (`PostgreSQL_Content_Coverage_Checklist.md`) tracks
  topic completion; keep it updated when you add or remove content.

## Content Notes

- Every part states version policies and flags standard-SQL vs
  PostgreSQL-specific features.
- Performance claims are never invented; the book explains how to measure
  actual improvements with `EXPLAIN (ANALYZE, BUFFERS)` and
  `pg_stat_statements` instead of quoting fictitious percentages.
- AWS sections (Part 22) distinguish RDS PostgreSQL from standard PostgreSQL
  and from Aurora; service limitations are stated where documented.
