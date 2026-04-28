import os
from pathlib import Path
import pytest

from testpilot.audit.workbook_index import build_index, normalize_object, normalize_api, WorkbookRow

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "audit"
FIXTURE_PATH = FIXTURE_DIR / "sample_workbook.xlsx"


def make_sample_workbook(path: Path):
    # create a simple workbook using openpyxl
    try:
        import openpyxl
    except Exception as e:
        pytest.skip(f"openpyxl not available: {e}")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Wifi_LLAPI"
    headers = ["Object", "API", "Test Steps", "Command Output", "5G", "6G", "2.4G"]
    ws.append(headers)
    ws.append(["Device .1.", "DoThing", "step1", "out1", "PASS", "FAIL", "PASS"])
    ws.append(["Device .1.", "DoThing", "step2", "out2", "", "PASS", "FAIL"])
    ws.append(["OtherDevice.", "OtherAPI", "s", "o", "FAIL", "PASS", "PASS"])
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def test_normalize_object_examples():
    assert normalize_object(' Device .1. ') == 'Device .{i}'
    assert normalize_object('Foo.Bar.2.3.') == 'Foo.Bar.{i}.3'  # only the .<num>. pattern
    assert normalize_object('NoChange') == 'NoChange'


def test_normalize_api_examples():
    assert normalize_api(' DoThing ') == 'DoThing'
    assert normalize_api('doThing') == 'doThing'  # preserve case


def test_build_index_groups_rows(tmp_path):
    # ensure fixture exists
    if not FIXTURE_PATH.exists():
        make_sample_workbook(FIXTURE_PATH)

    idx = build_index(str(FIXTURE_PATH))
    # key should be (normalized_object, normalized_api)
    key = ('Device .{i}', 'DoThing')
    assert key in idx
    rows = idx[key]
    assert isinstance(rows, list)
    assert len(rows) == 2
    assert rows[0].row_index == 2
    assert rows[1].row_index == 3
    assert rows[0].result_5g == 'PASS'
    assert rows[1].result_6g == 'PASS'

    other_key = ('OtherDevice', 'OtherAPI')
    assert other_key in idx
    assert len(idx[other_key]) == 1


def test_build_index_column_overrides():
    # Create a workbook with different header names
    try:
        import openpyxl
    except Exception as e:
        pytest.skip(f"openpyxl not available: {e}")
    p = Path(tmp_path:=Path('.')) / 'temp_workbook.xlsx'
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Wifi_LLAPI'
    headers = ['OBJ', 'API_NAME', 'Steps', 'CmdOut', '5G', '6G', '2.4G']
    ws.append(headers)
    ws.append(['X', 'Y', 's', 'o', 'P', '', 'F'])
    wb.save(p)

    # pass overrides mapping header substring -> desired field name
    overrides = {'OBJ': 'object', 'API_NAME': 'api', 'Steps': 'test_steps', 'CmdOut': 'command_output'}
    idx = build_index(str(p), column_overrides=overrides)
    assert ('X', 'Y') in idx
