#!/usr/bin/env python3
"""Auxilia a engenharia reversa de logica de precificacao em workbooks XLSX.

Reaproveita o parsing OOXML de `scripts/audit_xlsx.py` (biblioteca padrao
apenas) e adiciona duas analises que a auditoria estrutural nao fazia:

1. Extracao de constantes numericas literais embutidas em formulas
   (possiveis parametros "magicos": pesos, percentuais, indices de
   lookup etc.), gravadas em `pricing_parameters_detected.csv`.
2. Deteccao de regioes onde o padrao de formula de uma coluna muda de
   forma inesperada (ex.: um trecho de linhas com formula diferente ou
   com valor manual no meio de uma coluna majoritariamente calculada),
   gravadas em `formula_consistency_flags.csv`.

Nenhuma classificacao de significado de negocio e feita aqui - isso e
trabalho humano/assistido, registrado separadamente em
`business_rules_catalog.csv` (fora deste script). A ferramenta apenas
levanta evidencia estrutural, com `confidence` e `requires_human_explanation`
sempre marcados de forma conservadora.

Nao contem nomes de arquivo, caminhos absolutos, hashes ou valores
privados - tudo isso entra via argumentos de linha de comando.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import audit_xlsx as ax  # noqa: E402

NUMERIC_LITERAL_RE = re.compile(r"(?<![A-Za-z$])-?\d+\.\d+|(?<![A-Za-z$])-?\d+(?!\.\d)")
STRUCTURAL_SMALL_INTS = {"0", "1", "2", "3", "4", "-1"}


def strip_cell_refs(formula: str) -> str:
    without_refs = ax.CELL_REF_RE.sub(" ", formula)
    without_sheet_refs = re.sub(r"(?:'[^']+'|[A-Za-z_][\w .]*)!", " ", without_refs)
    return without_sheet_refs


def guess_role(value_str: str, formula: str) -> str:
    try:
        value = float(value_str)
    except ValueError:
        return "desconhecido"
    if 0 < value < 1:
        return "possivel_percentual_ou_peso"
    if value in (100, 1000):
        return "possivel_conversao_ou_escala"
    if value.is_integer() and 0 <= value <= 60 and re.search(r"(VLOOKUP|HLOOKUP)\(", formula, re.I):
        return "possivel_indice_ou_offset_de_lookup"
    if abs(value) >= 1000:
        return "possivel_valor_monetario_ou_area_total"
    return "desconhecido"


def requires_explanation(value_str: str, formula: str) -> bool:
    if value_str in STRUCTURAL_SMALL_INTS and re.search(r"(VLOOKUP|HLOOKUP|MATCH|INDEX)\(", formula, re.I):
        return False
    return True


def extract_parameters(workbook_id: str, sheet_name: str, sheet: dict) -> list[dict]:
    rows_out = []
    counter = 0
    seen_per_pattern: dict[tuple, int] = defaultdict(int)
    for ref, c in sheet["cells"].items():
        if not c["formula"]:
            continue
        remainder = strip_cell_refs(c["formula"])
        for m in NUMERIC_LITERAL_RE.finditer(remainder):
            literal = m.group(0)
            pattern_key = (ax.normalize_formula(c["formula"]), literal)
            seen_per_pattern[pattern_key] += 1
            if seen_per_pattern[pattern_key] > 1:
                # mesma constante no mesmo padrao de formula já foi
                # registrada uma vez; evita explodir uma constante
                # estrutural copiada em centenas de linhas.
                continue
            counter += 1
            rows_out.append({
                "parameter_id": f"{workbook_id}-{sheet_name}-p{counter}",
                "workbook": workbook_id,
                "sheet": sheet_name,
                "location": ref,
                "value_or_expression": literal,
                "used_by": c["formula"][:200],
                "possible_role": guess_role(literal, c["formula"]),
                "origin_type": "HARDCODED_FORMULA",
                "confidence": "LOW",
                "requires_human_explanation": requires_explanation(literal, c["formula"]),
            })
    return rows_out


def detect_consistency_flags(workbook_id: str, sheet_name: str, sheet: dict) -> list[dict]:
    by_col: dict[str, dict[int, dict]] = defaultdict(dict)
    for ref, c in sheet["cells"].items():
        by_col[c["col_letters"]][c["row"]] = c

    rows_out = []
    for col, cells_by_row in by_col.items():
        rows_sorted = sorted(cells_by_row)
        if len(rows_sorted) < 5:
            continue
        signatures = []
        for r in rows_sorted:
            c = cells_by_row[r]
            if c["formula"]:
                sig = ("formula", ax.normalize_formula(c["formula"]))
            elif c["type"] in ("number", "string", "date") and c["value"] not in (None, ""):
                sig = ("manual_value", c["type"])
            else:
                sig = ("empty", None)
            signatures.append((r, sig))

        counts = defaultdict(int)
        for _, sig in signatures:
            counts[sig] += 1
        if not counts:
            continue
        majority_sig, majority_count = max(counts.items(), key=lambda kv: kv[1])
        if majority_sig[0] != "formula" or majority_count < 5:
            continue

        # agrupa runs contiguas que divergem do padrao majoritario
        run_start = None
        run_sig = None
        for idx, (r, sig) in enumerate(signatures):
            deviates = sig != majority_sig
            if deviates and run_start is None:
                run_start, run_sig = r, sig
            ended = (not deviates) or idx == len(signatures) - 1
            if run_start is not None and ended:
                run_end = r if deviates else signatures[idx - 1][0]
                run_len = sum(1 for rr, ss in signatures if run_start <= rr <= run_end and ss == run_sig)
                if run_len >= 1:
                    kind = run_sig[0] if isinstance(run_sig, tuple) else "unknown"
                    detail = run_sig[1] if isinstance(run_sig, tuple) else ""
                    rows_out.append({
                        "workbook": workbook_id,
                        "sheet": sheet_name,
                        "column": col,
                        "row_range": f"{run_start}-{run_end}",
                        "affected_cells": run_len,
                        "majority_pattern_kind": majority_sig[0],
                        "deviation_kind": kind,
                        "deviation_detail": (detail or "")[:200],
                        "classification_hint": (
                            "POSSIBLE_MANUAL_OVERRIDE" if kind == "manual_value" else
                            "POSSIBLE_ERROR_OR_VARIANT_FORMULA" if kind == "formula" else
                            "UNKNOWN"
                        ),
                    })
                run_start, run_sig = None, None
    return rows_out


def write_csv(path: Path, fieldnames: list[str], rows: list[dict]):
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def analyze_workbook(path: Path, workbook_id: str):
    z = ax.Zip(path)
    shared_strings = ax.parse_shared_strings(z)
    xf_to_numfmt, custom_fmts = ax.parse_styles(z)
    sheets_meta, _, _, _ = ax.parse_workbook(z)
    wb_rels = ax.parse_rels(z, "xl/_rels/workbook.xml.rels")

    parameters = []
    flags = []
    for sm in sheets_meta:
        target = wb_rels.get(sm["rId"])
        if not target:
            continue
        sheet_path = ax.resolve_target("xl", target)
        root = z.xml(sheet_path)
        if root is None:
            continue
        sheet = ax.parse_sheet_xml(root, shared_strings, xf_to_numfmt, custom_fmts)
        parameters.extend(extract_parameters(workbook_id, sm["name"], sheet))
        flags.extend(detect_consistency_flags(workbook_id, sm["name"], sheet))
    return parameters, flags


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Extrai constantes numericas embutidas em formulas e "
                     "sinaliza regioes de inconsistencia de formula por "
                     "coluna, para apoiar engenharia reversa de logica de "
                     "precificacao. Sem dependencias externas."
    )
    parser.add_argument("--input", action="append", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--workbook-id", action="append", default=None)
    args = parser.parse_args(argv)

    inputs = [ax.resolve_input_path(p) for p in args.input]
    ids = args.workbook_id or [f"wb{i+1}" for i in range(len(inputs))]
    if len(ids) != len(inputs):
        parser.error("--workbook-id, se usado, deve aparecer o mesmo numero de vezes que --input")

    all_params, all_flags = [], []
    for path, wb_id in zip(inputs, ids):
        if not path.exists():
            parser.error(f"arquivo de entrada nao encontrado: {path}")
        params, flags = analyze_workbook(path, wb_id)
        all_params.extend(params)
        all_flags.extend(flags)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    param_fields = ["parameter_id", "workbook", "sheet", "location", "value_or_expression",
                     "used_by", "possible_role", "origin_type", "confidence",
                     "requires_human_explanation"]
    write_csv(out_dir / "pricing_parameters_detected.csv", param_fields, all_params)

    flag_fields = ["workbook", "sheet", "column", "row_range", "affected_cells",
                   "majority_pattern_kind", "deviation_kind", "deviation_detail",
                   "classification_hint"]
    write_csv(out_dir / "formula_consistency_flags.csv", flag_fields, all_flags)

    print(f"parametros detectados: {len(all_params)}")
    print(f"regioes de inconsistencia sinalizadas: {len(all_flags)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
