"""Build the versioned MoHan character-content inventory."""

from __future__ import annotations

lazy import argparse
lazy import sys
lazy from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

lazy from tools import mohan_character_inventory as _adapter

DIRECT = _adapter.DIRECT
EMBEDDED = _adapter.EMBEDDED
SOURCE_ROOTS = _adapter.SOURCE_ROOTS
IMAGE_SUFFIXES = _adapter.IMAGE_SUFFIXES
MEDIUM_EVIDENCE_THRESHOLD = _adapter.MEDIUM_EVIDENCE_THRESHOLD
HIGH_EVIDENCE_THRESHOLD = _adapter.HIGH_EVIDENCE_THRESHOLD
NON_PRODUCT_ROOTS = _adapter.NON_PRODUCT_ROOTS
CATEGORY_LABELS = _adapter.CATEGORY_LABELS
Group = _adapter.Group
ContentRule = _adapter.ContentRule
GROUPS = _adapter.GROUPS
MANUAL_REVIEW_HINTS = _adapter.MANUAL_REVIEW_HINTS
CONTENT_RULES = _adapter.CONTENT_RULES
PRODUCT_SHELL_ALLOWLIST = _adapter.PRODUCT_SHELL_ALLOWLIST
PRODUCT_IDENTITY_LITERAL = _adapter.PRODUCT_IDENTITY_LITERAL
PRODUCT_IDENTITY_RULE = _adapter.PRODUCT_IDENTITY_RULE
PRODUCT_IDENTITY_REASON = _adapter.PRODUCT_IDENTITY_REASON
UI_TEXT_REFERENCE_PATHS = _adapter.UI_TEXT_REFERENCE_PATHS
CLASSIFICATION_REASONS = _adapter.CLASSIFICATION_REASONS
WORK_PACKAGE_DEFINITIONS = _adapter.WORK_PACKAGE_DEFINITIONS

source_evidence = _adapter.source_evidence
file_metadata = _adapter.file_metadata
manifest_references = _adapter.manifest_references
_reference_index = _adapter._reference_index
_excluded_scope = _adapter._excluded_scope
_asset_scope = _adapter._asset_scope
_fullbody_category = _adapter._fullbody_category
_readers = _adapter._readers
_pack_members = _adapter._pack_members
_python_sources = _adapter._python_sources
_parsed_python = _adapter._parsed_python
_docstring_nodes = _adapter._docstring_nodes
_match_line = _adapter._match_line
_fstring_templates = _adapter._fstring_templates
_product_identity_spans = _adapter._product_identity_spans
_content_evidence = _adapter._content_evidence
_top_level_symbols = _adapter._top_level_symbols
_source_classification = _adapter._source_classification
_source_difficulty = _adapter._source_difficulty
_work_package = _adapter._work_package
_code_records = _adapter._code_records
_manual_review_hints = _adapter._manual_review_hints
build_inventory = _adapter.build_inventory
render_inventory = _adapter.render_inventory
_worklist_item = _adapter._worklist_item
build_extraction_worklist = _adapter.build_extraction_worklist
render_extraction_worklist = _adapter.render_extraction_worklist
render_extraction_summary = _adapter.render_extraction_summary
render_summary = _adapter.render_summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "docs/character-pack")
    args = parser.parse_args(argv)
    inventory = build_inventory()
    worklist = build_extraction_worklist(inventory)
    outputs = {
        "mohan-inventory.json": render_inventory(inventory),
        "mohan-inventory-summary.md": render_summary(inventory),
        "extraction-worklist.json": render_extraction_worklist(worklist),
        "extraction-worklist.md": render_extraction_summary(worklist),
    }
    if args.check:
        for name, expected in outputs.items():
            path = args.output_dir / name
            if not path.is_file() or path.read_text(encoding="utf-8") != expected:
                print(f"CHARACTER_INVENTORY_STALE={name}")
                return 1
        print("CHARACTER_INVENTORY_MATCH")
        return 0
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, text in outputs.items():
        (args.output_dir / name).write_text(text, encoding="utf-8", newline="\n")
    print("CHARACTER_INVENTORY_WRITTEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
