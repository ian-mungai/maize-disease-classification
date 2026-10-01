/** Verify the historical source without importing or running its application code. */
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const manifest = JSON.parse(readFileSync(join(root, "docs/source_manifest.json"), "utf8"));
const assertions = [];
const record = (scenario, pass, observed) => assertions.push({ scenario, status: pass ? "pass" : "fail", observed });
const digest = (data) => createHash("sha256").update(data).digest("hex");

for (const file of manifest.files) {
    const target = join(root, file.path);
    if (file.treatment === "excluded_local_noise") {
        record(`excluded ${file.path}`, !existsSync(target), "file must be absent");
    } else if (file.treatment === "preserved") {
        const matches = existsSync(target) && digest(readFileSync(target)) === file.sha256;
        record(`preserved ${file.path}`, matches, matches ? file.sha256 : "file missing or changed");
    }
}

function inspect(directory) {
    for (const entry of readdirSync(directory, { withFileTypes: true })) {
        if ([".git", ".agent_handoff", ".enjoy-logs", ".venv", ".tools"].includes(entry.name)) continue;
        if (directory === root && entry.isDirectory() && [".mypy_cache", ".ruff_cache"].includes(entry.name)) continue;
        const path = join(directory, entry.name);
        if (entry.isSymbolicLink()) {
            record("no outgoing symlink", false, path.slice(root.length + 1));
        } else if (entry.isDirectory()) {
            if (["node_modules", "vendor", "__pycache__"].includes(entry.name)) record("no generated dependency directory", false, entry.name);
            else inspect(path);
        } else if (/\.sql$|\.sqlite$|\.db$|\.pem$|\.key$|\.pyc$|\.log$|^\.DS_Store$|^\.env$/.test(entry.name)) {
            record("no private or generated file", false, path.slice(root.length + 1));
        }
    }
}
inspect(root);

const notebook = JSON.parse(readFileSync(join(root, "Maize_Diseases_Detection_Model.ipynb"), "utf8"));
record("notebook remains parseable", notebook.nbformat === 4 && notebook.cells.length === 19, "nbformat 4, 19 cells expected");
const models = manifest.files.filter((file) => file.path.startsWith("flask-app/model/"));
record("four original model files retained", models.length === 4 && models.every((file) => file.treatment === "preserved"), String(models.length));
const report = {
    source_commit: manifest.source_commit,
    assertions,
    failed: assertions.filter((item) => item.status === "fail").length,
    boundary: "Source-preservation verification only. Separate model-format review does not establish application execution, inference behavior, retraining, fresh accuracy or image redistribution rights.",
    reproduction: "node scripts/verify_archive.mjs",
};
const reportPath = join(root, "artifacts/e2e/archive_review/report.json");
mkdirSync(dirname(reportPath), { recursive: true });
writeFileSync(reportPath, JSON.stringify(report, null, 2) + "\n");
process.stdout.write(`Archive assertions: ${assertions.length - report.failed}/${assertions.length} passed\n`);
process.exitCode = report.failed ? 1 : 0;
