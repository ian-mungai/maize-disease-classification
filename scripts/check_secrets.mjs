/** Scan the complete working tree with the verified pinned secret scanner. */
import { spawnSync } from "node:child_process";
const scanner = process.env.GITLEAKS_BIN || "gitleaks";
const version = spawnSync(scanner, ["version"], { encoding: "utf8" });
if (version.status !== 0 || version.stdout.trim() !== "8.30.1") {
    process.stderr.write("gitleaks 8.30.1 is required for the local secret check.\n");
    process.exitCode = 1;
} else {
    const result = spawnSync(scanner, ["dir", "--redact", "--no-banner", "."], { stdio: "inherit" });
    process.exitCode = result.status === 0 ? 0 : 1;
}
