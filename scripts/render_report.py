#!/usr/bin/env python3
"""
Render a category-research report HTML from data/{slug}.json + template.

Pipeline:
  1. Load data/{slug}.json
  2. Validate against schema (calls validate_data.py module-level functions)
  3. Substitute inline JSON block in templates/lens-report-template.html
  4. Write dist/{slug}.html

Usage:
    python scripts/render_report.py health-ring
    python scripts/render_report.py --all
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from validate_data import (  # type: ignore
    load_schema,
    validate_schema,
    check_cross_refs,
    check_evidence_gates,
)

TEMPLATE_PATH = ROOT / "templates" / "lens-report-template.html"
DATA_DIR = ROOT / "data"
DIST_DIR = ROOT / "dist"

# The marker we substitute. Template has:
#   <script type="application/json" id="report-data">{{REPORT_DATA_JSON}}</script>
DATA_MARKER = "{{REPORT_DATA_JSON}}"


def render(slug: str, *, skip_validate: bool = False) -> Path:
    data_path = DATA_DIR / f"{slug}.json"
    if not data_path.exists():
        sys.exit(f"✗ {data_path} not found")

    # Validate
    if not skip_validate:
        data = json.loads(data_path.read_text(encoding="utf-8"))
        schema = load_schema()
        errs = validate_schema(data, schema) + check_cross_refs(data)
        if errs:
            for e in errs:
                print(f"✗ {e}", file=sys.stderr)
            sys.exit(f"✗ validation failed for {slug} — refusing to render")
        check_evidence_gates(data)  # warnings only

    # Load template
    template_html = TEMPLATE_PATH.read_text(encoding="utf-8")
    if DATA_MARKER not in template_html:
        sys.exit(f"✗ template missing {DATA_MARKER} placeholder — did you template-ize it?")

    # Substitute
    data_json = data_path.read_text(encoding="utf-8").strip()
    rendered = template_html.replace(DATA_MARKER, data_json)

    # Write
    DIST_DIR.mkdir(exist_ok=True)
    out = DIST_DIR / f"{slug}.html"
    out.write_text(rendered, encoding="utf-8")
    size_kb = out.stat().st_size / 1024
    print(f"✓ {out.relative_to(ROOT)}  ({size_kb:.1f} KB)")
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("slug", nargs="?", help="Slug to render (e.g. health-ring)")
    p.add_argument("--all", action="store_true", help="Render every data/*.json")
    p.add_argument("--skip-validate", action="store_true", help="Skip schema/xref validation")
    args = p.parse_args()

    if args.all:
        slugs = sorted(f.stem for f in DATA_DIR.glob("*.json"))
        if not slugs:
            sys.exit("✗ no data files in data/")
    elif args.slug:
        slugs = [args.slug]
    else:
        p.print_help()
        return 2

    for slug in slugs:
        render(slug, skip_validate=args.skip_validate)
    return 0


if __name__ == "__main__":
    sys.exit(main())
