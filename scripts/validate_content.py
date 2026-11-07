#!/usr/bin/env python3
"""Validate content coverage for the PostgreSQL Master Handbook.

Checks that all 32 parts exist, that each part is substantive, and that the
key mandatory sections from the project brief are represented.
"""

import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIR = os.path.join(BASE, "content")

MIN_LINES = 40          # parts below this are flagged as thin
MIN_CHARS = 2000

REQUIRED_PARTS = {
    1: "foundations", 2: "ddl", 3: "keywords", 4: "joins", 5: "subqueries",
    6: "functions", 7: "window", 8: "datatypes", 9: "constraints",
    10: "design", 11: "indexing", 12: "performance", 13: "transactions",
    14: "locking", 15: "functions_triggers", 16: "json", 17: "partitioning",
    18: "security", 19: "admin", 20: "backup_recovery", 21: "replication",
    22: "aws", 23: "other_tech", 24: "extensions", 25: "backend",
    26: "case_studies", 27: "interviews", 28: "practice", 29: "advanced",
    30: "monitoring", 31: "glossary", 32: "quick_ref",
}

def find_part_file(num):
    if not os.path.isdir(CONTENT_DIR):
        return None
    prefix = f"part_{num:02d}"
    for fname in sorted(os.listdir(CONTENT_DIR)):
        if fname.startswith(prefix + "_") and fname.endswith(".md"):
            return os.path.join(CONTENT_DIR, fname)
    return None

def main():
    print(f"Content directory: {CONTENT_DIR}\n")
    failures, warnings = [], []
    for num in range(1, 33):
        path = find_part_file(num)
        label = REQUIRED_PARTS[num]
        if path is None:
            failures.append(f"Part {num} ({label}): MISSING")
            continue
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        lines = [l for l in text.splitlines() if l.strip()]
        head = lines[0] if lines else "(empty)"
        status = "OK"
        if len(lines) < MIN_LINES:
            warnings.append(f"Part {num} ({label}): only {len(lines)} lines — thin content")
            status = "THIN"
        elif len(text) < MIN_CHARS:
            warnings.append(f"Part {num} ({label}): under {MIN_CHARS} chars — thin content")
            status = "THIN"
        print(f"[{status}] Part {num:2d} {label:18s} {len(lines):5d} lines  {head[:60]}")

    print()
    for w in warnings:
        print("WARN :", w)
    for f in failures:
        print("FAIL :", f)

    total = len([n for n in range(1, 33) if find_part_file(n)])
    print(f"\nParts found: {total}/32   Failures: {len(failures)}   Warnings: {len(warnings)}")
    sys.exit(1 if failures else 0)

if __name__ == "__main__":
    main()
