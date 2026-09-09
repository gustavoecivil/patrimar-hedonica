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


FK_TABLE_LEVEL_RE = re.compile(
    r"FOREIGN\s+KEY\s*\(([^)]*)\)\s*REFERENCES\s+(\w+)\.(\w+)\s*\(([^)]*)\)", re.IGNORECASE)
INLINE_COL_FK_RE = re.compile(
    r"^(\w+)\b.*?REFERENCES\s+(\w+)\.(\w+)\s*\((\w+)\)", re.IGNORECASE | re.DOTALL)
PRIMARY_KEY_TABLE_RE = re.compile(r"^PRIMARY\s+KEY\s*\(([^)]*)\)", re.IGNORECASE)
INSERT_HEADER_RE = re.compile(r"INSERT\s+INTO\s+(\w+)\.(\w+)\s*\(", re.IGNORECASE)


def _cols(text: str) -> tuple[str, ...]:
    return tuple(c.strip().lower() for c in text.split(",") if c.strip())


def extract_ddl_schema(sql_dir: Path, filenames: list[str]) -> dict:
    """Extrai, dos arquivos DDL, um mapa table -> {columns, pk, fks} usado
    para validar um seed sem precisar de um PostgreSQL real."""
    tables: dict[str, dict] = {}

    def get_table(name: str) -> dict:
        return tables.setdefault(name, {"columns": {}, "pk": None, "fks": []})

    for fname in filenames:
        path = sql_dir / fname
        if not path.exists():
            continue
        clean = strip_comments(path.read_text(encoding="utf-8"))
        for stmt in split_dollar_quoted(clean):
            stmt_norm = " ".join(stmt.split())

            m = CREATE_TABLE_HEADER_RE.search(stmt)
            if m:
                schema, table = m.group(1).lower(), m.group(2).lower()
                key = f"{schema}.{table}"
                body = extract_table_body(stmt, m.end() - 1)
                entry = get_table(key)
                for fragment in split_top_level_commas(body):
                    frag_norm = " ".join(fragment.split())
                    first_token = fragment.split()[0] if fragment.split() else ""

                    pk_m = PRIMARY_KEY_TABLE_RE.match(frag_norm)
                    if pk_m:
                        entry["pk"] = _cols(pk_m.group(1))
                        continue
                    fk_m = FK_TABLE_LEVEL_RE.search(frag_norm)
                    if fk_m:
                        src_cols = _cols(fk_m.group(1))
                        target = f"{fk_m.group(2).lower()}.{fk_m.group(3).lower()}"
                        target_cols = _cols(fk_m.group(4))
                        entry["fks"].append((src_cols, target, target_cols))
                        continue
                    if first_token.upper() in CONSTRAINT_KEYWORDS:
                        continue

                    col_name = first_token.lower()
                    not_null = bool(re.search(r"\bNOT\s+NULL\b", frag_norm, re.IGNORECASE))
                    is_pk_inline = bool(re.search(r"\bPRIMARY\s+KEY\b", frag_norm, re.IGNORECASE))
                    generated = bool(re.search(r"\bGENERATED\s+ALWAYS\s+AS\b", frag_norm, re.IGNORECASE))
                    has_default = bool(re.search(r"\bDEFAULT\b", frag_norm, re.IGNORECASE)) or generated
                    entry["columns"][col_name] = {
                        "not_null": not_null or is_pk_inline,
                        "has_default": has_default or is_pk_inline,
                        "generated": generated,
                    }
                    if is_pk_inline:
                        entry["pk"] = (col_name,)
                    inline_fk = INLINE_COL_FK_RE.match(frag_norm)
                    if inline_fk:
                        target = f"{inline_fk.group(2).lower()}.{inline_fk.group(3).lower()}"
                        entry["fks"].append(((col_name,), target, (inline_fk.group(4).lower(),)))
                continue

            m = ALTER_TABLE_FK_RE.search(stmt_norm)
            if m:
                src_schema, src_table, ref_schema, ref_table = m.groups()
                src_key = f"{src_schema.lower()}.{src_table.lower()}"
                target_key = f"{ref_schema.lower()}.{ref_table.lower()}"
                cols_m = re.search(r"FOREIGN\s+KEY\s*\(([^)]*)\)\s*REFERENCES\s+\w+\.\w+\s*\(([^)]*)\)",
                                    stmt_norm, re.IGNORECASE)
                if cols_m:
                    get_table(src_key)["fks"].append(
                        (_cols(cols_m.group(1)), target_key, _cols(cols_m.group(2)))
                    )
                continue

    return tables


