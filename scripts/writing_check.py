"""Writing check: prose in Markdown files and article content follows the owner's writing preferences.

Run from the repository root: ``python3 scripts/writing_check.py``. The pre-commit hook and ``npm run ci`` run it. It flags:

- ``comma-and``: a comma right before a final "and", "or" or "nor", in lists and between clauses (no Oxford comma).
- ``iso-date``: an ISO 8601 date such as 2026-09-30 in prose; write Sep 30 2026 instead. Code and URLs may keep ISO dates.
- ``em-dash``: an em dash in article text (the article style allows few or none).

Scope: tracked and untracked non-ignored ``*.md`` files outside ``artifacts/`` (generated E2E reports), plus the reader-facing
strings of article files under ``content/articles/`` (any file that declares an ``Article``). Code spans, fenced code blocks,
URLs and link targets are ignored. Exceptions live in ``.writing_allowlist`` as ``<type> <path glob> -- <reason>``; an entry
without a reason is itself a finding. Spelling and Title Case are not checked here: they stay a reviewer's judgment.
"""

from __future__ import annotations

import fnmatch
import re
import shutil
import subprocess
import sys
from pathlib import Path

ALLOWLIST = ".writing_allowlist"
RULE = "writing preferences: no Oxford comma, dates like Sep 30 2026 in prose, few or no em dashes in articles (README, Commands)"
ASK = "if the rule seems wrong here, stop and ask the repository owner; there are no bypasses"
CHECKS = {
    "comma-and": ("comma before a final 'and', 'or' or 'nor'", re.compile(r",\s+(?:and|or|nor)\b"), "drop the comma, or split the sentence in two"),
    "iso-date": ("ISO date in prose", re.compile(r"\b\d{4}-\d{2}-\d{2}\b"), "write the date as Sep 30 2026, or put a machine value in `code`"),
    "em-dash": ("em dash in article text", re.compile("—"), "use a colon, comma, parentheses or a new sentence"),
}
ARTICLE_ONLY = {"em-dash"}
SKIPPED_PREFIXES = ("artifacts/", "node_modules/", ".next/")
# Reader-facing string values in article files; slug, published and kind are metadata.
ARTICLE_STRING = re.compile(r'"((?:[^"\\\n]|\\.)*)"')
METADATA_KEY = re.compile(r"\b(?:slug|published|kind)\s*:\s*$")


def git_files() -> list[str]:
    """Tracked and untracked non-ignored files, from Git with a fixed argument list."""
    program = shutil.which("git")
    if program is None:
        raise SystemExit("writing check: git not found on PATH")
    listing = subprocess.run(  # noqa: S603 - fixed arguments, no shell
        [program, "ls-files", "--cached", "--others", "--exclude-standard"], check=True, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=120
    ).stdout
    return sorted(set(listing.splitlines()))


def mask(text: str) -> str:
    """Replace code spans, URLs and link targets with a neutral word so only prose is checked; line numbers stay intact.

    A neutral word, not blanks: blanking would turn "`a`, `b` and `c`" into a comma followed by spaces and "and".
    """
    text = re.sub(r"`[^`\n]*`", "code", text)
    text = re.sub(r"\]\([^)\s]*\)", "]", text)
    return re.sub(r"https?://\S+", "url", text)


def markdown_lines(text: str) -> list[tuple[int, str]]:
    """Prose lines of a Markdown file, outside fenced code blocks."""
    lines, fenced = [], False
    for number, line in enumerate(text.splitlines(), 1):
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
            continue
        if not fenced:
            lines.append((number, mask(line)))
    return lines


def article_lines(text: str) -> list[tuple[int, str]]:
    """Reader-facing string literals of an article file, one entry per string with its line number."""
    lines = []
    for number, line in enumerate(text.splitlines(), 1):
        for match in ARTICLE_STRING.finditer(line):
            if not METADATA_KEY.search(line[: match.start()]):
                lines.append((number, mask(match.group(1))))
    return lines


def allowlist() -> tuple[list[tuple[str, str]], list[str]]:
    """Read ``type glob -- reason`` entries; an entry without a reason or with an unknown type is itself a finding."""
    entries: list[tuple[str, str]] = []
    problems: list[str] = []
    if not Path(ALLOWLIST).exists():
        return entries, problems
    for number, line in enumerate(Path(ALLOWLIST).read_text().splitlines(), 1):
        text = "" if line.lstrip().startswith("#") else line.strip()
        if not text:
            continue
        match = re.fullmatch(r"(\S+)\s+(\S+)(?:\s+--\s*(.*))?", text)
        if not match or match.group(1) not in CHECKS:
            problems.append(f"{ALLOWLIST}:{number}: allowlist entry with an unknown type (use one of: {', '.join(CHECKS)})")
        elif not (match.group(3) or "").strip():
            problems.append(f"{ALLOWLIST}:{number}: allowlist entry without a reason (add ' -- <why this text is kept as is>')")
        else:
            entries.append((match.group(1), match.group(2)))
    return entries, problems


def scan() -> list[str]:
    """Return one finding per rule broken per line: file, line, type and description, then the fix."""
    allowed, findings = allowlist()
    for path in git_files():
        if path.startswith(SKIPPED_PREFIXES) or not Path(path).is_file():
            continue
        if path.endswith(".md"):
            lines, article = markdown_lines(Path(path).read_text(errors="replace")), False
        elif path.startswith("content/articles/") and path.endswith(".ts"):
            text = Path(path).read_text(errors="replace")
            if not re.search(r":\s*Article\s*=", text):
                continue
            lines, article = article_lines(text), True
        else:
            continue
        for number, line in lines:
            for kind, (description, pattern, fix) in CHECKS.items():
                if kind in ARTICLE_ONLY and not article:
                    continue
                if pattern.search(line) and not any(kind == entry_kind and fnmatch.fnmatch(path, glob) for entry_kind, glob in allowed):
                    findings.append(f"{path}:{number}: {kind}: {description}\n  fix: {fix}")
    return findings


def main() -> int:
    """Report findings and exit 1 when there are any."""
    findings = scan()
    for finding in findings:
        sys.stderr.write(f"{finding}\n  rule: {RULE}\n  {ASK}\n")
    sys.stdout.write(f"writing check: {len(findings)} findings\n")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
