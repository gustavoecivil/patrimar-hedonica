#!/usr/bin/env python3
"""Scanner de privacidade do bundle publicado (Fase 3E, Passos 6/28).

Varre um diretorio de publicacao (por padrao `web/pricing-intelligence/`
— o mesmo apontado por `netlify.toml` [build] publish) procurando por
indicadores estruturais de vazamento de dados privados, e BLOQUEIA
(exit code != 0) se encontrar algum.

Importante: este script NUNCA contem, ele mesmo, nenhum nome real de
empreendimento, senha, hash de XLSX ou qualquer outro valor privado —
ele e versionado e publicado junto do resto do repositorio, entao so
pode conter padroes GENERICOS (regex estrutural), nunca segredos
hardcoded (ver docs/04-DECISOES.md D4/D6).

Para conferencia adicional com os valores reais (nomes dos dois
empreendimentos, etc.), passe --markers-file apontando para um arquivo
LOCAL, nunca commitado (ex.: algo dentro de data/restricted/), com um
marcador por linha. Sem esse arquivo, o scanner roda só com os
checks estruturais/genericos abaixo — que já cobrem a maior parte dos
riscos reais (credenciais, .env, hash de XLSX, caminho data/restricted,
nome de arquivo .xlsx).

Uso:
    python scripts/scan_deploy_privacy.py
    python scripts/scan_deploy_privacy.py --dir web/pricing-intelligence
    python scripts/scan_deploy_privacy.py --markers-file data/restricted/privacy_markers.txt

Exit code 0 = limpo. Exit code 1 = vazamento encontrado (bloquear deploy).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# Extensoes de texto que fazem sentido varrer (bundle web + eventuais
# arquivos de config). Binarios (png/ico/woff) sao ignorados.
TEXT_EXTENSIONS = {".html", ".htm", ".js", ".mjs", ".css", ".json", ".txt", ".md", ".toml", ".svg"}

# Padroes estruturais genericos — nenhum deles contem um valor privado
# em si, apenas a FORMA de um valor privado.
STRUCTURAL_PATTERNS = [
    ("PGPASSWORD/credencial libpq", re.compile(r"PG(PASSWORD|HOST|USER|DATABASE)\s*=\s*\S+")),
    ("connection string Postgres", re.compile(r"postgres(ql)?://[^\s'\"]+:[^\s'\"]+@")),
    ("DATABASE_URL com credencial", re.compile(r"DATABASE_URL\s*=\s*\S+")),
    ("hash sha256 bruto (64 hex)", re.compile(r"\b[a-fA-F0-9]{64}\b")),
    ("nome de arquivo .xlsx", re.compile(r"[^\s'\"]+\.xlsx", re.IGNORECASE)),
    ("caminho data/restricted", re.compile(r"data[/\\]restricted")),
    ("nome de banco privado", re.compile(r"patrimar_pricing_v2_private_dev")),
    ("referencia a PRIVATE_API_BASE != 127.0.0.1", re.compile(r"PRIVATE_API_BASE\s*=\s*['\"]http://(?!127\.0\.0\.1)")),
]

FORBIDDEN_FILENAMES = {".env", ".env.local"}
FORBIDDEN_SUFFIXES = {".xlsx", ".xls", ".sql", ".py", ".ps1"}


def iter_deploy_files(root: Path):
    for path in root.rglob("*"):
        if path.is_file():
            yield path


def scan_structural(root: Path) -> list[str]:
    findings = []
    for path in iter_deploy_files(root):
        rel = path.relative_to(root)
        if path.name in FORBIDDEN_FILENAMES or path.name.startswith(".env"):
            findings.append(f"{rel}: arquivo de ambiente (.env*) nao deveria estar no bundle publicado")
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            findings.append(f"{rel}: extensao '{path.suffix}' nao deveria estar no bundle publicado (script/planilha/DDL)")
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for label, pattern in STRUCTURAL_PATTERNS:
            m = pattern.search(text)
            if m:
                findings.append(f"{rel}: possivel '{label}' encontrado (trecho: {m.group(0)[:40]!r})")
    return findings


def scan_markers(root: Path, markers_file: Path) -> list[str]:
    findings = []
    markers = [m.strip() for m in markers_file.read_text(encoding="utf-8").splitlines() if m.strip() and not m.strip().startswith("#")]
    if not markers:
        return findings
    for path in iter_deploy_files(root):
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for marker in markers:
            if marker in text:
                findings.append(f"{path.relative_to(root)}: marcador privado encontrado ({marker[:4]}***)")
    return findings


def check_demo_mode(root: Path) -> list[str]:
    """Sanity check: se existir demo-data.json, meta.mode precisa ser 'DEMO'."""
    findings = []
    demo_file = root / "demo-data.json"
    if demo_file.exists():
        import json
        try:
            data = json.loads(demo_file.read_text(encoding="utf-8"))
            if data.get("meta", {}).get("mode") != "DEMO":
                findings.append(f"demo-data.json: meta.mode nao e 'DEMO' (encontrado: {data.get('meta', {}).get('mode')!r}) "
                                 "— risco de estar publicando um dataset PRIVATE por engano")
        except (json.JSONDecodeError, OSError) as exc:
            findings.append(f"demo-data.json: nao foi possivel validar ({exc})")
    return findings


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dir", default="web/pricing-intelligence", help="Diretorio de publicacao a varrer.")
    parser.add_argument("--markers-file", default=None,
                         help="Arquivo LOCAL (nunca commitado) com um marcador privado por linha, para conferencia extra.")
    args = parser.parse_args(argv)

    root = Path(args.dir).resolve()
    if not root.is_dir():
        print(f"ERRO: diretorio de publicacao nao encontrado: {root}", file=sys.stderr)
        return 1

    findings = scan_structural(root)
    findings += check_demo_mode(root)

    if args.markers_file:
        markers_path = Path(args.markers_file)
        if markers_path.exists():
            findings += scan_markers(root, markers_path)
        else:
            print(f"[aviso] --markers-file {markers_path} nao existe — pulando conferencia extra.", file=sys.stderr)

    if findings:
        print(f"FALHA: {len(findings)} indicio(s) de dado privado no bundle publicado ({root}):", file=sys.stderr)
        for f in findings:
            print(f"  - {f}", file=sys.stderr)
        print("\nDEPLOY BLOQUEADO.", file=sys.stderr)
        return 1

    print(f"OK: nenhum indicio de dado privado encontrado em {root}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
