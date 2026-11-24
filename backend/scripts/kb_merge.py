"""Merge knowledge-base source files into one reviewable knowledge_base.md.

    python scripts/kb_merge.py <source_dir> [-o knowledge_base.md]

Reads every .md and .txt under <source_dir> (recursively, in name order). Each
file is split into paragraphs and these are dropped:
- exact or near-exact duplicates (same text after case, punctuation and
  whitespace are folded), wherever they appear;
- paragraphs that are not actionable material: blank, very short (< 40 chars),
  only links, tables of contents, page numbers, share or subscribe lines.
Headings are kept so the structure stays readable. Every kept block is
preceded by an HTML comment naming its source file, so a reviewer can trace it.
Nothing is rewritten or summarised: the output contains only text that was in
the sources. A summary of what was dropped is printed and written at the end
of the file. The admin reviews the file before uploading it in the admin page.
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path
from typing import Dict, List, Tuple

MIN_CHARS = 40
NOISE = re.compile(
    r"^(table of contents|contents|المحتويات|فهرس|page \d+|صفحة \d+|share|subscribe|follow us|click here|"
    r"اشترك|تابعنا|شارك)\b", re.IGNORECASE,
)
LINK_ONLY = re.compile(r"^(\s*[-*]?\s*(\[[^\]]*\]\([^)]*\)|https?://\S+)\s*)+$")


def fold(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    text = re.sub(r"[ً-ْـ]", "", text)  # tashkeel, tatweel
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def prepare(body: str) -> str:
    """Turn a YAML front matter block into a heading, a summary line, tags and sources.

    Only fields that help search and trust are kept (title, summary, tags,
    sources). slug, level and updated are dropped. Text without front matter is
    returned unchanged. Nothing in the article body is touched.
    """
    body = body.replace("\r\n", "\n")
    if not body.startswith("---\n"):
        return body
    end = body.find("\n---", 4)
    if end == -1:
        return body
    head, rest = body[4:end], body[end + 4:].lstrip("\n")
    meta: Dict[str, str] = {}
    sources: List[str] = []
    key = ""
    for line in head.splitlines():
        match = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if match:
            key = match.group(1)
            meta[key] = match.group(2).strip().strip('"')
        elif key == "sources" and line.strip().startswith("- "):
            sources.append(line.strip()[2:].strip().strip('"'))
    title = meta.get("title", "").strip()
    parts = [meta.get("summary", "").strip()]
    tags = meta.get("tags", "").strip("[]")
    if tags:
        parts.append("Tags: " + ", ".join(t.strip() for t in tags.split(",") if t.strip()))
    if sources:
        parts.append("Sources: " + "; ".join(sources))
    intro = "\n".join(p for p in parts if p)
    heading = f"## {title}\n\n" if title and not rest.lstrip().startswith("# ") else ""
    if intro and not heading and rest.lstrip().startswith("# "):
        # The article has its own title: keep it first, then the summary, then the text.
        first, _, remainder = rest.lstrip().partition("\n")
        return f"{first}\n\n{intro}\n\n{remainder.lstrip()}"
    return f"{heading}{intro}\n\n{rest}" if intro else f"{heading}{rest}"


def paragraphs(body: str) -> List[str]:
    return [p.strip() for p in re.split(r"\n\s*\n", body.replace("\r\n", "\n")) if p.strip()]


def keep_reason(p: str) -> str | None:
    """None when the paragraph is kept, else why it is dropped."""
    if p.startswith("#"):
        return None
    if LINK_ONLY.match(p):
        return "links only"
    if NOISE.match(p.lstrip("#*-• ").strip()):
        return "navigation/boilerplate"
    if len(p) < MIN_CHARS:
        return "too short"
    return None


def merge(files: List[Tuple[str, str]]) -> Tuple[str, Dict[str, int]]:
    seen: set = set()
    dropped: Dict[str, int] = {"duplicate": 0, "links only": 0, "navigation/boilerplate": 0, "too short": 0}
    out: List[str] = ["# Helix knowledge base (merged draft: review before upload)", ""]
    for name, body in files:
        kept: List[str] = []
        for p in paragraphs(prepare(body)):
            reason = keep_reason(p)
            if reason:
                dropped[reason] += 1
                continue
            key = fold(p)
            if not p.startswith("#") and key in seen:
                dropped["duplicate"] += 1
                continue
            seen.add(key)
            kept.append(p)
        if any(not p.startswith("#") for p in kept):
            out.append(f"<!-- source: {name} -->")
            out.extend(sum(([p, ""] for p in kept), []))
    out.append("<!-- merge summary: " + ", ".join(f"{k}: {v}" for k, v in dropped.items()) + " -->")
    return "\n".join(out).rstrip() + "\n", dropped


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("source_dir")
    ap.add_argument("-o", "--output", default="knowledge_base.md")
    ap.add_argument("--split", action="store_true",
                    help="write one file per top-level folder into the --output directory (better citations)")
    args = ap.parse_args(argv)
    root = Path(args.source_dir)
    # README files describe the folder, not the subject: they are skipped.
    files = [(str(p.relative_to(root)), p.read_text(encoding="utf-8", errors="replace"))
             for p in sorted(root.rglob("*"))
             if p.is_file() and p.suffix.lower() in (".md", ".txt") and p.name.lower() != "readme.md"]
    if not files:
        print("No .md or .txt files found.", file=sys.stderr)
        return 1
    if not args.split:
        text, dropped = merge(files)
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"{len(files)} files -> {args.output} ({len(text)} chars). Dropped: {dropped}")
        return 0
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    groups: Dict[str, List[Tuple[str, str]]] = {}
    for name, body in files:
        parts = Path(name).parts
        groups.setdefault(parts[-2] if len(parts) > 1 else "general", []).append((name, body))
    for group, items in groups.items():
        text, dropped = merge(items)
        target = out_dir / f"{group}.md"
        target.write_text(text, encoding="utf-8")
        print(f"{group}: {len(items)} files -> {target.name} ({len(text)} chars). Dropped: {dropped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
