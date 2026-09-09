#!/usr/bin/env python3
"""Teste de fumaca de scripts/validate_db_v2.py usando arquivos .sql
sinteticos minimos (nenhum conteudo real do projeto). Verifica tanto o
caminho feliz (schema valido) quanto a deteccao de problemas: FK para
tabela inexistente/ainda nao criada, nome fora de snake_case, DROP
destrutivo e termo proibido.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import validate_db_v2 as vdb

VALID_FILE_A = """
CREATE SCHEMA IF NOT EXISTS demo_core;

CREATE TABLE demo_core.widgets (
  id UUID PRIMARY KEY,
  name TEXT NOT NULL,
  CONSTRAINT uq_widgets_name UNIQUE (name)
);
"""

VALID_FILE_B = """
CREATE SCHEMA IF NOT EXISTS demo_orders;

CREATE TABLE demo_orders.orders (
  id UUID PRIMARY KEY,
  widget_id UUID NOT NULL REFERENCES demo_core.widgets(id),
  quantity INTEGER CHECK (quantity > 0)
);

CREATE OR REPLACE VIEW demo_orders.v_order_summary AS
  SELECT widget_id, count(*) FROM demo_orders.orders GROUP BY widget_id;
"""

BROKEN_FILE_FORWARD_REF = """
CREATE SCHEMA IF NOT EXISTS demo_orders;

CREATE TABLE demo_orders.orders (
  id UUID PRIMARY KEY,
  widget_id UUID NOT NULL REFERENCES demo_core.widgets(id)
);
"""

BROKEN_FILE_BAD_NAMING = """
CREATE SCHEMA IF NOT EXISTS demo_core;

CREATE TABLE demo_core.Widgets (
  id UUID PRIMARY KEY,
  "CamelCaseColumn" TEXT
);
"""

BROKEN_FILE_DROP = """
DROP TABLE demo_core.widgets;
"""

SEED_GOOD = """
INSERT INTO demo_core.widgets (id, name) VALUES ('11111111-1111-1111-1111-111111111111', 'Widget A');
INSERT INTO demo_orders.orders (id, widget_id, quantity) VALUES ('22222222-2222-2222-2222-222222222222', '11111111-1111-1111-1111-111111111111', 3);
"""

SEED_MISSING_REQUIRED_COLUMN = """
INSERT INTO demo_core.widgets (id) VALUES ('11111111-1111-1111-1111-111111111111');
"""

SEED_FK_NOT_YET_INSERTED = """
INSERT INTO demo_orders.orders (id, widget_id, quantity) VALUES ('22222222-2222-2222-2222-222222222222', '99999999-9999-9999-9999-999999999999', 3);
"""


def write(tmp: Path, name: str, content: str) -> None:
    (tmp / name).write_text(content, encoding="utf-8")


def run():
    tmp = Path(tempfile.mkdtemp(prefix="validate-db-v2-selftest-"))
    try:
        # caminho feliz
        write(tmp, "001_a.sql", VALID_FILE_A)
        write(tmp, "002_b.sql", VALID_FILE_B)
        rc = vdb.main(["--sql-dir", str(tmp), "--file", "001_a.sql", "--file", "002_b.sql"])
        assert rc == 0, "schema sintetico valido deveria passar sem problemas"

        # FK para frente (tabela referenciada so existiria depois, mas o
        # arquivo que a criaria nao foi incluido nesta chamada)
        tmp2 = Path(tempfile.mkdtemp(prefix="validate-db-v2-selftest-fwd-"))
        write(tmp2, "001_only_orders.sql", BROKEN_FILE_FORWARD_REF)
        findings = vdb.validate_files(tmp2, ["001_only_orders.sql"], [])
        assert any("antes de ele existir" in f for f in findings), \
            "referencia a tabela inexistente deveria ser sinalizada"
        shutil.rmtree(tmp2, ignore_errors=True)

        # nomenclatura fora de snake_case
        tmp3 = Path(tempfile.mkdtemp(prefix="validate-db-v2-selftest-naming-"))
        write(tmp3, "001_bad_naming.sql", BROKEN_FILE_BAD_NAMING)
        findings = vdb.validate_files(tmp3, ["001_bad_naming.sql"], [])
        assert any("snake_case" in f for f in findings), \
            "nome fora de snake_case deveria ser sinalizado"
        shutil.rmtree(tmp3, ignore_errors=True)

        # DROP destrutivo
        tmp4 = Path(tempfile.mkdtemp(prefix="validate-db-v2-selftest-drop-"))
        write(tmp4, "001_drop.sql", BROKEN_FILE_DROP)
        findings = vdb.validate_files(tmp4, ["001_drop.sql"], [])
        assert any("DROP destrutivo" in f for f in findings), \
            "DROP TABLE deveria ser sinalizado"
        shutil.rmtree(tmp4, ignore_errors=True)

        # termo proibido
        tmp5 = Path(tempfile.mkdtemp(prefix="validate-db-v2-selftest-forbidden-"))
        write(tmp5, "001_a.sql", VALID_FILE_A)
        findings = vdb.validate_files(tmp5, ["001_a.sql"], ["widgets"])
        assert any("termo proibido" in f for f in findings), \
            "termo proibido presente no arquivo deveria ser sinalizado"
        shutil.rmtree(tmp5, ignore_errors=True)

        # validacao de seed: caminho feliz
        tmp6 = Path(tempfile.mkdtemp(prefix="validate-db-v2-selftest-seed-ok-"))
        write(tmp6, "001_a.sql", VALID_FILE_A)
        write(tmp6, "002_b.sql", VALID_FILE_B)
        write(tmp6, "seed.sql", SEED_GOOD)
        rc = vdb.main(["--sql-dir", str(tmp6), "--file", "001_a.sql", "--file", "002_b.sql",
                       "--seed-file", str(tmp6 / "seed.sql")])
        assert rc == 0, "seed sintetico valido deveria passar sem problemas"
        shutil.rmtree(tmp6, ignore_errors=True)

        # validacao de seed: coluna obrigatoria ausente
        tmp7 = Path(tempfile.mkdtemp(prefix="validate-db-v2-selftest-seed-missing-"))
        write(tmp7, "001_a.sql", VALID_FILE_A)
        write(tmp7, "002_b.sql", VALID_FILE_B)
        ddl_schema = vdb.extract_ddl_schema(tmp7, ["001_a.sql", "002_b.sql"])
        findings = vdb.validate_seed(ddl_schema, SEED_MISSING_REQUIRED_COLUMN)
        assert any("obrigatorias ausentes" in f for f in findings), \
            "coluna NOT NULL sem default ausente do INSERT deveria ser sinalizada"
        shutil.rmtree(tmp7, ignore_errors=True)

        # validacao de seed: FK aponta para linha nunca inserida (ordem/dado ausente)
        findings = vdb.validate_seed(ddl_schema, SEED_FK_NOT_YET_INSERTED)
        assert any("nao resolvida" in f for f in findings), \
            "FK apontando para linha inexistente/fora de ordem deveria ser sinalizada"

        print("OK: todas as verificacoes do teste sintetico de validate_db_v2 passaram")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(run())
