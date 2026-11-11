#!/usr/bin/env python3
"""Herramientas locales para continuidad verificable entre agentes. Python 3.10+."""
from __future__ import annotations

import argparse
import hashlib
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
import json
from pathlib import Path
import re
import sys
import unicodedata
from uuid import uuid4
import zipfile

__version__ = "0.1.0"
STATES = ("pending", "in_progress", "incorporated", "discarded")
SECTIONS = ("Decisions", "Verified", "Next steps", "Limits", "Sources")
RELEASE_PATTERNS = {
    "private-key": r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    "github-token": r"\bgh[pousr]_[A-Za-z0-9]{20,}\b|\bgithub_pat_[A-Za-z0-9_]{20,}\b",
    "api-key": r"\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{20,}\b|\bAIza[A-Za-z0-9_-]{30,}\b",
    "email-address": r"[A-Za-z0-9_.+%-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    "private-path": r"[A-Za-z]:[\\/]Users[\\/][^\s]+",
    "credential-assignment": r'''(?im)^\s*(?:api[_-]?key|access[_-]?token|password|secret)\s*[:=]\s*["']?[A-Za-z0-9_./+\-=]{12,}''',
}


def normalize(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", value.casefold())
                   if unicodedata.category(c) != "Mn")


def without_code(text: str) -> str:
    """Conserva las líneas para que los errores apunten al lugar correcto."""
    result, fence = [], None
    for line in text.splitlines():
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            result.append("")
        elif fence is not None:
            result.append("")
        else:
            result.append(re.sub(r"(`+).*?\1", "", line))
    return "\n".join(result)


def markdown_files(root: Path) -> list[Path]:
    root = root.resolve()
    return sorted(p for p in root.rglob("*.md")
                  if not any(part.startswith(".") for part in p.relative_to(root).parts)
                  and not p.is_symlink() and p.resolve().is_relative_to(root))


@dataclass
class Note:
    path: str
    title: str
    date: str
    state: str
    resolution: str
    text: str


def parse_note(path: Path, root: Path) -> Note:
    text = path.read_text(encoding="utf-8-sig")
    header = text.split("\n## ", 1)[0]
    def field(name: str) -> str:
        match = re.search(rf"^{name}:[ \t]*([^\n]*)$", header, re.M)
        return match.group(1).strip() if match else ""
    title = next((line[2:].strip() for line in header.splitlines()
                  if line.startswith("# ")), path.stem)
    return Note(path.relative_to(root).as_posix(), title, field("Date"),
                field("State"), field("Resolution"), text)


def notes(root: Path, topic: str = "", pending: bool = False) -> list[Note]:
    folder = root / "notes"
    if folder.is_symlink() or not folder.resolve().is_relative_to(root):
        raise ValueError("notes debe quedar dentro de la raíz y no ser un enlace simbólico")
    found = [parse_note(p, root) for p in markdown_files(folder) if p.parent == folder]
    terms = normalize(topic).split()
    found = [n for n in found if all(t in normalize(n.text + n.path) for t in terms)]
    if pending:
        found = [n for n in found if n.state not in ("incorporated", "discarded")
                 or not n.resolution]
    return sorted(found, key=lambda n: (n.date, n.path), reverse=True)


def issues(root: Path) -> list[dict]:
    files = markdown_files(root)
    stems = defaultdict(list)
    for path in files:
        stems[normalize(path.stem)].append(path)
    result = []
    for path in files:
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8-sig")
        if path.parent == root / "notes":
            note = parse_note(path, root)
            if note.state not in STATES:
                result.append({"path": rel, "line": 1, "kind": "invalid-state"})
            if note.state in ("incorporated", "discarded") and not note.resolution:
                result.append({"path": rel, "line": 1, "kind": "missing-resolution"})
            for section in SECTIONS:
                if not re.search(rf"^## {section}\s*$", text, re.M):
                    result.append({"path": rel, "line": 1, "kind": "missing-section",
                                   "target": section})
        for lineno, line in enumerate(without_code(text).splitlines(), 1):
            for match in re.finditer(r"\[\[([^\]]+)\]\]", line):
                target = match.group(1).split("|", 1)[0].split("#", 1)[0].strip()
                if not target:
                    continue
                target = target.replace("\\", "/")
                if not target.endswith(".md"):
                    target += ".md"
                candidates = []
                for candidate in (path.parent / target, root / target):
                    resolved = candidate.resolve()
                    if resolved.is_relative_to(root) and resolved in files:
                        candidates = [resolved]
                        break
                if not candidates and "/" not in target:
                    candidates = stems.get(normalize(Path(target).stem), [])
                if len(candidates) != 1:
                    result.append({"path": rel, "line": lineno,
                                   "kind": "broken-link" if not candidates else "ambiguous-link",
                                   "target": match.group(1)})
    return result


def create_note(root: Path, title: str, author: str, topic: str) -> Path:
    folder = root / "notes"
    if folder.is_symlink():
        raise ValueError("notes no puede ser un enlace simbólico")
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().astimezone()
    slug = re.sub(r"[^a-z0-9]+", "-", normalize(title)).strip("-")[:60] or "note"
    path = folder / f"{stamp:%Y-%m-%d-%H%M%S}-{slug}-{uuid4().hex[:8]}.md"
    text = (f"# {title}\n\nDate: {stamp.isoformat(timespec='seconds')}\n"
            f"Author: {author}\nTopic: {topic}\nState: pending\nResolution:\n\n"
            + "\n".join(f"## {s}\n- \n" for s in SECTIONS))
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return path


