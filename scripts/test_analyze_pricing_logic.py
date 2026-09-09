#!/usr/bin/env python3
"""Teste de fumaca de scripts/analyze_pricing_logic.py usando um workbook
XLSX sintetico (nenhum dado real/privado). Reaproveita o construtor de
workbook sintetico de test_audit_xlsx.py e adiciona uma coluna com uma
constante numerica embutida em formula e uma regiao com override manual
no meio de uma coluna calculada, para validar as duas analises da
ferramenta.
"""

from __future__ import annotations

import csv
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import analyze_pricing_logic as apl
import test_audit_xlsx as fixtures

SHEET_WITH_PARAM_AND_OVERRIDE = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <dimension ref="A1:B7"/>
  <sheetData>
    <row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c></row>
    <row r="2"><c r="A2"><v>100</v></c><c r="B2"><f>A2*0.6</f><v>60</v></c></row>
    <row r="3"><c r="A3"><v>200</v></c><c r="B3"><f>A3*0.6</f><v>120</v></c></row>
    <row r="4"><c r="A4"><v>300</v></c><c r="B4"><v>999</v></c></row>
    <row r="5"><c r="A5"><v>400</v></c><c r="B5"><f>A5*0.6</f><v>240</v></c></row>
    <row r="6"><c r="A6"><v>500</v></c><c r="B6"><f>A6*0.6</f><v>300</v></c></row>
    <row r="7"><c r="A7"><v>600</v></c><c r="B7"><f>A7*0.6</f><v>360</v></c></row>
  </sheetData>
</worksheet>"""


def build_workbook(dest: Path):
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", fixtures.CONTENT_TYPES)
        zf.writestr("_rels/.rels", fixtures.ROOT_RELS)
        zf.writestr("xl/workbook.xml", fixtures.workbook_xml("visible"))
        zf.writestr("xl/_rels/workbook.xml.rels", fixtures.WORKBOOK_RELS)
        zf.writestr("xl/worksheets/sheet1.xml", SHEET_WITH_PARAM_AND_OVERRIDE)
        zf.writestr("xl/worksheets/sheet2.xml", fixtures.sheet2_xml())
        zf.writestr("xl/sharedStrings.xml", fixtures.SHARED_STRINGS)
        zf.writestr("xl/styles.xml", fixtures.STYLES)
        zf.writestr("docProps/core.xml", fixtures.CORE_PROPS)
        zf.writestr("docProps/app.xml", fixtures.APP_PROPS)


def read_csv(path: Path):
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def run():
    tmpdir = Path(tempfile.mkdtemp(prefix="analyze-pricing-selftest-"))
    out_dir = tmpdir / "out"
    try:
        wb = tmpdir / "sintetico-parametros.xlsx"
        build_workbook(wb)

        rc = apl.main(["--input", str(wb), "--output-dir", str(out_dir), "--workbook-id", "wbX"])
        assert rc == 0

        params = read_csv(out_dir / "pricing_parameters_detected.csv")
        assert any(p["value_or_expression"] == "0.6" for p in params), \
            "constante 0.6 embutida na formula deveria ter sido detectada"

        flags = read_csv(out_dir / "formula_consistency_flags.csv")
        # a linha de cabecalho (B1, texto) tambem diverge da formula
        # majoritaria e gera flag - esperado, pois esta ferramenta nao
        # faz deteccao de cabecalho (isso e escopo de audit_xlsx.py).
        override_flags = [f for f in flags if f["deviation_detail"] == "number"]
        assert override_flags, "linha B4 (valor manual em coluna calculada) deveria gerar flag"
        assert override_flags[0]["row_range"] == "4-4"
        assert override_flags[0]["classification_hint"] == "POSSIBLE_MANUAL_OVERRIDE"

        print("OK: todas as verificacoes do teste sintetico de analyze_pricing_logic passaram")
        return 0
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(run())
