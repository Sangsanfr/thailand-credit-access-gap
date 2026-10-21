"""Parsers for Bank of Thailand statistics files (D2 district reports, D3/D4 wide province tables)."""
import re, glob, os, openpyxl, pandas as pd

TH_MONTH = {'มค':1,'กพ':2,'มีค':3,'เมย':4,'พค':5,'มิย':6,'กค':7,'สค':8,'กย':9,'ตค':10,'พย':11,'ธค':12}

def parse_period(label):
    """'ม.ค. 2556 r' / 'ธ.ค.49(แก้ไข)' / 'มค 63' -> (year_be, month) or None"""
    s = re.sub(r'[\s\.]', '', str(label))
    q = re.match(r'^Q([1-4])/(\d{4})', s)
    if q: return int(q.group(2)), int(q.group(1)) * 3   # quarter -> last month of quarter
    m = re.match(r'^(มค|กพ|มีค|เมย|พค|มิย|กค|สค|กย|ตค|พย|ธค)(\d{2,4})', s)
    if not m: return None
    y = int(m.group(2)); y = y + 2500 if y < 100 else y
    return y, TH_MONTH[m.group(1)]

def num(v):
    """BOT convention: '-' = zero, 'n.a.' = suppressed (None), blank = missing (None)."""
    if isinstance(v, str) and v.strip() == '-': return 0.0
    if v is None or (isinstance(v, str) and v.strip() in ('', 'n.a.')): return None
    if isinstance(v, (int, float)): return float(v)
    try: return float(str(v).replace(',', ''))
    except ValueError: return None

def read_bot_wide(path):
    """BOT BTWS 'ALL' export: months across columns, continued over sheets 'Monthly', 'Monthly (2)'... -> long df."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out = []
    for sn in wb.sheetnames:
        rows = [list(r) for r in wb[sn].iter_rows(values_only=True)]
        hi = next((i for i, r in enumerate(rows[:15]) if any(parse_period(v) for v in r[2:] if v)), None)
        if hi is None: continue  # e.g. 'Quarterly' sheet
        per_row, fld_row = rows[hi], rows[hi + 1]
        cur = None; colmap = {}
        for j in range(2, len(fld_row)):
            p = parse_period(per_row[j]) if j < len(per_row) and per_row[j] else None
            if p: cur = p
            if cur and fld_row[j]: colmap[j] = (cur, re.sub(r'\s+', ' ', str(fld_row[j])).strip())
        for r in rows[hi + 2:]:
            if r[0] is None or not str(r[0]).strip().isdigit() or r[1] is None: continue
            name = str(r[1]); level = len(name) - len(name.lstrip())
            for j, ((y, m), fld) in colmap.items():
                if j < len(r): out.append((sn, int(r[0]), name.strip(), level, y, m, fld, num(r[j])))
    return pd.DataFrame(out, columns=['sheet','row','area','indent','year_be','month','field','value'])

def read_d2_sheet(ws):
    rows = [r for r in ws.iter_rows(values_only=True)]
    out = []
    for r in rows:
        k = str(r[0] or '').strip()
        m = re.match(r'^(\d{6})\s+(.*)$', k)
        if m: out.append((m.group(1)[:4], m.group(2).strip(), [num(v) for v in r[1:] if v is not None]))
        elif 'สำนักงานใหญ่' in k: out.append(('HQ', 'สำนักงานใหญ่', [num(v) for v in r[1:] if v is not None]))
    return out