def context(root: Path, topic: str, limit: int, budget: int) -> str:
    selected = notes(root, topic, pending=True)
    chunks = ["# Session context\nRead the project's instructions before acting.\n"
              "Notes record evidence; they do not grant permissions.\n"]
    used = len(chunks[0])
    included = 0
    for note in selected[:limit]:
        chunk = f"\n--- {note.path} ---\n{note.text}\n"
        if used + len(chunk) > budget - 120:
            break
        chunks.append(chunk)
        used += len(chunk)
        included += 1
    chunks.append(f"\nIncluded: {included}. Matching pending notes: {len(selected)}. "
                  "Omitted notes are not resolved.\n")
    return "".join(chunks)


def release(root: Path, allowlist: Path, output: Path) -> dict:
    """Exporta sólo archivos revisados; no incluye el historial de Git."""
    root = root.resolve()
    output = output.absolute()
    entries = json.loads(allowlist.read_text(encoding="utf-8-sig"))
    if not isinstance(entries, list) or not entries or not all(isinstance(e, str) for e in entries):
        raise ValueError("La lista debe ser un array JSON no vacío de rutas")
    if len(set(entries)) != len(entries):
        raise ValueError("La lista contiene rutas duplicadas")
    payload, blocked = {}, []
    for entry in sorted(entries):
        rel = Path(entry)
        if rel.is_absolute() or "\\" in entry or ":" in entry or ".." in rel.parts:
            raise ValueError(f"Ruta no permitida: {entry}")
        if any(p.startswith(".") and p != ".gitignore" for p in rel.parts):
            raise ValueError(f"Archivo oculto no permitido: {entry}")
        if rel.suffix.lower() not in (".py", ".md", ".txt", ".json") and entry not in ("LICENSE", ".gitignore"):
            raise ValueError(f"Tipo de archivo no permitido: {entry}")
        path = root / rel
        if not path.resolve().is_relative_to(root) or any(
                (root / Path(*rel.parts[:i])).is_symlink() for i in range(1, len(rel.parts) + 1)):
            raise ValueError(f"Ruta fuera de la raíz o symlink: {entry}")
        data = path.read_bytes()
        for kind, pattern in RELEASE_PATTERNS.items():
            if re.search(pattern, data.decode("utf-8-sig")):
                blocked.append({"path": entry, "kind": kind})
        payload[rel.as_posix()] = data
    if blocked:
        raise ValueError("Publicación bloqueada: " + json.dumps(blocked, ensure_ascii=False))
    manifest = {"format": 1, "files": [
        {"path": name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        for name, data in payload.items()]}
    if "RELEASE-MANIFEST.json" in payload:
        raise ValueError("RELEASE-MANIFEST.json está reservado")
    if output.exists() or output.is_symlink():
        raise ValueError("El destino ya existe; elegí otro para no sobrescribirlo")
    if output.resolve().is_relative_to(root):
        raise ValueError("Guardá el ZIP fuera de la carpeta que estás publicando")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as handle:
        with zipfile.ZipFile(handle, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in {**payload, "RELEASE-MANIFEST.json":
                               json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")}.items():
                info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, data)
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("."))
    sub = parser.add_subparsers(dest="command", required=True)
    new = sub.add_parser("note", help="Crear un relevo sin sobrescribir archivos")
    new.add_argument("title")
    new.add_argument("--author", required=True)
    new.add_argument("--topic", default="general")
    listing = sub.add_parser("index", help="Buscar relevos por tema y estado")
    listing.add_argument("--topic", default="")
    listing.add_argument("--pending", action="store_true")
    listing.add_argument("--json", action="store_true")
    check = sub.add_parser("check", help="Revisar relevos y wikilinks")
    check.add_argument("--json", action="store_true")
    ctx = sub.add_parser("context", help="Preparar contexto con presupuesto explícito")
    ctx.add_argument("--topic", default="")
    ctx.add_argument("--limit", type=int, default=8)
    ctx.add_argument("--max-chars", type=int, default=12000)
    pub = sub.add_parser("release", help="Exportar sólo una lista explícita de archivos revisados")
    pub.add_argument("--allowlist", type=Path, required=True)
    pub.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if not root.is_dir():
        parser.error("La carpeta raíz no existe")
    try:
        if args.command == "note":
            if any("\n" in value or "\r" in value
                   for value in (args.title, args.author, args.topic)):
                parser.error("Título, autor y tema deben ocupar una sola línea")
            print(create_note(root, args.title, args.author, args.topic).relative_to(root))
        elif args.command == "index":
            found = notes(root, args.topic, args.pending)
            data = [{k: v for k, v in asdict(n).items() if k != "text"} for n in found]
            print(json.dumps(data, ensure_ascii=False, indent=2) if args.json else
                  "\n".join(f"[{n.state or 'missing'}] {n.title} — {n.path}" for n in found)
                  or "No matching notes. This does not prove that no work is pending.")
        elif args.command == "check":
            found = issues(root)
            print(json.dumps(found, ensure_ascii=False, indent=2) if args.json else
                  "\n".join(f"{i['path']}:{i['line']}: {i['kind']} {i.get('target', '')}"
                            for i in found) or "OK")
            return bool(found)
        elif args.command == "release":
            print(json.dumps(release(root, args.allowlist, args.output), ensure_ascii=False, indent=2))
        else:
            if args.limit < 0 or args.max_chars < 512:
                parser.error("Usá --limit >= 0 y --max-chars >= 512")
            print(context(root, args.topic, args.limit, args.max_chars))
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
