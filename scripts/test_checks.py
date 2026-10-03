"""Scenario runner for the document checks: every bad sample must fail for its intended cause, every good sample must pass.

Run from the repository root: ``.venv/bin/python scripts/test_checks.py``. The pre-commit hook and ``npm run check:source``
run it. Each scenario builds a throwaway Git repository in a temporary folder, writes its files there and runs the real
check command against it; nothing in this repository is touched and no checker internals are imported.

Failure modes these scenarios guard against, written before the checks:

1. A time-bound word in prose passes, or the same word inside code, a URL or front matter is flagged.
2. "as soon as" is flagged as the time word "soon".
3. A check passes because it never ran: a missing checker or a crash must count as a failure, not a pass.
4. The runner inherits the hook's Git index variables and checks this repository instead of the scratch one.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

from process import clear_git_environment, find_program, run_command

SCRIPTS = Path(__file__).resolve().parent
WRITING = [str(SCRIPTS / "writing_check.py")]

# (name, command, files, expected exit code, text every finding must contain, or None for a clean pass)
SCENARIOS: list[tuple[str, list[str], dict[str, str], int, str | None]] = [
    ("time-bound word in prose fails", WRITING, {"a.md": "The service currently loads the model once.\n"}, 1, "a.md:1: time-word"),
    ("'for now' in prose fails", WRITING, {"a.md": "The app runs locally for now.\n"}, 1, "a.md:1: time-word"),
    ("'soon' in prose fails", WRITING, {"a.md": "A new release ships soon.\n"}, 1, "a.md:1: time-word"),
    ("'as soon as' passes", WRITING, {"a.md": "Stop the service as soon as the run ends.\n"}, 0, None),
    ("time word in code passes", WRITING, {"a.md": "Run `currently` and see https://example.com/recently.\n"}, 0, None),
    ("front matter values are ignored", WRITING, {"a.md": "---\ntitle: Currently\nlast_updated: 2026-10-03\n---\n# Plain Text\n"}, 0, None),
    ("existing ISO date rule still fails", WRITING, {"a.md": "Released on 2026-10-03 after review.\n"}, 1, "a.md:1: iso-date"),
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
        findings = [line for line in output.splitlines() if line and not line.startswith(" ") and ":" in line.split(" ")[0]]
        matched = bool(findings) and all(expected_text in line for line in findings) if expected_text else True
        ok = code == expected_code and matched
        failures += not ok
        sys.stdout.write(f"{'PASS' if ok else 'FAIL'} {name}: exit {code}; {' | '.join(findings) or 'no findings'}\n")
    sys.stdout.write(f"{len(SCENARIOS) - failures}/{len(SCENARIOS)} scenarios pass\n")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
