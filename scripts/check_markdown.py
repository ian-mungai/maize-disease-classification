"""Markdown syntax check: run the pinned markdownlint-cli2 over the repository's Markdown documents.

Run from the repository root: ``.venv/bin/python scripts/check_markdown.py``. The pre-commit hook and ``npm run ci`` run
it. Scope: tracked and untracked non-ignored ``*.md`` files outside ``artifacts/`` (generated E2E reports). Settings come
from ``.markdownlint-cli2.jsonc`` beside this script's repository root. A missing checker is a failure, never a pass;
install it with ``python3 scripts/install_markdownlint.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

from process import run_command

ROOT = Path(__file__).resolve().parent.parent
BINARY = ROOT / ".tools" / "markdownlint-cli2" / "node_modules" / ".bin" / "markdownlint-cli2"
CONFIG = ROOT / ".markdownlint-cli2.jsonc"
SKIPPED_PREFIXES = ("artifacts/", "node_modules/", "web-app/vendor/")


def main() -> int:
    """Lint every eligible Markdown file and pass the checker's exit code through."""
    listing = run_command("git", ["ls-files", "--cached", "--others", "--exclude-standard"], timeout=120, check=True).stdout
    paths = sorted({p for p in listing.splitlines() if p.endswith(".md") and not p.startswith(SKIPPED_PREFIXES) and Path(p).is_file()})
    if not paths:
        sys.stdout.write("markdown check: no Markdown files\n")
        return 0
    if not BINARY.is_file():
        sys.stderr.write("markdown check: markdownlint-cli2 is not installed; run python3 scripts/install_markdownlint.py\n")
        return 1
    result = run_command(str(BINARY), ["--config", str(CONFIG), *paths], timeout=120)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
