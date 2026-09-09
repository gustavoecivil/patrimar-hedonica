#!/usr/bin/env python3
"""Validação estrutural genérica de um diretório de arquivos .sql,
sem depender de um PostgreSQL real (útil quando nenhum servidor local
está disponível).

Verifica, na ordem dos arquivos informada (por nome, ordenados
lexicograficamente por padrão):

- todos os arquivos esperados existem;
- nenhum DROP destrutivo;
- convenção de nomenclatura snake_case para schemas/tabelas/colunas
  criadas;
- toda referência REFERENCES (inline ou via ALTER TABLE ... FOREIGN
  KEY) aponta para schema.tabela já conhecido no ponto da execução
  (permite o padrão de FK adicionada em arquivo posterior via ALTER
  TABLE, desde que a tabela de destino já exista até aquele ponto);
- nenhum termo de uma lista de padrões proibidos (para uso conjunto
  com verificação de não vazamento de dado privado — a lista de
  termos é passada pelo chamador, este script não contém nenhum nome
  privado embutido).

Não executa nada contra um banco real. Não contém nomes de arquivo,
caminhos absolutos, ou dado privado de nenhum projeto especifico -
tudo entra via argumento de linha de comando.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SNAKE_RE = re.compile(r"^[a-z_][a-z0-9_]*$")

CREATE_SCHEMA_RE = re.compile(r"CREATE\s+SCHEMA\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)", re.IGNORECASE)
CREATE_TABLE_HEADER_RE = re.compile(r"CREATE\s+TABLE\s+(\w+)\.(\w+)\s*\(", re.IGNORECASE)
CREATE_VIEW_RE = re.compile(r"CREATE\s+(?:OR\s+REPLACE\s+)?VIEW\s+(\w+)\.(\w+)", re.IGNORECASE)
ALTER_TABLE_FK_RE = re.compile(
    r"ALTER\s+TABLE\s+(\w+)\.(\w+)\s+ADD\s+CONSTRAINT\s+\w+\s+FOREIGN\s+KEY\s*\([^)]*\)\s*"
    r"REFERENCES\s+(\w+)\.(\w+)", re.IGNORECASE)
INLINE_REF_RE = re.compile(r"REFERENCES\s+(\w+)\.(\w+)", re.IGNORECASE)
CONSTRAINT_KEYWORDS = {"PRIMARY", "FOREIGN", "UNIQUE", "CHECK", "CONSTRAINT"}
DROP_RE = re.compile(r"\bDROP\s+(TABLE|SCHEMA|VIEW|DATABASE)\b", re.IGNORECASE)


def split_top_level_commas(body: str) -> list[str]:
    """Divide o corpo de um CREATE TABLE em definicoes de coluna/constraint,
    respeitando parenteses aninhados (ex.: CHECK(...), NUMERIC(9,2))."""
    parts, buf, depth = [], [], 0
    for ch in body:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return [p.strip() for p in parts if p.strip()]


def extract_table_body(stmt: str, start_idx: int) -> str:
    """A partir do '(' de abertura em start_idx, retorna o conteudo entre
    ele e seu ')' correspondente (respeitando aninhamento)."""
    depth = 0
    for i in range(start_idx, len(stmt)):
        if stmt[i] == "(":
            depth += 1
        elif stmt[i] == ")":
            depth -= 1
            if depth == 0:
                return stmt[start_idx + 1:i]
    return stmt[start_idx + 1:]


def strip_comments(sql: str) -> str:
    sql = re.sub(r"--.*?$", "", sql, flags=re.MULTILINE)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    return sql


def split_dollar_quoted(sql: str) -> list[str]:
    """Divide em statements por ';', preservando corpos $$ ... $$ inteiros
    (funções PL/pgSQL) como um unico statement."""
    parts = []
    buf = []
    in_dollar = False
    i = 0
    while i < len(sql):
        if sql[i:i + 2] == "$$":
            in_dollar = not in_dollar
            buf.append("$$")
            i += 2
            continue
        if sql[i] == ";" and not in_dollar:
            parts.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(sql[i])
        i += 1
    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return [p.strip() for p in parts if p.strip()]


def validate_naming(name: str, kind: str, findings: list[str], location: str):
    if not SNAKE_RE.match(name):
        findings.append(f"{location}: {kind} '{name}' nao segue snake_case")


def validate_files(sql_dir: Path, filenames: list[str], forbidden_terms: list[str]) -> list[str]:
    findings: list[str] = []
    known_objects: set[str] = set()   # "schema.table"
    known_schemas: set[str] = set()

    for fname in filenames:
        path = sql_dir / fname
        if not path.exists():
            findings.append(f"arquivo esperado ausente: {fname}")
            continue
        raw = path.read_text(encoding="utf-8")

        for term in forbidden_terms:
            if term and term.lower() in raw.lower():
                findings.append(f"{fname}: termo proibido encontrado: {term!r}")

        if DROP_RE.search(strip_comments(raw)):
            findings.append(f"{fname}: contem DROP destrutivo (TABLE/SCHEMA/VIEW/DATABASE)")

        clean = strip_comments(raw)
        for stmt in split_dollar_quoted(clean):
            stmt_norm = " ".join(stmt.split())

            m = CREATE_SCHEMA_RE.match(stmt_norm)
            if m:
                schema = m.group(1)
                validate_naming(schema, "schema", findings, fname)
                known_schemas.add(schema.lower())
                continue

            m = CREATE_TABLE_HEADER_RE.search(stmt)
            if m:
                schema, table = m.group(1), m.group(2)
                body = extract_table_body(stmt, m.end() - 1)
                validate_naming(schema, "schema", findings, fname)
                validate_naming(table, "tabela", findings, fname)
                known_objects.add(f"{schema.lower()}.{table.lower()}")
                for fragment in split_top_level_commas(body):
                    first_token = fragment.split()[0] if fragment.split() else ""
                    if first_token.upper() in CONSTRAINT_KEYWORDS:
                        continue
                    validate_naming(first_token, "coluna", findings, f"{fname}:{schema}.{table}")
                for ref_schema, ref_table in INLINE_REF_RE.findall(body):
                    target = f"{ref_schema.lower()}.{ref_table.lower()}"
                    if target not in known_objects:
                        findings.append(
                            f"{fname}: {schema}.{table} referencia {target} antes de ele existir"
                        )
                continue

            m = CREATE_VIEW_RE.search(stmt_norm)
            if m:
                schema, view = m.group(1), m.group(2)
                validate_naming(schema, "schema", findings, fname)
                validate_naming(view, "view", findings, fname)
                known_objects.add(f"{schema.lower()}.{view.lower()}")
                continue

            m = ALTER_TABLE_FK_RE.search(stmt_norm)
            if m:
                src_schema, src_table, ref_schema, ref_table = m.groups()
                src = f"{src_schema.lower()}.{src_table.lower()}"
                target = f"{ref_schema.lower()}.{ref_table.lower()}"
                if src not in known_objects:
                    findings.append(f"{fname}: ALTER TABLE em {src} antes de ele existir")
                if target not in known_objects:
                    findings.append(f"{fname}: FK de {src} para {target} antes de ele existir")
                continue

    return findings


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Validacao estrutural de um conjunto de arquivos .sql, sem executar contra um banco real."
    )
    parser.add_argument("--sql-dir", required=True, help="Diretorio contendo os arquivos .sql")
    parser.add_argument("--file", action="append", required=True,
                         help="Nome de arquivo dentro de --sql-dir, na ordem de execucao. "
                              "Pode ser passado varias vezes.")
    parser.add_argument("--forbidden-term", action="append", default=[],
                         help="Termo que NAO deve aparecer em nenhum arquivo (case-insensitive). "
                              "Pode ser passado varias vezes.")
    args = parser.parse_args(argv)

    sql_dir = Path(args.sql_dir)
    findings = validate_files(sql_dir, args.file, args.forbidden_term)

    if findings:
        print(f"FALHOU: {len(findings)} problema(s) encontrado(s)")
        for f in findings:
            print(f" - {f}")
        return 1

    print(f"OK: {len(args.file)} arquivo(s) validados, nenhum problema estrutural encontrado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
