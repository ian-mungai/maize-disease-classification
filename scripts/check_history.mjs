/** Validate stored commit messages; the initial message is enforced by the commit-msg hook. */
import { execFileSync, spawnSync } from "node:child_process";
const head = spawnSync("git", ["rev-parse", "--verify", "HEAD"], { stdio: "ignore" });
const inside = spawnSync("git", ["rev-parse", "--is-inside-work-tree"], { encoding: "utf8" });
const branch = spawnSync("git", ["symbolic-ref", "--quiet", "HEAD"], { encoding: "utf8" });
const unborn = inside.status === 0 && inside.stdout.trim() === "true" && branch.status === 0 &&
    branch.stdout.trim().startsWith("refs/heads/") &&
    spawnSync("git", ["show-ref", "--verify", "--quiet", branch.stdout.trim()], { stdio: "ignore" }).status === 1;
if (head.status === 0) {
    execFileSync(process.execPath, ["scripts/check_commit_msg.mjs", "--range", "HEAD"], { stdio: "inherit" });
} else if (unborn) {
    process.stdout.write("No stored commits; the initial message is checked by the commit-msg hook.\n");
} else {
    process.stderr.write("Git checkpoint could not be inspected.\n");
    process.exitCode = 1;
}