def parse_seed_inserts(seed_text: str) -> list[tuple[str, list[str], list[str]]]:
    """Retorna [(schema.tabela, [colunas...], [valores literais...]), ...]
    na ordem em que aparecem no seed."""
    clean = strip_comments(seed_text)
    out = []
    for stmt in split_dollar_quoted(clean):
        m = INSERT_HEADER_RE.search(stmt)
        if not m:
            continue
        table = f"{m.group(1).lower()}.{m.group(2).lower()}"
        cols_body = extract_table_body(stmt, m.end() - 1)
        columns = [c.strip().lower() for c in split_top_level_commas(cols_body)]
        rest = stmt[m.end():]
        values_m = re.search(r"VALUES\s*\(", rest, re.IGNORECASE)
        if not values_m:
            continue
        values_body = extract_table_body(rest, values_m.end() - 1)
        values = split_top_level_commas(values_body)
        out.append((table, columns, values))
    return out


def validate_seed(ddl_schema: dict, seed_text: str) -> list[str]:
    findings: list[str] = []
    known_rows: dict[str, list[dict]] = {}

    for table, columns, values in parse_seed_inserts(seed_text):
        if table not in ddl_schema:
            findings.append(f"seed: INSERT em tabela desconhecida no DDL: {table}")
            known_rows.setdefault(table, []).append(dict(zip(columns, values)))
            continue

        entry = ddl_schema[table]
        unknown_cols = [c for c in columns if c not in entry["columns"]]
        for c in unknown_cols:
            findings.append(f"seed: {table} — coluna desconhecida no DDL: {c}")

        for c in columns:
            if c in entry["columns"] and entry["columns"][c]["generated"]:
                findings.append(f"seed: {table} — INSERT explicito em coluna GENERATED: {c}")

        required = [c for c, info in entry["columns"].items()
                    if info["not_null"] and not info["has_default"] and not info["generated"]]
        missing = [c for c in required if c not in columns]
        if missing:
            findings.append(f"seed: {table} — colunas obrigatorias ausentes no INSERT: {missing}")

        row = dict(zip(columns, values))

        for src_cols, target_table, target_cols in entry["fks"]:
            if not all(c in row for c in src_cols):
                continue
            src_values = tuple(row[c] for c in src_cols)
            if any(v.strip().upper() == "NULL" for v in src_values):
                continue
            candidates = known_rows.get(target_table, [])
            found = any(
                all(prev.get(tc) == sv for tc, sv in zip(target_cols, src_values))
                for prev in candidates
            )
            if not found:
                findings.append(
                    f"seed: {table}{src_cols} -> {target_table}{target_cols} nao resolvida "
                    f"(linha referenciada ainda nao inserida ou inexistente): valores={src_values}"
                )

        known_rows.setdefault(table, []).append(row)

    return findings


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
    parser.add_argument("--seed-file", default=None,
                         help="Caminho de um arquivo de seed .sql a validar contra o DDL "
                              "(tabelas/colunas existem, nenhuma coluna GENERATED recebe INSERT "
                              "explicito, colunas obrigatorias presentes, FKs resolviveis na "
                              "ordem em que as linhas aparecem).")
    args = parser.parse_args(argv)

    sql_dir = Path(args.sql_dir)
    findings = validate_files(sql_dir, args.file, args.forbidden_term)

    if args.seed_file:
        seed_path = Path(args.seed_file)
        if not seed_path.exists():
            findings.append(f"seed: arquivo nao encontrado: {args.seed_file}")
        else:
            for term in args.forbidden_term:
                if term and term.lower() in seed_path.read_text(encoding="utf-8").lower():
                    findings.append(f"{args.seed_file}: termo proibido encontrado: {term!r}")
            ddl_schema = extract_ddl_schema(sql_dir, args.file)
            findings.extend(validate_seed(ddl_schema, seed_path.read_text(encoding="utf-8")))

    if findings:
        print(f"FALHOU: {len(findings)} problema(s) encontrado(s)")
        for f in findings:
            print(f" - {f}")
        return 1

    suffix = " + seed" if args.seed_file else ""
    print(f"OK: {len(args.file)} arquivo(s) de DDL{suffix} validados, nenhum problema estrutural encontrado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
