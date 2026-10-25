"""Verifica la navegación de la documentación Markdown del repositorio.

Reglas comprobadas sobre cada ``.md`` rastreado por Git (excepto
``node_modules``):

1. Todo enlace relativo resuelve a un archivo o carpeta rastreado.
2. Todo ``.md`` distinto de ``README.md`` está enlazado desde ``README.md``.
3. Todo ``.md`` distinto de ``README.md`` enlaza de vuelta a ``README.md``.
4. Todo ``.md`` dentro de ``docs/03 Implementación/Sprint 02/`` enlaza al
   índice del Sprint 2.

Solo usa la librería estándar. Uso: ``python scripts/check_docs.py``.
Devuelve 0 si no hay errores y 1 en caso contrario.
"""

from __future__ import annotations

import posixpath
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote

ROOT_README = "README.md"
SPRINT2_DIR = "docs/03 Implementación/Sprint 02"
SPRINT2_INDEX = f"{SPRINT2_DIR}/README.md"

# La plantilla de PR se copia literalmente en la descripción de cada PR de
# GitHub; un enlace de retorno al README aparecería en todos los PRs y, además,
# su ruta relativa no resuelve desde la vista del PR. Se enlaza desde el README
# pero se excluye de la regla de retorno.
BACKLINK_EXCLUDED = frozenset({".github/pull_request_template.md"})

INLINE_LINK = re.compile(
    r"!?\[(?:[^\[\]]|\[[^\]]*\])*\]"  # texto del enlace
    r"\(\s*(<[^>]*>|[^)\s]+)(?:\s+\"[^\"]*\")?\s*\)"  # destino y título
)
REFERENCE_DEF = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*(<[^>]*>|\S+)", re.MULTILINE)
FENCE = re.compile(r"^\s{0,3}(```|~~~)")
INLINE_CODE = re.compile(r"`+[^`]*`+")
EXTERNAL = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


def nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


@dataclass
class Report:
    errors: dict[str, list[str]] = field(default_factory=dict)

    def add(self, rule: str, message: str) -> None:
        self.errors.setdefault(rule, []).append(message)

    @property
    def total(self) -> int:
        return sum(len(items) for items in self.errors.values())


def tracked_files(repo: Path) -> list[str]:
    output = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo,
        check=True,
        capture_output=True,
    ).stdout.decode("utf-8")
    return [nfc(path) for path in output.split("\0") if path]


def markdown_files(files: list[str]) -> list[str]:
    return sorted(
        path
        for path in files
        if path.lower().endswith(".md") and "node_modules/" not in path
    )


def strip_code(text: str) -> str:
    """Elimina bloques y fragmentos de código para no validar ejemplos."""
    lines: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if FENCE.match(line):
            in_fence = not in_fence
            lines.append("")
            continue
        lines.append("" if in_fence else INLINE_CODE.sub("", line))
    return "\n".join(lines)


def extract_targets(text: str) -> list[tuple[int, str]]:
    """Devuelve (línea, destino) de los enlaces inline y de referencia."""
    clean = strip_code(text)
    targets: list[tuple[int, str]] = []
    for pattern in (INLINE_LINK, REFERENCE_DEF):
        for match in pattern.finditer(clean):
            raw = match.group(1)
            if raw.startswith("<") and raw.endswith(">"):
                raw = raw[1:-1]
            line = clean.count("\n", 0, match.start()) + 1
            targets.append((line, raw.strip()))
    return targets


def resolve(source: str, target: str) -> str | None:
    """Resuelve un destino relativo a una ruta del repositorio.

    Devuelve ``None`` para enlaces externos o anclas internas.
    """
    if not target or target.startswith("#") or EXTERNAL.match(target):
        return None
    path = unquote(target.split("#", 1)[0].split("?", 1)[0])
    if not path:
        return None
    if path.startswith("/"):
        joined = path.lstrip("/")
    else:
        joined = posixpath.join(posixpath.dirname(source), path)
    return nfc(posixpath.normpath(joined))


def exists(path: str, files: set[str], directories: set[str]) -> bool:
    return path in files or path.rstrip("/") in directories or path == "."


def all_directories(files: set[str]) -> set[str]:
    directories: set[str] = set()
    for path in files:
        parent = posixpath.dirname(path)
        while parent:
            directories.add(parent)
            parent = posixpath.dirname(parent)
    return directories


def check(repo: Path) -> Report:
    files_list = tracked_files(repo)
    files = set(files_list)
    directories = all_directories(files)
    docs = markdown_files(files_list)
    report = Report()
    links: dict[str, set[str]] = {}

    for doc in docs:
        text = nfc((repo / doc).read_text(encoding="utf-8"))
        resolved: set[str] = set()
        for line, target in extract_targets(text):
            path = resolve(doc, target)
            if path is None:
                continue
            if not exists(path, files, directories):
                report.add(
                    "Enlaces relativos rotos",
                    f"{doc}:{line} -> {target}",
                )
                continue
            resolved.add(path)
        links[doc] = resolved

    from_readme = links.get(ROOT_README, set())
    for doc in docs:
        if doc == ROOT_README:
            continue
        if doc not in from_readme:
            report.add("Documentos no enlazados desde README.md", doc)
        if doc not in BACKLINK_EXCLUDED and ROOT_README not in links[doc]:
            report.add("Documentos sin enlace de retorno a README.md", doc)
        if (
            doc.startswith(f"{SPRINT2_DIR}/")
            and doc != SPRINT2_INDEX
            and SPRINT2_INDEX not in links[doc]
        ):
            report.add("Documentos del Sprint 2 sin enlace a su índice", doc)
    return report


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    repo = Path(__file__).resolve().parent.parent
    report = check(repo)
    if report.total == 0:
        print("check_docs: OK. Enlaces, índice del README y retornos correctos.")
        return 0
    for rule, items in report.errors.items():
        print(f"\n{rule} ({len(items)}):")
        for item in items:
            print(f"  - {item}")
    print(f"\ncheck_docs: {report.total} error(es).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
