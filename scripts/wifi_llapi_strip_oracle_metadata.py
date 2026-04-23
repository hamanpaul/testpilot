#!/usr/bin/env python3
"""Strip wifi_llapi oracle metadata migration script.
"""
from __future__ import annotations
import argparse
from pathlib import Path
try:
    from ruamel.yaml import YAML
    YAML_AVAILABLE = True
except Exception:
    YAML_AVAILABLE = False


def process_file(path: Path, apply: bool, yaml: YAML | None):
    # Prefer ruamel if available
    if YAML_AVAILABLE and yaml is not None:
        data = yaml.load(path.read_text())
        if data is None:
            data = {}
        removed = []
        # top-level results_reference
        if isinstance(data, dict) and "results_reference" in data:
            removed.append("results_reference")
            data.pop("results_reference", None)
        # source-level if mapping
        src = data.get("source") if isinstance(data, dict) else None
        if isinstance(src, dict):
            for key in ("baseline", "report", "sheet"):
                if key in src:
                    removed.append(f"source.{key}")
                    src.pop(key, None)
        # write if apply and removed
        if removed and apply:
            # write preserving formatting
            with path.open("w", encoding="utf-8") as f:
                yaml.dump(data, f)
        return removed
    # Fallback: text-based conservative removal to avoid dependency
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    removed = []
    out_lines = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        # detect top-level results_reference (no leading space)
        if line.startswith("results_reference:") or line.startswith("results_reference :"):
            removed.append("results_reference")
            i += 1
            continue
        # detect top-level source:
        if line.startswith("source:"):
            # lookahead to see if mapping (next line indented)
            j = i + 1
            if j < n and (lines[j].startswith(" ") or lines[j].startswith("\t")):
                # keep the source: line
                out_lines.append(line)
                i += 1
                # process indented block
                while i < n and (lines[i].startswith(" ") or lines[i].startswith("\t")):
                    stripped = lines[i].lstrip()
                    # split key by colon
                    key = stripped.split(":", 1)[0]
                    if key in ("baseline", "report", "sheet"):
                        removed.append(f"source.{key}")
                        i += 1
                        continue
                    else:
                        out_lines.append(lines[i])
                        i += 1
                continue
            else:
                # scalar source, keep as-is
                out_lines.append(line)
                i += 1
                continue
        # default keep line
        out_lines.append(line)
        i += 1
    if removed and apply:
        path.write_text("\n".join(out_lines) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")
    return removed


def main(argv: list[str] | None = None):
    parser = argparse.ArgumentParser(description="Strip wifi_llapi oracle metadata")
    parser.add_argument("--apply", action="store_true", help="Apply changes in-place")
    parser.add_argument("--cases-dir", default="plugins/wifi_llapi/cases", help="Directory with case YAMLs")
    args = parser.parse_args(argv)

    if YAML_AVAILABLE:
        yaml = YAML(typ='rt')
        yaml.default_flow_style = False
    else:
        yaml = None

    cases_dir = Path(args.cases_dir)
    files = sorted(cases_dir.glob("*.yaml")) if cases_dir.exists() else []
    scanned = 0
    modified = 0
    clean = 0
    for p in files:
        scanned += 1
        try:
            removed = process_file(p, args.apply, yaml)
        except Exception:
            # skip unreadable
            removed = []
        if removed:
            print(f"{p}: removed [{', '.join(removed)}]")
            modified += 1
        else:
            clean += 1
    print(f"{scanned} files scanned, {modified} modified, {clean} already clean")


if __name__ == '__main__':
    main()
