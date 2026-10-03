"""Front matter check: every project document carries valid YAML metadata whose title matches its H1.

Run from the repository root: ``.venv/bin/python scripts/front_matter_check.py``. The pre-commit hook and ``npm run ci``
run it. Scope: tracked and untracked non-ignored ``*.md`` files, except READMEs, well-known files (such as CHANGELOG.md)
and generated reports under ``artifacts/``. Each document starts with ``---`` front matter that parses as YAML and holds
``title`` equal to the first H1, a ``description`` of at most 120 characters and ``last_updated`` as ``YYYY-MM-DD``.
"""

from __future__ import annotations

import importlib
import re
import sys
from datetime import date
from pathlib import Path

from process import run_command

RULE = "document metadata: YAML front matter with title equal to the H1, description of at most 120 characters, last_updated as YYYY-MM-DD"
ASK = "if the rule seems wrong here, stop and ask the repository owner; there are no bypasses"
WELL_KNOWN = {"AGENTS.md", "CLAUDE.md", "CONTRIBUTING.md", "CHANGELOG.md", "SECURITY.md", "CODE_OF_CONDUCT.md", "SUPPORT.md", "LICENSE.md"}
SKIPPED_PREFIXES = ("artifacts/", "node_modules/", "web-app/vendor/")
DESCRIPTION_LIMIT = 120
ISO_DAY = re.compile(r"\d{4}-\d{2}-\d{2}")


def load_yaml(text: str) -> object:
    """Parse YAML with PyYAML's safe loader; PyYAML ships no type hints, so it is imported by name."""
    yaml = importlib.import_module("yaml")
    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise ValueError("YAML parsing failed") from error


def first_h1(text: str) -> str | None:
    """The first level-one heading outside code fences; shorter inner markers do not close a fence."""
    fence: tuple[str, int] | None = None
    for line in text.splitlines():
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if marker:
            token, rest = marker.groups()
            if fence is None:
                fence = (token[0], len(token))
            elif token[0] == fence[0] and len(token) >= fence[1] and not rest.strip():
                fence = None
            continue
        if fence is None and line.startswith("# "):
            return line[2:].strip()
    return None


def valid_day(value: object) -> bool:
    """Whether a YAML value is a real calendar date written as YYYY-MM-DD."""
    if type(value) is date:
        return True
    if not isinstance(value, str) or not ISO_DAY.fullmatch(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def problems(text: str) -> list[str]:
    """Metadata problems of one document, empty when it is valid."""
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return ["no front matter: start the file with --- title, description and last_updated ---"]
    end = next((number for number, line in enumerate(lines[1:], 1) if line.strip() == "---"), None)
    if end is None:
        return ["front matter is not closed with a --- line"]
    try:
        data = load_yaml("\n".join(lines[1:end]))
    except ValueError as error:
        return [f"front matter is not valid YAML ({error}); quote values that contain ': '"]
    if not isinstance(data, dict):
        return ["front matter is not valid YAML: expected key: value lines"]
    found = []
    title, description = data.get("title"), data.get("description")
    if not isinstance(title, str) or title != first_h1("\n".join(lines[end + 1 :])):
        found.append("title does not match the H1")
    if not isinstance(description, str) or not description.strip():
        found.append("description is missing")
    elif len(description) > DESCRIPTION_LIMIT:
        found.append(f"description over {DESCRIPTION_LIMIT} characters ({len(description)})")
    if not valid_day(data.get("last_updated")):
        found.append("last_updated is not a YYYY-MM-DD date")
    return found


def in_scope(path: str) -> bool:
    """Whether a repository path is a document that needs front matter."""
    name = Path(path).name
    return path.endswith(".md") and not path.startswith(SKIPPED_PREFIXES) and name not in WELL_KNOWN and not name.startswith("README") and Path(path).is_file()


def main() -> int:
    """Report one finding per problem and exit 1 when there are any."""
    listing = run_command("git", ["ls-files", "--cached", "--others", "--exclude-standard"], timeout=120, check=True).stdout
    findings = [f"{path}:1: {problem}" for path in sorted(set(listing.splitlines())) if in_scope(path) for problem in problems(Path(path).read_text())]
    for finding in findings:
        sys.stderr.write(f"{finding}\n  fix: correct the YAML title, description and last_updated fields\n  rule: {RULE}\n  {ASK}\n")
    sys.stdout.write(f"front matter check: {len(findings)} findings\n")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
