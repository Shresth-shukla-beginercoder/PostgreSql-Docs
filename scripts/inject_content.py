#!/usr/bin/env python3
"""
Injects every content/*.md into the matching <script type="text/markdown">
block of output/PostgreSQL_Master_Handbook.html, producing one fully
self-contained HTML file. No dependencies beyond the standard library.

Run from the project root:
    python scripts/inject_content.py
"""
import os, re, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(BASE, "content")
TEMPLATE = os.path.join(BASE, "output", "PostgreSQL_Master_Handbook.html")

# Map md-file -> script-block id
FILES = {
    "part_01_foundations.md":"01","part_02_ddl.md":"02",
    "part_02b_dml_dcl_tcl.md":"02b","part_03_keywords.md":"03",
    "part_04_joins.md":"04","part_05_subqueries.md":"05",
    "part_06_functions.md":"06","part_07_window.md":"07",
    "part_08_datatypes.md":"08","part_09_constraints.md":"09",
    "part_10_design.md":"10","part_11_indexing.md":"11",
    "part_12_performance.md":"12","part_13_transactions.md":"13",
    "part_14_locking.md":"14","part_15_functions_triggers.md":"15",
    "part_16_json.md":"16","part_17_partitioning.md":"17",
    "part_18_security.md":"18","part_19_admin.md":"19",
    "part_20_backup_recovery.md":"20","part_21_replication.md":"21",
    "part_22_aws.md":"22","part_23_other_tech.md":"23",
    "part_24_extensions.md":"24","part_25_backend.md":"25",
    "part_26_case_studies.md":"26","part_27_interviews.md":"27",
    "part_28_practice.md":"28","part_29_advanced.md":"29",
    "part_30_monitoring.md":"30","part_31_glossary.md":"31",
    "part_32_quick_ref.md":"32",
}

def main():
    with open(TEMPLATE, encoding="utf-8") as f:
        html = f.read()

    missing = []
    for fname, key in FILES.items():
        path = os.path.join(CONTENT, fname)
        if not os.path.exists(path):
            missing.append(fname)
            continue
        with open(path, encoding="utf-8") as f:
            md = f.read()
        # Guard: raw markdown must not contain the literal closing tag.
        md = md.replace("</script>", "<\\u002Fscript>")
        block_re = re.compile(r'(<script type="text/markdown" id="md-%s">)(.*?)(</script>)' % re.escape(key), re.S)
        m = block_re.search(html)
        if not m:
            print("WARN: no block for", fname)
            continue
        # Keep content between the tags (drop any placeholder).
        html = block_re.sub(lambda mm: mm.group(1) + md + mm.group(3), html, count=1)

    with open(TEMPLATE, "w", encoding="utf-8") as f:
        f.write(html)

    size = os.path.getsize(TEMPLATE)
    print(f"Injected {len(FILES)-len(missing)} of {len(FILES)} parts.")
    if missing:
        print("Missing files:", missing)
    print(f"Self-contained HTML written: {TEMPLATE} ({size//1024} KB)")

if __name__ == "__main__":
    main()
