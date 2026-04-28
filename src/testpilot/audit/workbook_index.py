from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple
import re

try:
    import openpyxl
except Exception:  # pragma: no cover - tests skip if openpyxl missing
    openpyxl = None


@dataclass
class WorkbookRow:
    row_index: int
    object: str
    api: str
    test_steps: Optional[str]
    command_output: Optional[str]
    result_5g: Optional[str]
    result_6g: Optional[str]
    result_24g: Optional[str]


def normalize_object(value: Optional[str]) -> str:
    if value is None:
        return ''
    s = str(value).strip()
    if not s:
        return ''
    # Collapse occurrences like .1. to .{i}.
    s = re.sub(r"\.(\d+)\.", ".{i}.", s)
    # strip trailing dot
    if s.endswith('.'):
        s = s[:-1]
    return s


def normalize_api(value: Optional[str]) -> str:
    if value is None:
        return ''
    return str(value).strip()


def _detect_columns(headers: List[str], column_overrides: Optional[Dict[str, str]] = None) -> Dict[str, int]:
    # headers: list of header strings, 1-based indexing for columns
    mapping: Dict[str, int] = {}
    low_headers = [ (i+1, (h or '').strip()) for i, h in enumerate(headers) ]
    # apply overrides first
    if column_overrides:
        for key, desired in column_overrides.items():
            # find exact header match
            for col, h in low_headers:
                if h == key:
                    mapping[desired] = col
                    break
    # helper to find by substring
    def find_substr(subs: List[str]) -> Optional[int]:
        for col, h in low_headers:
            hl = h.lower()
            for sub in subs:
                if sub in hl:
                    return col
        return None

    if 'object' not in mapping:
        col = find_substr(['object'])
        if col:
            mapping['object'] = col
    if 'api' not in mapping:
        col = find_substr(['api'])
        if col:
            mapping['api'] = col
    if 'test_steps' not in mapping:
        col = find_substr(['test steps', 'test_steps', 'steps', 'test'])
        if col:
            mapping['test_steps'] = col
    if 'command_output' not in mapping:
        col = find_substr(['command output', 'command_output', 'command', 'output', 'cmd'])
        if col:
            mapping['command_output'] = col
    # results
    if 'result_5g' not in mapping:
        col = find_substr(['5g'])
        if col:
            mapping['result_5g'] = col
    if 'result_6g' not in mapping:
        col = find_substr(['6g'])
        if col:
            mapping['result_6g'] = col
    if 'result_24g' not in mapping:
        col = find_substr(['2.4', '2_4', '24g', '2.4g'])
        if col:
            mapping['result_24g'] = col

    return mapping


def build_index(workbook_path: str, *, sheet_name: str = 'Wifi_LLAPI', column_overrides: Optional[Dict[str, str]] = None) -> Dict[Tuple[str, str], List[WorkbookRow]]:
    if openpyxl is None:
        raise RuntimeError('openpyxl is required to build index')
    wb = openpyxl.load_workbook(workbook_path, read_only=True, data_only=True)
    if sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
    else:
        ws = wb.active

    # read header (first row)
    headers = []
    for cell in next(ws.iter_rows(min_row=1, max_row=1)):
        headers.append(cell.value or '')
    col_map = _detect_columns(headers, column_overrides=column_overrides)

    index: Dict[Tuple[str, str], List[WorkbookRow]] = {}

    for row in ws.iter_rows(min_row=2):
        # get values by column if present
        def get_col(name: str) -> Optional[str]:
            col = col_map.get(name)
            if col is None:
                return ''
            cell = row[col-1]
            return cell.value if cell.value is not None else ''

        raw_object = get_col('object')
        raw_api = get_col('api')
        norm_obj = normalize_object(raw_object)
        norm_api = normalize_api(raw_api)
        test_steps = get_col('test_steps')
        cmd_out = get_col('command_output')
        r5 = get_col('result_5g')
        r6 = get_col('result_6g')
        r24 = get_col('result_24g')

        # row index relative to sheet (1-based)
        row_index = row[0].row
        wb_row = WorkbookRow(
            row_index=row_index,
            object=norm_obj,
            api=norm_api,
            test_steps=test_steps,
            command_output=cmd_out,
            result_5g=r5,
            result_6g=r6,
            result_24g=r24,
        )
        key = (norm_obj, norm_api)
        index.setdefault(key, []).append(wb_row)

    return index
