"""Scenario runner for the document checks: every bad sample must fail for its intended cause, every good sample must pass.

Run from the repository root: ``.venv/bin/python scripts/test_checks.py``. The pre-commit hook and ``npm run check:source``
run it. Each scenario builds a throwaway Git repository in a temporary folder, writes its files there and runs the real
check command against it; nothing in this repository is touched and no checker internals are imported.

Failure modes these scenarios guard against, written before the checks:

1. A time-bound word in prose passes, or the same word inside code, a URL or front matter is flagged.
2. "as soon as" is flagged as the time word "soon".
3. A check passes because it never ran: a missing checker or a crash must count as a failure, not a pass.
4. The runner inherits the hook's Git index variables and checks this repository instead of the scratch one.
5. Front matter that is missing, unclosed or not valid YAML passes; a title that differs from the H1, an empty or
   over-long description or an impossible date passes; a heading inside a code fence is taken as the H1.
6. READMEs, well-known files or E2E artifacts are wrongly required to carry front matter.
7. Markdown with star bullets, a fence without a language or duplicate sibling headings passes; repeated subheadings
   under different parents or an E2E report are flagged; the scratch repository's config replaces the project's.
"""

from __future__ import annotations

import re
import shutil
import sys
import tempfile
from pathlib import Path

from process import clear_git_environment, find_program, run_command

SCRIPTS = Path(__file__).resolve().parent
WRITING = [str(SCRIPTS / "writing_check.py")]
FRONT_MATTER = [str(SCRIPTS / "front_matter_check.py")]
MARKDOWN = [str(SCRIPTS / "check_markdown.py")]
FINDING = re.compile(r"^\S+:\d+")  # A finding starts with path:line; summary lines do not.
VALID = "---\ntitle: Sample\ndescription: A valid document.\nlast_updated: 2026-10-03\n---\n# Sample\n"

# (name, command, files, expected exit code, text every finding must contain, or None for a clean pass)
SCENARIOS: list[tuple[str, list[str], dict[str, str], int, str | None]] = [
    ("time-bound word in prose fails", WRITING, {"a.md": "The service currently loads the model once.\n"}, 1, "a.md:1: time-word"),
    ("'for now' in prose fails", WRITING, {"a.md": "The app runs locally for now.\n"}, 1, "a.md:1: time-word"),
    ("'soon' in prose fails", WRITING, {"a.md": "A new release ships soon.\n"}, 1, "a.md:1: time-word"),
    ("'as soon as' passes", WRITING, {"a.md": "Stop the service as soon as the run ends.\n"}, 0, None),
    ("time word in code passes", WRITING, {"a.md": "Run `currently` and see https://example.com/recently.\n"}, 0, None),
    ("front matter values are ignored", WRITING, {"a.md": "---\ntitle: Currently\nlast_updated: 2026-10-03\n---\n# Plain Text\n"}, 0, None),
    ("existing ISO date rule still fails", WRITING, {"a.md": "Released on 2026-10-03 after review.\n"}, 1, "a.md:1: iso-date"),
    ("valid front matter passes", FRONT_MATTER, {"docs/a.md": VALID}, 0, None),
    ("missing front matter fails", FRONT_MATTER, {"docs/a.md": "# Sample\n"}, 1, "no front matter"),
    ("unclosed front matter fails", FRONT_MATTER, {"docs/a.md": "---\ntitle: Sample\n# Sample\n"}, 1, "not closed"),
    ("malformed YAML fails", FRONT_MATTER, {"docs/a.md": VALID.replace("title: Sample", "title: [")}, 1, "not valid YAML"),
    ("title unlike the H1 fails", FRONT_MATTER, {"docs/a.md": VALID.replace("title: Sample", "title: Other")}, 1, "title does not match"),
    ("empty description fails", FRONT_MATTER, {"docs/a.md": VALID.replace("A valid document.", "")}, 1, "description is missing"),
    ("121-character description fails", FRONT_MATTER, {"docs/a.md": VALID.replace("A valid document.", "a" * 121)}, 1, "description over 120"),
    ("impossible date fails", FRONT_MATTER, {"docs/a.md": VALID.replace("2026-10-03", '"2026-02-31"')}, 1, "last_updated is not"),
    ("non-ISO date fails", FRONT_MATTER, {"docs/a.md": VALID.replace("2026-10-03", "Oct 3 2026")}, 1, "last_updated is not"),
    ("heading in a code fence is not the H1", FRONT_MATTER, {"docs/a.md": VALID.replace("# Sample", "```python\n# Sample\n```\n")}, 1, "title does not match"),
    (
        "README, well-known files and E2E reports are exempt",
        FRONT_MATTER,
        {"README.md": "# A\n", "web-app/README.md": "# B\n", "CHANGELOG.md": "# C\n", "artifacts/e2e/r/report.md": "# D\n"},
        0,
        None,
    ),
    ("clean Markdown passes", MARKDOWN, {"a.md": "# Title\n\n- Item\n\n```bash\nls\n```\n"}, 0, None),
    ("star bullet fails", MARKDOWN, {"a.md": "# Title\n\n* Item\n"}, 1, "a.md:3"),
    ("fence without a language fails", MARKDOWN, {"a.md": "# Title\n\n```\nls\n```\n"}, 1, "a.md:3"),
    ("duplicate sibling headings fail", MARKDOWN, {"a.md": "# Title\n\n## Part\n\n## Part\n"}, 1, "a.md:5"),
    ("repeated subheadings under different parents pass", MARKDOWN, {"a.md": "# Title\n\n## One\n\n### Added\n\n## Two\n\n### Added\n"}, 0, None),
    ("E2E reports are not linted", MARKDOWN, {"artifacts/e2e/r/report.md": "* Item\n"}, 0, None),
]


def run(command: list[str], files: dict[str, str]) -> tuple[int, str]:
    """Write the files into a fresh Git repository, run the command there and return its exit code and output."""
    folder = Path(tempfile.mkdtemp(prefix="doc_checks_"))
    try:
        if find_program("git") is None:
            return 99, "cannot run: git not found"
        run_command("git", ["init", "-q", str(folder)], timeout=60, check=True)
        for name, text in files.items():
            path = folder / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        result = run_command(sys.executable, command, cwd=folder, timeout=120)
        return result.returncode, result.stdout + result.stderr
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def main() -> int:
    """Run every scenario and report pass or fail with the observed findings."""
    clear_git_environment()
    failures = 0
    for name, command, files, expected_code, expected_text in SCENARIOS:
        code, output = run(command, files)
        findings = [line for line in output.splitlines() if FINDING.match(line)]
        matched = bool(findings) and all(expected_text in line for line in findings) if expected_text else True
        ok = code == expected_code and matched
        failures += not ok
        sys.stdout.write(f"{'PASS' if ok else 'FAIL'} {name}: exit {code}; {' | '.join(findings) or 'no findings'}\n")
    sys.stdout.write(f"{len(SCENARIOS) - failures}/{len(SCENARIOS)} scenarios pass\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
