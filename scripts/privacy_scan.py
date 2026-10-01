"""Privacy scan: whole project files, not the diff, for personal data and environment-specific values.

Run from the repository root: ``python3 scripts/privacy_scan.py [--all] [--warn]``. The pre-commit hook and ``npm run ci``
run it without flags. Each finding names the file, line and finding type, never the value, and any finding exits 1.
Files that cannot be read as text are listed as unreviewed: inspect them by eye before publishing. Exceptions live in
``.privacy_allowlist`` as ``<type> <path glob> -- <reason>``; entries match by type and path, never by value.
Patterns are assembled from fragments so this file does not flag itself. Needs Python 3.10 or later.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

RULE = "no personal data or environment-specific values in project files (README, Commands)"
FIX = (
    "replace the value with a placeholder (~, $TMPDIR, <name>, example.invalid) or read it from configuration;"
    " if it is meant to be public, add a reasoned entry to .privacy_allowlist"
)
ASK = "if the rule seems wrong here, stop and ask the repository owner; there are no bypasses"
ALLOWLIST = ".privacy_allowlist"
PATTERNS = {
    "home-path": ("home-directory path with a user name", re.compile(r"/(?:" + "Us" + r"ers|home)/(?![<$])(?!Shared/)[A-Za-z0-9._-]+")),
    "temp-path": ("machine temporary path", re.compile(r"/var/" + r"folders/[A-Za-z0-9_+-]+/[A-Za-z0-9_+-]+")),
    "email": ("email address", re.compile(r"\b[A-Za-z0-9._%+-]+@((?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,})\b")),
    "phone": (
        "phone number",
        re.compile(
            r"(?<![\w.])(?:\+\d{1,3}[ .-]?)?(?:\(\d{3}\)[ .-]?|\d{3}[ .-])\d{3}[ .-]\d{4}(?![\w.])|(?<![\w.])\+\d{1,3}[ -]\d{2,4}[ -]\d{3}[ -]\d{3,4}(?![\w.])"
        ),
    ),
    "aws-account": ("AWS account ID", re.compile(r"arn:aws[a-z-]*:[a-z0-9-]*:[a-z0-9-]*:\d{12}:|(?i:account[_ -]?id)\W{1,4}\d{12}\b")),
}
RESERVED_DOMAINS = (".invalid", ".test", ".localhost", ".example", "example.com", "example.org", "example.net")
ENV_VALUE_KEYS = re.compile(r"PROFILE|BUCKET|ACCOUNT|ARN|ENDPOINT|HOST|EMAIL|USER")
SKIPPED_DIRS = {".git", ".next", "node_modules", "__pycache__", ".ruff_cache"}


def git(*args: str) -> str:
    """Run Git with a fixed argument list (no shell) and return its output; a Git failure stops the scan."""
    program = shutil.which("git")
    if program is None:
        raise SystemExit("privacy scan: git not found on PATH")
    return subprocess.run([program, *args], check=True, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=120).stdout  # noqa: S603 - fixed arguments, no shell


def project_files(everything: bool) -> list[str]:
    """Tracked and untracked non-ignored files; with ``everything``, ignored and hidden files too (not tool folders)."""
    if not everything:
        return sorted(set(git("ls-files", "--cached", "--others", "--exclude-standard").splitlines()))
    found = []
    for folder, subfolders, names in os.walk("."):
        subfolders[:] = sorted(name for name in subfolders if name not in SKIPPED_DIRS and not os.path.islink(os.path.join(folder, name)))
        found += [os.path.normpath(os.path.join(folder, name)) for name in names]
    return sorted(found)


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
        if not match or match.group(1) not in {*PATTERNS, "env-value"}:
            problems.append(f"{ALLOWLIST}:{number}: allowlist entry with an unknown type (use one of: {', '.join([*PATTERNS, 'env-value'])})")
        elif not (match.group(3) or "").strip():
            problems.append(f"{ALLOWLIST}:{number}: allowlist entry without a reason (add ' -- <why this value is intentionally public>')")
        else:
            entries.append((match.group(1), match.group(2)))
    return entries, problems


def env_values() -> list[str]:
    """Values of identifying keys in the project's .env (profile, bucket, account, host), never printed."""
    if not Path(".env").is_file():
        return []
    values = []
    for line in Path(".env").read_text().splitlines():
        key, _, value = line.partition("=")
        value = value.strip().strip("\"'")
        if ENV_VALUE_KEYS.search(key.strip().upper()) and len(value) >= 4 and not line.lstrip().startswith("#"):
            values.append(value)
    return values


def line_kinds(line: str, values: list[str]) -> list[str]:
    """Return the finding types on one line."""
    kinds = []
    for kind, (_, pattern) in PATTERNS.items():
        for match in pattern.finditer(line):
            if kind == "email" and match.group(1).lower().endswith(RESERVED_DOMAINS):
                continue
            kinds.append(kind)
            break
    if any(value in line for value in values):
        kinds.append("env-value")
    return kinds


def scan(everything: bool) -> tuple[list[str], list[str]]:
    """Return findings (location and type, never the value) and the files that could not be read as text."""
    allowed, findings = allowlist()
    values = env_values()
    descriptions = {kind: description for kind, (description, _) in PATTERNS.items()} | {"env-value": "value declared in .env"}
    unreviewed = []
    for path in project_files(everything):
        if path == ".env" or os.path.islink(path) or not os.path.isfile(path):
            continue
        data = Path(path).read_bytes()
        try:
            if b"\0" in data[:8192]:
                raise UnicodeDecodeError("utf-8", data[:1], 0, 1, "binary")
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            unreviewed.append(f"{path}: unreviewed: cannot be read as text; inspect it before publishing")
            continue
        for number, line in enumerate(text.splitlines(), 1):
            for kind in line_kinds(line, values):
                if not any(kind == entry_kind and fnmatch.fnmatch(path, glob) for entry_kind, glob in allowed):
                    findings.append(f"{path}:{number}: {descriptions[kind]}")
    return findings, unreviewed


def main() -> int:
    """Scan the project and report; exit 1 on any finding unless ``--warn``."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--all", action="store_true", help="include ignored and hidden files (before publishing)")
    parser.add_argument("--warn", action="store_true", help="report findings without failing")
    args = parser.parse_args()
    findings, unreviewed = scan(args.all)
    for line in unreviewed:
        sys.stderr.write(f"{line}\n")
    for finding in findings:
        sys.stderr.write(f"{'WARN ' if args.warn else ''}{finding}\n  rule: {RULE}\n  fix: {FIX}\n  {ASK}\n")
    if findings and not args.warn:
        return 1
    sys.stdout.write(f"privacy scan: {len(findings)} findings, {len(unreviewed)} files not readable as text\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
