#!/usr/bin/env python3
"""Auditoria estrutural genérica de workbooks XLSX (OOXML).

Le apenas metadados estruturais e estatisticas agregadas de cada
workbook (abas, formulas, dependencias, qualidade) e grava os
resultados em arquivos CSV/Markdown no diretorio de saida indicado.
Nao contem nomes de arquivo, caminhos absolutos, hashes ou valores de
planilha especificos de nenhum projeto - todos esses dados chegam via
argumentos de linha de comando em tempo de execucao.

Usa somente a biblioteca padrao do Python (zipfile, xml.etree) para
nao introduzir uma dependencia externa no repositorio.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import difflib
import re
import statistics
import sys
import unicodedata
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

NS_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS_PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
NS_CORE = "http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
NS_DC = "http://purl.org/dc/elements/1.1/"
NS_DCTERMS = "http://purl.org/dc/terms/"
NS_EXTENDED = "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"

BUILTIN_DATE_NUMFMT_IDS = set(range(14, 23)) | {45, 46, 47}

CELL_REF_RE = re.compile(r"(\$?)([A-Z]{1,3})(\$?)(\d+)")
SHEET_REF_RE = re.compile(r"(?:'([^']+)'|([A-Za-z_][A-Za-z0-9_. ]*))!")
COL_LETTERS_RE = re.compile(r"^([A-Z]+)(\d+)$")

PII_PATTERNS = {
    "cpf": re.compile(r"^\d{3}\.?\d{3}\.?\d{3}-?\d{2}$"),
    "telefone": re.compile(r"^(\+?55)?\s*\(?\d{2}\)?\s*\d{4,5}-?\d{4}$"),
    "email": re.compile(r"^[^@\s]+@[^@\s]+\.[a-zA-Z]{2,}$"),
}
PII_HEADER_HINTS = (
    "cpf", "cnpj", "telefone", "celular", "email", "e-mail",
    "nome", "cliente", "comprador", "rg", "identidade", "endereco",
    "endereço",
)


def q(tag: str) -> str:
    return f"{{{NS_MAIN}}}{tag}"


def local(tag: str) -> str:
    return tag.split("}")[-1]


def col_letters_to_index(letters: str) -> int:
    idx = 0
    for ch in letters:
        idx = idx * 26 + (ord(ch) - ord("A") + 1)
    return idx


def split_cell_ref(ref: str) -> tuple[str, int]:
    m = COL_LETTERS_RE.match(ref)
    if not m:
        return ref, 0
    return m.group(1), int(m.group(2))


class Zip:
    def __init__(self, path: Path):
        self.path = path
        self.zf = zipfile.ZipFile(path, "r")
        self.names = set(self.zf.namelist())

    def has(self, name: str) -> bool:
        return name in self.names

    def names_starting(self, prefix: str) -> list[str]:
        return sorted(n for n in self.names if n.startswith(prefix))

    def xml(self, name: str):
        if name not in self.names:
            return None
        with self.zf.open(name) as fh:
            data = fh.read()
        try:
            return ET.fromstring(data)
        except ET.ParseError:
            return None

    def size(self, name: str) -> int:
        return self.zf.getinfo(name).file_size


# ---------------------------------------------------------------- parsing --

def parse_shared_strings(z: Zip) -> list[str]:
    root = z.xml("xl/sharedStrings.xml")
    if root is None:
        return []
    out = []
    for si in root.findall(q("si")):
        parts = []
        t = si.find(q("t"))
        if t is not None and t.text:
            parts.append(t.text)
        for r in si.findall(q("r")):
            rt = r.find(q("t"))
            if rt is not None and rt.text:
                parts.append(rt.text)
        out.append("".join(parts))
    return out


def parse_styles(z: Zip) -> tuple[dict[int, int], dict[int, str]]:
    """Retorna (cellXf_index -> numFmtId, numFmtId customizado -> formatCode)."""
    root = z.xml("xl/styles.xml")
    if root is None:
        return {}, {}
    custom_fmts: dict[int, str] = {}
    num_fmts_el = root.find(q("numFmts"))
    if num_fmts_el is not None:
        for nf in num_fmts_el.findall(q("numFmt")):
            try:
                fmt_id = int(nf.get("numFmtId"))
            except (TypeError, ValueError):
                continue
            custom_fmts[fmt_id] = nf.get("formatCode", "")
    xf_to_numfmt: dict[int, int] = {}
    cell_xfs = root.find(q("cellXfs"))
    if cell_xfs is not None:
        for i, xf in enumerate(cell_xfs.findall(q("xf"))):
            try:
                xf_to_numfmt[i] = int(xf.get("numFmtId", "0"))
            except ValueError:
                xf_to_numfmt[i] = 0
    return xf_to_numfmt, custom_fmts


def is_date_style(style_idx: int, xf_to_numfmt: dict, custom_fmts: dict) -> bool:
    fmt_id = xf_to_numfmt.get(style_idx)
    if fmt_id is None:
        return False
    if fmt_id in BUILTIN_DATE_NUMFMT_IDS:
        return True
    code = custom_fmts.get(fmt_id, "")
    code_low = code.lower()
    if any(tok in code_low for tok in ("y", "d", "h", "m")) and "general" not in code_low:
        # evita falso positivo de formatos puramente numericos (#,##0.00 nao tem y/d/h)
        if re.search(r"[ymdh]", code_low):
            return True
    return False


def excel_serial_to_date(value: float):
    try:
        base = datetime.date(1899, 12, 30)
        return base + datetime.timedelta(days=value)
    except (OverflowError, ValueError):
        return None


def parse_workbook(z: Zip):
    root = z.xml("xl/workbook.xml")
    sheets = []
    defined_names = []
    protected = False
    calc_pr = {}
    if root is not None:
        sheets_el = root.find(q("sheets"))
        if sheets_el is not None:
            for idx, sh in enumerate(sheets_el.findall(q("sheet"))):
                sheets.append({
                    "index": idx,
                    "name": sh.get("name"),
                    "sheetId": sh.get("sheetId"),
                    "rId": sh.get(f"{{{NS_R}}}id"),
                    "state": sh.get("state", "visible"),
                })
        dn_el = root.find(q("definedNames"))
        if dn_el is not None:
            for dn in dn_el.findall(q("definedName")):
                defined_names.append({
                    "name": dn.get("name"),
                    "hidden": dn.get("hidden") == "1",
                    "localSheetId": dn.get("localSheetId"),
                    "value": (dn.text or "").strip(),
                })
        protected = root.find(q("workbookProtection")) is not None
        cp = root.find(q("calcPr"))
        if cp is not None:
            calc_pr = dict(cp.attrib)
    return sheets, defined_names, protected, calc_pr


def parse_rels(z: Zip, rels_path: str) -> dict[str, str]:
    root = z.xml(rels_path)
    mapping = {}
    if root is None:
        return mapping
    for rel in root.findall(f"{{{NS_PKG_REL}}}Relationship"):
        mapping[rel.get("Id")] = rel.get("Target")
    return mapping


def resolve_target(base_dir: str, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    parts = (base_dir.rstrip("/") + "/" + target).split("/")
    resolved = []
    for p in parts:
        if p == "..":
            if resolved:
                resolved.pop()
        elif p and p != ".":
            resolved.append(p)
    return "/".join(resolved)


def parse_core_props(z: Zip) -> dict:
    root = z.xml("docProps/core.xml")
    props = {}
    if root is None:
        return props
    for child in root:
        props[local(child.tag)] = (child.text or "").strip()
    return props


def parse_app_props(z: Zip) -> dict:
    root = z.xml("docProps/app.xml")
    props = {}
    if root is None:
        return props
    for child in root:
        tag = local(child.tag)
        if tag in ("Company", "Application", "AppVersion", "TotalTime"):
            props[tag] = (child.text or "").strip()
    return props


def parse_tables(z: Zip) -> dict[str, dict]:
    tables = {}
    for name in z.names_starting("xl/tables/table"):
        root = z.xml(name)
        if root is None:
            continue
        cols = [c.get("name") for c in root.findall(f".//{q('tableColumn')}")]
        tables[name] = {
            "name": root.get("name"),
            "ref": root.get("ref"),
            "columns": cols,
            "totalsRowShown": root.get("totalsRowShown"),
        }
    return tables


def detect_workbook_features(z: Zip) -> dict:
    return {
        "has_pivot_tables": bool(z.names_starting("xl/pivotTables/")),
        "has_pivot_caches": bool(z.names_starting("xl/pivotCache/")),
        "has_external_links": bool(z.names_starting("xl/externalLinks/")),
        "has_vba_macros": z.has("xl/vbaProject.bin"),
        "has_charts": bool(z.names_starting("xl/charts/")),
        "has_drawings": bool(z.names_starting("xl/drawings/")),
        "has_images": bool(z.names_starting("xl/media/")),
        "has_threaded_comments": bool(z.names_starting("xl/threadedComments/")),
        "has_legacy_comments": bool(
            n for n in z.names if re.match(r"xl/comments\d*\.xml$", n)
        ),
    }


def parse_sheet_xml(root, shared_strings, xf_to_numfmt, custom_fmts):
    """Extrai celulas, merges, hidden rows/cols, validations etc de um sheetN.xml."""
    cells: dict[str, dict] = {}
    dim = None
    dim_el = root.find(q("dimension"))
    if dim_el is not None:
        dim = dim_el.get("ref")

    hidden_rows = []
    max_row = 0
    max_col = 0
    sheet_data = root.find(q("sheetData"))
    shared_formula_masters: dict[str, str] = {}

    if sheet_data is not None:
        for row_el in sheet_data.findall(q("row")):
            r_idx = int(row_el.get("r"))
            max_row = max(max_row, r_idx)
            if row_el.get("hidden") == "1":
                hidden_rows.append(r_idx)
            for c_el in row_el.findall(q("c")):
                ref = c_el.get("r")
                col_letters, _ = split_cell_ref(ref)
                max_col = max(max_col, col_letters_to_index(col_letters))
                t = c_el.get("t", "n")
                style_idx = int(c_el.get("s", "0"))
                v_el = c_el.find(q("v"))
                f_el = c_el.find(q("f"))
                raw_v = v_el.text if v_el is not None else None
                formula_text = None
                is_shared = False
                if f_el is not None:
                    ftype = f_el.get("t")
                    si = f_el.get("si")
                    if ftype == "shared":
                        is_shared = True
                        if f_el.text:
                            formula_text = f_el.text
                            if si is not None:
                                shared_formula_masters[si] = formula_text
                        elif si is not None and si in shared_formula_masters:
                            formula_text = shared_formula_masters[si]
                    else:
                        formula_text = f_el.text

                value = raw_v
                py_type = "empty"
                if t == "s":
                    py_type = "string"
                    try:
                        value = shared_strings[int(raw_v)] if raw_v is not None else ""
                    except (ValueError, IndexError):
                        value = ""
                elif t == "str":
                    py_type = "string"
                    value = raw_v or ""
                elif t == "b":
                    py_type = "boolean"
                    value = raw_v == "1"
                elif t == "e":
                    py_type = "error"
                    value = raw_v
                elif t == "inlineStr":
                    py_type = "string"
                    is_el = c_el.find(q("is"))
                    value = "".join(x.text or "" for x in is_el.findall(q("t"))) if is_el is not None else ""
                else:  # numeric (default)
                    if raw_v is None:
                        py_type = "empty"
                    else:
                        try:
                            num = float(raw_v)
                        except ValueError:
                            num = None
                        if num is not None and is_date_style(style_idx, xf_to_numfmt, custom_fmts):
                            py_type = "date"
                            value = excel_serial_to_date(num)
                        else:
                            py_type = "number"
                            value = num

                cells[ref] = {
                    "row": r_idx,
                    "col_letters": col_letters,
                    "type": py_type,
                    "value": value,
                    "formula": formula_text,
                    "is_shared_formula": is_shared,
                    "style": style_idx,
                }

    merges = []
    merge_el = root.find(q("mergeCells"))
    if merge_el is not None:
        merges = [m.get("ref") for m in merge_el.findall(q("mergeCell"))]

    hidden_cols = []
    cols_el = root.find(q("cols"))
    if cols_el is not None:
        for c in cols_el.findall(q("col")):
            if c.get("hidden") == "1":
                try:
                    lo, hi = int(c.get("min")), int(c.get("max"))
                    hidden_cols.extend(range(lo, hi + 1))
                except (TypeError, ValueError):
                    pass

    freeze = None
    for pane in root.findall(f".//{q('pane')}"):
        freeze = pane.get("topLeftCell") or f"{pane.get('xSplit', '0')}x{pane.get('ySplit', '0')}"

    autofilter_ref = None
    af_el = root.find(q("autoFilter"))
    if af_el is not None:
        autofilter_ref = af_el.get("ref")

    data_validations = len(root.findall(f".//{q('dataValidation')}"))
    conditional_formats = len(root.findall(f".//{q('conditionalFormatting')}"))
    hyperlinks = len(root.findall(f".//{q('hyperlink')}"))
    sheet_protected = root.find(q("sheetProtection")) is not None
    table_parts = [tp.get(f"{{{NS_R}}}id") for tp in root.findall(f".//{q('tableParts')}/{q('tablePart')}")]

    return {
        "dimension": dim,
        "cells": cells,
        "max_row": max_row,
        "max_col": max_col,
        "merges": merges,
        "hidden_rows": hidden_rows,
        "hidden_cols": hidden_cols,
        "freeze_panes": freeze,
        "autofilter_ref": autofilter_ref,
        "data_validations": data_validations,
        "conditional_formats": conditional_formats,
        "hyperlinks": hyperlinks,
        "sheet_protected": sheet_protected,
        "table_part_rids": table_parts,
    }


# ------------------------------------------------------------- heuristics --

def detect_header_row(sheet: dict) -> tuple[int | None, float]:
    """Heuristica: procura, nas primeiras ~20 linhas, a linha com maior
    proporcao de celulas de texto nao vazias seguida por linhas mais
    numericas/mistas. Retorna (numero_da_linha, confianca 0-1)."""
    cells = sheet["cells"]
    if not cells:
        return None, 0.0
    rows = defaultdict(dict)
    for ref, c in cells.items():
        rows[c["row"]][c["col_letters"]] = c
    candidate_rows = sorted(r for r in rows if r <= 20) or sorted(rows)
    if not candidate_rows:
        return None, 0.0

    best_row, best_score = None, -1.0
    for r in candidate_rows[:20]:
        row_cells = [c for c in rows[r].values() if c["type"] != "empty"]
        if not row_cells:
            continue
        text_cells = [c for c in row_cells if c["type"] == "string"]
        text_ratio = len(text_cells) / len(row_cells)
        unique_vals = len({str(c["value"]) for c in text_cells})
        uniqueness = unique_vals / len(text_cells) if text_cells else 0

        following = [rr for rr in candidate_rows if rr > r][:5]
        below_numeric_ratio = 0.0
        below_count = 0
        for fr in following:
            fr_cells = [c for c in rows[fr].values() if c["type"] != "empty"]
            if not fr_cells:
                continue
            below_count += 1
            numericish = sum(1 for c in fr_cells if c["type"] in ("number", "date", "boolean"))
            below_numeric_ratio += numericish / len(fr_cells)
        below_numeric_ratio = below_numeric_ratio / below_count if below_count else 0

        score = (text_ratio * 0.5) + (uniqueness * 0.2) + (below_numeric_ratio * 0.3)
        if score > best_score:
            best_row, best_score = r, score

    confidence = max(0.0, min(1.0, best_score)) if best_row is not None else 0.0
    return best_row, round(confidence, 2)


def looks_like_pii_value(value) -> bool:
    if not isinstance(value, str):
        return False
    v = value.strip()
    if not v:
        return False
    for pat in PII_PATTERNS.values():
        if pat.match(v):
            return True
    return False


def profile_fields(workbook_id: str, sheet_name: str, sheet: dict, header_row, header_conf):
    cells = sheet["cells"]
    rows_by_col = defaultdict(dict)
    for ref, c in cells.items():
        rows_by_col[c["col_letters"]][c["row"]] = c

    if header_row is None:
        return []

    header_cells = {col: cs.get(header_row) for col, cs in rows_by_col.items()}
    data_rows = [r for r in range(header_row + 1, sheet["max_row"] + 1)]

    profiles = []
    for col, header_cell in sorted(header_cells.items(), key=lambda kv: col_letters_to_index(kv[0])):
        field_name = None
        if header_cell and header_cell["type"] == "string":
            field_name = str(header_cell["value"]).strip()
        if not field_name:
            continue

        col_cells = [rows_by_col[col].get(r) for r in data_rows]
        col_cells = [c for c in col_cells if c is not None]
        non_empty = [c for c in col_cells if c["type"] != "empty"]
        total = len(data_rows)
        filled = len(non_empty)
        blank = total - filled

        types_found = Counter(c["type"] for c in non_empty)
        predominant = types_found.most_common(1)[0][0] if types_found else "empty"
        mixed = len(types_found) > 1

        values = [c["value"] for c in non_empty if c["type"] != "error"]
        unique_count = len({repr(v) for v in values})
        duplicate_flag = filled > 0 and unique_count < filled

        has_formula = any(c["formula"] for c in non_empty)
        constant_flag = filled > 1 and unique_count == 1

        numeric_vals = [c["value"] for c in non_empty if c["type"] == "number" and isinstance(c["value"], (int, float))]
        date_vals = [c["value"] for c in non_empty if c["type"] == "date" and c["value"] is not None]
        text_vals = [c["value"] for c in non_empty if c["type"] == "string" and isinstance(c["value"], str)]
        error_count = sum(1 for c in non_empty if c["type"] == "error")

        min_v = max_v = mean_v = ""
        if numeric_vals:
            min_v, max_v = min(numeric_vals), max(numeric_vals)
            mean_v = round(statistics.fmean(numeric_vals), 4)

        date_min = date_max = ""
        if date_vals:
            date_min, date_max = min(date_vals).isoformat(), max(date_vals).isoformat()

        text_len_min = text_len_max = ""
        if text_vals:
            lens = [len(t) for t in text_vals]
            text_len_min, text_len_max = min(lens), max(lens)

        candidate_key = filled == total and filled > 0 and unique_count == filled
        cardinality_ratio = (unique_count / filled) if filled else 0
        candidate_category = filled > 0 and 0 < cardinality_ratio <= 0.2 and predominant == "string"
        candidate_calculated = has_formula and predominant in ("number", "date")

        field_lower = field_name.lower()
        potential_pii = any(hint in field_lower for hint in PII_HEADER_HINTS)
        if not potential_pii:
            potential_pii = any(looks_like_pii_value(v) for v in text_vals[:50])

        profiles.append({
            "workbook_id": workbook_id,
            "sheet_name": sheet_name,
            "header_row": header_row,
            "header_confidence": header_conf,
            "column_letter": col,
            "field_name": field_name,
            "predominant_type": predominant,
            "types_found": "|".join(sorted(types_found)),
            "filled_count": filled,
            "blank_count": blank,
            "fill_pct": round(100 * filled / total, 1) if total else 0,
            "unique_count": unique_count,
            "duplicate_flag": duplicate_flag,
            "has_formula": has_formula,
            "constant_value_flag": constant_flag,
            "min": min_v,
            "max": max_v,
            "mean": mean_v,
            "date_min": date_min,
            "date_max": date_max,
            "text_len_min": text_len_min,
            "text_len_max": text_len_max,
            "mixed_types_flag": mixed,
            "error_count": error_count,
            "candidate_key_flag": candidate_key,
            "candidate_category_flag": candidate_category,
            "candidate_calculated_flag": candidate_calculated,
            "potencial_pii": "SIM" if potential_pii else "NAO",
        })
    return profiles


def normalize_formula(formula: str) -> str:
    if not formula:
        return ""
    return CELL_REF_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}{m.group(3)}#", formula)


def formula_inventory_for_sheet(workbook_id: str, sheet_name: str, sheet: dict):
    groups: dict[str, list[dict]] = defaultdict(list)
    for ref, c in sheet["cells"].items():
        if not c["formula"]:
            continue
        pattern = normalize_formula(c["formula"])
        groups[pattern].append({"ref": ref, "row": c["row"], "col": c["col_letters"], "formula": c["formula"]})

    rows_out = []
    for pattern, occurrences in groups.items():
        rows_ = {o["row"] for o in occurrences}
        cols_ = {o["col"] for o in occurrences}
        if len(rows_) > 1 and len(cols_) == 1:
            direction = "vertical"
        elif len(cols_) > 1 and len(rows_) == 1:
            direction = "horizontal"
        elif len(rows_) > 1 and len(cols_) > 1:
            direction = "mixed"
        else:
            direction = "single"

        sheet_refs = set()
        for o in occurrences:
            for m in SHEET_REF_RE.finditer(o["formula"]):
                sheet_refs.add(m.group(1) or m.group(2))

        has_absolute = "$" in pattern
        has_relative = bool(re.search(r"(?<!\$)[A-Z]{1,3}#", pattern))
        broken = sum(1 for o in occurrences if "#REF!" in o["formula"] or "#REF!" in pattern)

        rows_out.append({
            "workbook_id": workbook_id,
            "sheet_name": sheet_name,
            "pattern": pattern,
            "occurrences": len(occurrences),
            "example_cell": occurrences[0]["ref"],
            "refs_other_sheets": "|".join(sorted(sheet_refs)),
            "has_absolute_ref": has_absolute,
            "has_relative_ref": has_relative,
            "direction": direction,
            "broken_count": broken,
        })
    return rows_out


def dependency_edges_for_sheet(workbook_id: str, sheet_name: str, sheet: dict):
    counter = Counter()
    for c in sheet["cells"].values():
        if not c["formula"]:
            continue
        for m in SHEET_REF_RE.finditer(c["formula"]):
            target = m.group(1) or m.group(2)
            if target and target != sheet_name:
                counter[target] += 1
    return [
        {
            "workbook_id": workbook_id,
            "source_sheet": sheet_name,
            "target_sheet": target,
            "reference_count": count,
        }
        for target, count in counter.items()
    ]


def quality_issues_for_sheet(workbook_id: str, sheet_name: str, sheet: dict, fields: list[dict]):
    issues = []

    rows_by_row = defaultdict(list)
    for c in sheet["cells"].values():
        rows_by_row[c["row"]].append(c)
    data_rows = sorted(r for r in rows_by_row if r > 0)
    if data_rows:
        first, last = data_rows[0], data_rows[-1]
        for r in range(first, last + 1):
            row_cells = rows_by_row.get(r, [])
            if row_cells and all(c["type"] == "empty" for c in row_cells):
                issues.append({
                    "workbook_id": workbook_id, "sheet_name": sheet_name,
                    "issue_type": "linha_totalmente_vazia_no_meio",
                    "location": f"row {r}", "detail": "", "severity": "MEDIA",
                })

    for f in fields:
        if f["blank_count"] > 0 and f["filled_count"] > 0 and f["fill_pct"] < 50:
            issues.append({
                "workbook_id": workbook_id, "sheet_name": sheet_name,
                "issue_type": "baixa_cobertura",
                "location": f"{f['sheet_name']}!{f['column_letter']}",
                "detail": f"fill_pct={f['fill_pct']}", "severity": "BAIXA",
            })
        if f["mixed_types_flag"]:
            issues.append({
                "workbook_id": workbook_id, "sheet_name": sheet_name,
                "issue_type": "tipos_inconsistentes",
                "location": f"{f['sheet_name']}!{f['column_letter']}",
                "detail": f["types_found"], "severity": "MEDIA",
            })
        if f["error_count"] > 0:
            issues.append({
                "workbook_id": workbook_id, "sheet_name": sheet_name,
                "issue_type": "celulas_com_erro",
                "location": f"{f['sheet_name']}!{f['column_letter']}",
                "detail": f"error_count={f['error_count']}", "severity": "ALTA",
            })
        if f["duplicate_flag"] and f["candidate_key_flag"] is False and f["filled_count"] > 0:
            dup_ratio = 1 - (f["unique_count"] / f["filled_count"])
            if dup_ratio > 0.3:
                issues.append({
                    "workbook_id": workbook_id, "sheet_name": sheet_name,
                    "issue_type": "possivel_duplicidade",
                    "location": f"{f['sheet_name']}!{f['column_letter']}",
                    "detail": f"dup_ratio={round(dup_ratio, 2)}", "severity": "BAIXA",
                })
        if f["constant_value_flag"]:
            issues.append({
                "workbook_id": workbook_id, "sheet_name": sheet_name,
                "issue_type": "coluna_quase_constante",
                "location": f"{f['sheet_name']}!{f['column_letter']}", "detail": "",
                "severity": "BAIXA",
            })

    key_candidates = [f for f in fields if f["candidate_key_flag"]]
    if not key_candidates and fields:
        issues.append({
            "workbook_id": workbook_id, "sheet_name": sheet_name,
            "issue_type": "possivel_chave_ausente",
            "location": sheet_name, "detail": "", "severity": "MEDIA",
        })

    return issues


def normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (name or "").lower())


def cross_workbook_mapping(workbooks: list[dict]):
    if len(workbooks) < 2:
        return []
    rows_out = []
    for i in range(len(workbooks)):
        for j in range(i + 1, len(workbooks)):
            wa, wb = workbooks[i], workbooks[j]
            for sa in wa["sheets_detail"]:
                for sb in wb["sheets_detail"]:
                    sim = difflib.SequenceMatcher(
                        None, normalize_name(sa["name"]), normalize_name(sb["name"])
                    ).ratio()
                    if sim < 0.4:
                        continue
                    confidence = "ALTA" if sim >= 0.85 else "MEDIA" if sim >= 0.6 else "BAIXA"
                    rows_out.append({
                        "workbook_a": wa["id"], "sheet_a": sa["name"],
                        "workbook_b": wb["id"], "sheet_b": sb["name"],
                        "field_a": "", "field_b": "",
                        "similarity_score": round(sim, 2), "confidence": confidence,
                        "basis": "nome_da_aba",
                    })

                    fields_a = {f["field_name"]: f for f in sa.get("fields", [])}
                    fields_b = {f["field_name"]: f for f in sb.get("fields", [])}
                    for fa_name, fa in fields_a.items():
                        best_name, best_sim = None, 0.0
                        for fb_name in fields_b:
                            s = difflib.SequenceMatcher(
                                None, normalize_name(fa_name), normalize_name(fb_name)
                            ).ratio()
                            if s > best_sim:
                                best_name, best_sim = fb_name, s
                        if best_name and best_sim >= 0.5:
                            confidence = "ALTA" if best_sim >= 0.85 else "MEDIA" if best_sim >= 0.65 else "BAIXA"
                            rows_out.append({
                                "workbook_a": wa["id"], "sheet_a": sa["name"],
                                "workbook_b": wb["id"], "sheet_b": sb["name"],
                                "field_a": fa_name, "field_b": best_name,
                                "similarity_score": round(best_sim, 2),
                                "confidence": confidence, "basis": "nome_de_campo",
                            })
    return rows_out


# --------------------------------------------------------------- runner ---

def audit_workbook(path: Path, workbook_id: str) -> dict:
    z = Zip(path)
    shared_strings = parse_shared_strings(z)
    xf_to_numfmt, custom_fmts = parse_styles(z)
    sheets_meta, defined_names, wb_protected, calc_pr = parse_workbook(z)
    wb_rels = parse_rels(z, "xl/_rels/workbook.xml.rels")
    core_props = parse_core_props(z)
    app_props = parse_app_props(z)
    tables = parse_tables(z)
    features = detect_workbook_features(z)

    sheets_detail = []
    all_field_profiles = []
    all_formula_rows = []
    all_dependency_edges = []
    all_quality_issues = []
    hidden_content_rows = []

    for sm in sheets_meta:
        target = wb_rels.get(sm["rId"])
        if not target:
            continue
        sheet_path = resolve_target("xl", target)
        root = z.xml(sheet_path)
        if root is None:
            continue
        sheet = parse_sheet_xml(root, shared_strings, xf_to_numfmt, custom_fmts)

        rels_path = resolve_target("xl/_rels", "")
        sheet_rels_path = sheet_path.rsplit("/", 1)[0] + "/_rels/" + sheet_path.rsplit("/", 1)[1] + ".rels"
        sheet_rels = parse_rels(z, sheet_rels_path)

        n_tables = sum(1 for rid in sheet["table_part_rids"] if rid in sheet_rels)
        has_comments = any(
            "comment" in (sheet_rels.get(rid, "") or "").lower() for rid in sheet_rels
        )
        has_chart_or_image = any(
            "drawing" in (sheet_rels.get(rid, "") or "").lower() for rid in sheet_rels
        )

        filled_cells = sum(1 for c in sheet["cells"].values() if c["type"] != "empty")
        formula_cells = sum(1 for c in sheet["cells"].values() if c["formula"])
        error_cells = sum(1 for c in sheet["cells"].values() if c["type"] == "error")

        header_row, header_conf = detect_header_row(sheet)
        fields = profile_fields(workbook_id, sm["name"], sheet, header_row, header_conf)
        formulas = formula_inventory_for_sheet(workbook_id, sm["name"], sheet)
        deps = dependency_edges_for_sheet(workbook_id, sm["name"], sheet)
        issues = quality_issues_for_sheet(workbook_id, sm["name"], sheet, fields)

        all_field_profiles.extend(fields)
        all_formula_rows.extend(formulas)
        all_dependency_edges.extend(deps)
        all_quality_issues.extend(issues)

        if sm["state"] != "visible":
            hidden_content_rows.append({
                "workbook_id": workbook_id, "type": f"{sm['state']}_sheet",
                "location": sm["name"], "detail": "",
            })
        for r in sheet["hidden_rows"]:
            hidden_content_rows.append({
                "workbook_id": workbook_id, "type": "hidden_row",
                "location": f"{sm['name']}!row{r}", "detail": "",
            })
        for c in sheet["hidden_cols"]:
            hidden_content_rows.append({
                "workbook_id": workbook_id, "type": "hidden_col",
                "location": f"{sm['name']}!col{c}", "detail": "",
            })

        sheets_detail.append({
            "name": sm["name"],
            "index": sm["index"],
            "state": sm["state"],
            "dimension": sheet["dimension"],
            "n_rows": sheet["max_row"],
            "n_cols": sheet["max_col"],
            "filled_cells": filled_cells,
            "formula_cells": formula_cells,
            "error_cells": error_cells,
            "merged_cells_count": len(sheet["merges"]),
            "has_autofilter": bool(sheet["autofilter_ref"]),
            "table_count": n_tables,
            "freeze_panes": sheet["freeze_panes"] or "",
            "hyperlinks_count": sheet["hyperlinks"],
            "comments_present": has_comments,
            "data_validations_count": sheet["data_validations"],
            "conditional_formatting_count": sheet["conditional_formats"],
            "hidden_rows_count": len(sheet["hidden_rows"]),
            "hidden_cols_count": len(sheet["hidden_cols"]),
            "has_chart_or_image": has_chart_or_image,
            "sheet_protected": sheet["sheet_protected"],
            "header_row_detected": header_row,
            "header_confidence": header_conf,
            "fields": fields,
        })

    for dn in defined_names:
        if dn["hidden"]:
            hidden_content_rows.append({
                "workbook_id": workbook_id, "type": "hidden_defined_name",
                "location": dn["name"], "detail": dn["value"],
            })
    if features["has_external_links"]:
        hidden_content_rows.append({
            "workbook_id": workbook_id, "type": "external_link",
            "location": "xl/externalLinks", "detail": "",
        })

    return {
        "id": workbook_id,
        "path": path,
        "size_bytes": path.stat().st_size,
        "core_props": core_props,
        "app_props": app_props,
        "sheet_count": len(sheets_meta),
        "defined_names_count": len(defined_names),
        "workbook_protected": wb_protected,
        "tables": tables,
        "features": features,
        "sheets_detail": sheets_detail,
        "field_profiles": all_field_profiles,
        "formula_rows": all_formula_rows,
        "dependency_edges": all_dependency_edges,
        "quality_issues": all_quality_issues,
        "hidden_content_rows": hidden_content_rows,
    }


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]):
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_outputs(workbooks: list[dict], output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    wb_rows = []
    sheet_rows = []
    field_rows = []
    formula_rows = []
    dep_rows = []
    hidden_rows = []
    quality_rows = []

    for wb in workbooks:
        wb_rows.append({
            "workbook_id": wb["id"],
            "size_bytes": wb["size_bytes"],
            "creator": wb["core_props"].get("creator", ""),
            "last_modified_by": wb["core_props"].get("lastModifiedBy", ""),
            "created": wb["core_props"].get("created", ""),
            "modified": wb["core_props"].get("modified", ""),
            "application": wb["app_props"].get("Application", ""),
            "sheet_count": wb["sheet_count"],
            "defined_names_count": wb["defined_names_count"],
            "workbook_protected": wb["workbook_protected"],
            "table_definitions_count": len(wb["tables"]),
            **wb["features"],
        })
        for s in wb["sheets_detail"]:
            sheet_rows.append({
                "workbook_id": wb["id"],
                "sheet_name": s["name"],
                "sheet_index": s["index"],
                "visibility": s["state"],
                "dimension_ref": s["dimension"] or "",
                "n_rows": s["n_rows"],
                "n_cols": s["n_cols"],
                "filled_cells": s["filled_cells"],
                "formula_cells": s["formula_cells"],
                "error_cells": s["error_cells"],
                "merged_cells_count": s["merged_cells_count"],
                "has_autofilter": s["has_autofilter"],
                "table_count": s["table_count"],
                "freeze_panes": s["freeze_panes"],
                "hyperlinks_count": s["hyperlinks_count"],
                "comments_present": s["comments_present"],
                "data_validations_count": s["data_validations_count"],
                "conditional_formatting_count": s["conditional_formatting_count"],
                "hidden_rows_count": s["hidden_rows_count"],
                "hidden_cols_count": s["hidden_cols_count"],
                "has_chart_or_image": s["has_chart_or_image"],
                "sheet_protected": s["sheet_protected"],
                "header_row_detected": s["header_row_detected"],
                "header_confidence": s["header_confidence"],
            })
        field_rows.extend(wb["field_profiles"])
        formula_rows.extend(wb["formula_rows"])
        dep_rows.extend(wb["dependency_edges"])
        hidden_rows.extend(wb["hidden_content_rows"])
        quality_rows.extend(wb["quality_issues"])

    write_csv(output_dir / "workbook_inventory.csv", list(wb_rows[0].keys()) if wb_rows else
              ["workbook_id", "size_bytes"], wb_rows)
    write_csv(output_dir / "sheet_inventory.csv", list(sheet_rows[0].keys()) if sheet_rows else
              ["workbook_id", "sheet_name"], sheet_rows)
    write_csv(output_dir / "field_profile.csv", list(field_rows[0].keys()) if field_rows else
              ["workbook_id", "sheet_name", "field_name"], field_rows)
    write_csv(output_dir / "formula_inventory.csv", list(formula_rows[0].keys()) if formula_rows else
              ["workbook_id", "sheet_name", "pattern"], formula_rows)
    write_csv(output_dir / "dependency_inventory.csv", list(dep_rows[0].keys()) if dep_rows else
              ["workbook_id", "source_sheet", "target_sheet"], dep_rows)
    write_csv(output_dir / "hidden_content_inventory.csv", list(hidden_rows[0].keys()) if hidden_rows else
              ["workbook_id", "type", "location"], hidden_rows)
    write_csv(output_dir / "quality_issues.csv", list(quality_rows[0].keys()) if quality_rows else
              ["workbook_id", "sheet_name", "issue_type"], quality_rows)

    cross_rows = cross_workbook_mapping(workbooks)
    write_csv(output_dir / "cross_workbook_mapping.csv",
              list(cross_rows[0].keys()) if cross_rows else
              ["workbook_a", "sheet_a", "workbook_b", "sheet_b", "confidence"], cross_rows)

    write_markdown_summary(workbooks, cross_rows, output_dir / "structural-audit.md")


def write_markdown_summary(workbooks: list[dict], cross_rows: list[dict], out_path: Path):
    lines = ["# Auditoria estrutural — resumo privado", "",
             "Gerado automaticamente por `scripts/audit_xlsx.py`. Este arquivo e "
             "privado (ignorado pelo Git) e pode conter nomes de abas/campos reais.",
             ""]
    for wb in workbooks:
        lines.append(f"## Workbook `{wb['id']}`")
        lines.append("")
        lines.append(f"- tamanho: {wb['size_bytes']} bytes")
        lines.append(f"- abas: {wb['sheet_count']}")
        lines.append(f"- nomes definidos: {wb['defined_names_count']}")
        lines.append(f"- workbook protegido: {wb['workbook_protected']}")
        for k, v in wb["features"].items():
            lines.append(f"- {k}: {v}")
        lines.append("")
        for s in wb["sheets_detail"]:
            lines.append(f"### Aba `{s['name']}` (visibilidade: {s['state']})")
            lines.append(
                f"- dimensao: {s['dimension']}, linhas: {s['n_rows']}, colunas: {s['n_cols']}, "
                f"celulas preenchidas: {s['filled_cells']}, formulas: {s['formula_cells']}, "
                f"erros: {s['error_cells']}"
            )
            lines.append(
                f"- cabecalho detectado na linha {s['header_row_detected']} "
                f"(confianca {s['header_confidence']})"
            )
            n_fields = len(s["fields"])
            n_keys = sum(1 for f in s["fields"] if f["candidate_key_flag"])
            n_pii = sum(1 for f in s["fields"] if f["potencial_pii"] == "SIM")
            lines.append(
                f"- campos detectados: {n_fields}, candidatos a chave: {n_keys}, "
                f"campos com potencial PII: {n_pii}"
            )
            lines.append("")
    if cross_rows:
        lines.append("## Comparacao entre workbooks")
        lines.append("")
        for row in cross_rows:
            if row["basis"] == "nome_da_aba":
                lines.append(
                    f"- aba `{row['sheet_a']}` ({row['workbook_a']}) ~ "
                    f"`{row['sheet_b']}` ({row['workbook_b']}): "
                    f"similaridade {row['similarity_score']} [{row['confidence']}]"
                )
        lines.append("")
        for row in cross_rows:
            if row["basis"] == "nome_de_campo":
                lines.append(
                    f"- campo `{row['field_a']}` ({row['sheet_a']}) ~ "
                    f"`{row['field_b']}` ({row['sheet_b']}): "
                    f"similaridade {row['similarity_score']} [{row['confidence']}]"
                )
    out_path.write_text("\n".join(lines), encoding="utf-8")


def resolve_input_path(raw: str) -> Path:
    """Resolve um caminho de entrada tolerando diferenca de normalizacao
    Unicode (NFC vs NFD) entre o argumento de linha de comando e o nome
    real do arquivo no sistema de arquivos - comum quando o shell e o
    sistema de arquivos normalizam acentos de formas diferentes."""
    p = Path(raw)
    if p.exists():
        return p
    for form in ("NFC", "NFD"):
        candidate = Path(unicodedata.normalize(form, raw))
        if candidate.exists():
            return candidate
    parent = p.parent if p.parent != Path("") else Path(".")
    target_norm = unicodedata.normalize("NFC", p.name)
    if parent.exists():
        for entry in parent.iterdir():
            if unicodedata.normalize("NFC", entry.name) == target_norm:
                return entry
    return p


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Auditoria estrutural generica de workbooks XLSX (OOXML), "
                     "sem dependencias externas."
    )
    parser.add_argument("--input", action="append", required=True,
                         help="Caminho para um arquivo .xlsx a auditar. Pode ser "
                              "passado mais de uma vez para comparar workbooks.")
    parser.add_argument("--output-dir", required=True,
                         help="Diretorio onde os CSVs/Markdown de saida serao gravados.")
    parser.add_argument("--workbook-id", action="append", default=None,
                         help="Identificador generico para cada --input, na mesma ordem "
                              "(ex.: wb1, wb2). Se omitido, gera wb1, wb2, ...")
    args = parser.parse_args(argv)

    inputs = [resolve_input_path(p) for p in args.input]
    ids = args.workbook_id or [f"wb{i+1}" for i in range(len(inputs))]
    if len(ids) != len(inputs):
        parser.error("--workbook-id, se usado, deve aparecer o mesmo numero de vezes que --input")

    workbooks = []
    for path, wb_id in zip(inputs, ids):
        if not path.exists():
            parser.error(f"arquivo de entrada nao encontrado: {path}")
        workbooks.append(audit_workbook(path, wb_id))

    write_outputs(workbooks, Path(args.output_dir))

    for wb in workbooks:
        print(f"{wb['id']}: {wb['sheet_count']} aba(s), "
              f"{len(wb['field_profiles'])} campo(s) detectado(s), "
              f"{len(wb['formula_rows'])} padrao(oes) de formula, "
              f"{len(wb['quality_issues'])} problema(s) de qualidade")

    return 0


if __name__ == "__main__":
    sys.exit(main())
