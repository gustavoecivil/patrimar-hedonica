#!/usr/bin/env python3
"""Teste de fumaca de scripts/audit_xlsx.py usando workbooks XLSX sintéticos
gerados em memória (nenhum dado real/privado é usado ou versionado).

Cria dois arquivos .xlsx minimos via zipfile/XML puro (sem openpyxl, que nao
esta disponivel no ambiente), roda a ferramenta de auditoria sobre eles e
valida que os CSVs de saida contêm os achados esperados: aba oculta,
formula compartilhada, celula de erro e correspondencia entre os dois
workbooks.
"""

from __future__ import annotations

import csv
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

import audit_xlsx

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
  <Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>
  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"""

ROOT_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"""

WORKBOOK_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>
  <Relationship Id="rId4" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <numFmts count="0"/>
  <fonts count="1"><font/></fonts>
  <fills count="1"><fill/></fills>
  <borders count="1"><border/></borders>
  <cellStyleXfs count="1"><xf numFmtId="0"/></cellStyleXfs>
  <cellXfs count="1"><xf numFmtId="0"/></cellXfs>
</styleSheet>"""

CORE_PROPS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
                    xmlns:dc="http://purl.org/dc/elements/1.1/"
                    xmlns:dcterms="http://purl.org/dc/terms/">
  <dc:creator>teste-sintetico</dc:creator>
  <cp:lastModifiedBy>teste-sintetico</cp:lastModifiedBy>
</cp:coreProperties>"""

APP_PROPS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">
  <Application>synthetic-test</Application>
</Properties>"""

SHARED_STRINGS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="4" uniqueCount="4">
  <si><t>codigo</t></si>
  <si><t>quantidade</t></si>
  <si><t>total</t></si>
  <si><t>nota</t></si>
</sst>"""


def workbook_xml(sheet2_state: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
          xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="Dados" sheetId="1" r:id="rId1"/>
    <sheet name="Auxiliar" sheetId="2" state="{sheet2_state}" r:id="rId2"/>
  </sheets>
</workbook>"""


def sheet1_xml() -> str:
    # cabecalho na linha 1 (codigo, quantidade, total), 3 linhas de dados,
    # coluna C usa formula compartilhada, linha 5 tem erro propositalmente.
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <dimension ref="A1:C5"/>
  <sheetData>
    <row r="1">
      <c r="A1" t="s"><v>0</v></c>
      <c r="B1" t="s"><v>1</v></c>
      <c r="C1" t="s"><v>2</v></c>
    </row>
    <row r="2">
      <c r="A2"><v>1</v></c>
      <c r="B2"><v>10</v></c>
      <c r="C2"><f t="shared" ref="C2:C4" si="0">A2*B2</f><v>10</v></c>
    </row>
    <row r="3">
      <c r="A3"><v>2</v></c>
      <c r="B3"><v>20</v></c>
      <c r="C3"><f t="shared" si="0"/><v>40</v></c>
    </row>
    <row r="4">
      <c r="A4"><v>3</v></c>
      <c r="B4"><v>30</v></c>
      <c r="C4"><f t="shared" si="0"/><v>90</v></c>
    </row>
    <row r="5">
      <c r="A5"><v>4</v></c>
      <c r="B5" t="e"><v>#DIV/0!</v></c>
      <c r="C5"><f>A5*B5</f><v>#DIV/0!</v></c>
    </row>
  </sheetData>
</worksheet>"""


def sheet2_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <dimension ref="A1:A1"/>
  <sheetData>
    <row r="1"><c r="A1" t="s"><v>3</v></c></row>
  </sheetData>
</worksheet>"""


def build_synthetic_xlsx(dest: Path, sheet2_state: str):
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", CONTENT_TYPES)
        zf.writestr("_rels/.rels", ROOT_RELS)
        zf.writestr("xl/workbook.xml", workbook_xml(sheet2_state))
        zf.writestr("xl/_rels/workbook.xml.rels", WORKBOOK_RELS)
        zf.writestr("xl/worksheets/sheet1.xml", sheet1_xml())
        zf.writestr("xl/worksheets/sheet2.xml", sheet2_xml())
        zf.writestr("xl/sharedStrings.xml", SHARED_STRINGS)
        zf.writestr("xl/styles.xml", STYLES)
        zf.writestr("docProps/core.xml", CORE_PROPS)
        zf.writestr("docProps/app.xml", APP_PROPS)


def read_csv(path: Path):
    with path.open(encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def run():
    tmpdir = Path(tempfile.mkdtemp(prefix="audit-xlsx-selftest-"))
    out_dir = tmpdir / "out"
    try:
        wb1 = tmpdir / "sintetico-um.xlsx"
        wb2 = tmpdir / "sintetico-dois.xlsx"
        build_synthetic_xlsx(wb1, sheet2_state="hidden")
        build_synthetic_xlsx(wb2, sheet2_state="visible")

        rc = audit_xlsx.main([
            "--input", str(wb1), "--input", str(wb2),
            "--output-dir", str(out_dir),
            "--workbook-id", "wbA", "--workbook-id", "wbB",
        ])
        assert rc == 0, "audit_xlsx.main deveria retornar 0"

        sheet_rows = read_csv(out_dir / "sheet_inventory.csv")
        assert len(sheet_rows) == 4, f"esperado 4 linhas de aba, veio {len(sheet_rows)}"
        hidden = [r for r in sheet_rows if r["workbook_id"] == "wbA" and r["sheet_name"] == "Auxiliar"]
        assert hidden and hidden[0]["visibility"] == "hidden", "aba Auxiliar de wbA deveria estar hidden"

        field_rows = read_csv(out_dir / "field_profile.csv")
        codigo_fields = [r for r in field_rows if r["field_name"] == "codigo"]
        assert codigo_fields, "campo 'codigo' deveria ter sido detectado"
        assert codigo_fields[0]["candidate_key_flag"] == "True", "codigo deveria ser candidato a chave"

        formula_rows = read_csv(out_dir / "formula_inventory.csv")
        # C2:C4 (formula compartilhada) e C5 (formula solta, mesma estrutura A#*B#)
        # devem cair no mesmo padrao normalizado -> 4 ocorrencias no total.
        shared_group = [r for r in formula_rows if r["occurrences"] == "4"]
        assert shared_group, "grupo de formulas equivalentes deveria ter 4 ocorrencias"
        assert shared_group[0]["direction"] == "vertical"

        quality_rows = read_csv(out_dir / "quality_issues.csv")
        error_issues = [r for r in quality_rows if r["issue_type"] == "celulas_com_erro"]
        assert error_issues, "celula de erro deveria gerar issue de qualidade"

        cross_rows = read_csv(out_dir / "cross_workbook_mapping.csv")
        sheet_matches = [r for r in cross_rows if r["basis"] == "nome_da_aba" and r["confidence"] == "ALTA"]
        assert sheet_matches, "abas com nome identico entre wbA e wbB deveriam casar com confianca ALTA"

        for name in ("workbook_inventory.csv", "dependency_inventory.csv",
                     "hidden_content_inventory.csv", "structural-audit.md"):
            assert (out_dir / name).exists(), f"arquivo de saida ausente: {name}"

        print("OK: todas as verificacoes do teste sintetico passaram")
        return 0
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(run())
