import os
import shutil
import subprocess
import sys
from pathlib import Path
import tempfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "wifi_llapi_strip_oracle_metadata.py"


def run_script(cases_dir, apply=False):
    cmd = [sys.executable, str(SCRIPT)]
    if apply:
        cmd.append("--apply")
    cmd.extend(["--cases-dir", str(cases_dir)])
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr



def write_yaml(path: Path, text: str):
    path.write_text(text, encoding="utf-8")


def read_text(path: Path):
    return path.read_text(encoding="utf-8")


@pytest.fixture
def tmp_cases_dir(tmp_path):
    d = tmp_path / "cases"
    d.mkdir()
    return d


def test_dry_run_no_write(tmp_cases_dir):
    y = tmp_cases_dir / "case1.yaml"
    write_yaml(y, """# case comment
id: D001
results_reference: fake
source:
  object: some
  api: action
  baseline: to-remove
  report: to-remove
  sheet: to-remove
  row: 5
""")
    rc, out, err = run_script(tmp_cases_dir, apply=False)
    assert rc == 0
    assert "removed [results_reference, source.baseline, source.report, source.sheet]" in out
    # file unchanged
    txt = read_text(y)
    assert "baseline: to-remove" in txt


def test_apply_removes_keys(tmp_cases_dir):
    y = tmp_cases_dir / "case2.yaml"
    write_yaml(y, """#cm
name: test
results_reference: r
source:
  object: o
  api: a
  baseline: b
  report: rep
  sheet: s
  row: 7
""")
    rc, out, err = run_script(tmp_cases_dir, apply=True)
    assert rc == 0
    # file changed
    txt = read_text(y)
    assert "results_reference" not in txt
    assert "baseline:" not in txt
    assert "report:" not in txt
    assert "sheet:" not in txt
    # preserve identifiers
    assert "row: 7" in txt
    assert "object: o" in txt
    assert "api: a" in txt


def test_idempotence(tmp_cases_dir):
    y = tmp_cases_dir / "case3.yaml"
    write_yaml(y, """id: D
results_reference: x
source:
  baseline: b
  row: 2
""")
    # apply first time
    rc, out, err = run_script(tmp_cases_dir, apply=True)
    assert rc == 0
    assert "modified" in out
    # apply second time => already clean
    rc2, out2, err2 = run_script(tmp_cases_dir, apply=True)
    assert rc2 == 0
    assert "0 files scanned, 0 modified, 1 already clean" in out2 or "already clean" in out2


def test_preserve_comments_and_order(tmp_cases_dir):
    y = tmp_cases_dir / "case4.yaml"
    write_yaml(y, """# top comment
id: D
# mid comment
source:
  # src comment
  object: o
  baseline: b
  report: rep
other: val
""")
    rc, out, err = run_script(tmp_cases_dir, apply=True)
    txt = read_text(y)
    # comments preserved
    assert "# top comment" in txt
    assert "# src comment" in txt
    # other key preserved and order: other should come after source
    assert "other: val" in txt


def test_source_not_mapping(tmp_cases_dir):
    y = tmp_cases_dir / "case5.yaml"
    write_yaml(y, """id: X
results_reference: r
source: some-string
""")
    rc, out, err = run_script(tmp_cases_dir, apply=True)
    assert rc == 0
    txt = read_text(y)
    assert "results_reference" not in txt
    # source should remain as scalar
    assert "source: some-string" in txt


