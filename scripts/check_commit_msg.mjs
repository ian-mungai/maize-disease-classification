#!/usr/bin/env node
/**
 * Commit-message policy: Conventional Commit subjects and no AI attribution.
 *
 * Usage: node scripts/check_commit_msg.mjs <message-file>   (commit-msg hook)
 *        node scripts/check_commit_msg.mjs --range <a..b>   (local CI; checks stored messages)
 *
 * Human co-authors and factual mentions of tools stay allowed. Findings name the line, never echo the message.
 */
import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";

const TYPES = ["feat", "fix", "docs", "chore", "refactor", "test", "build", "ci", "perf", "style", "revert"];
const SUBJECT = new RegExp(`^(?:${TYPES.join("|")})(?:\\([a-z0-9._/-]+\\))?!?: \\S.*$`);
const AGENTS = ["claude", "codex", "grok", "antigravity", "chatgpt", "copilot", "gemini", "cursor", "devin", "aider", "windsurf"];
const AI_NAMES = new RegExp(`\\b(?:${[...AGENTS, "anthropic", "openai", "xai"].join("|")})\\b`, "i");
const CREDIT = /^\s*(?:co-authored-by|co-developed-by|assisted-by|generated-by)\s*:\s*(.*)$/i;
const GENERATED = /^\s*(?:[🤖✨]\s*)?(?:generated (?:with|by)|written by)\b(.*)$/iu;
const SESSION = new RegExp(`^\\s*(?:${AGENTS.join("|")})-session\\s*:`, "i");

/** Drop Git comment lines and everything below the verbose-commit scissors line. */
function stripComments(message) {
  const lines = [];
  for (const line of message.split("\n")) {
    if (/^# -+ >8 -+$/.test(line)) break;
    if (!line.startsWith("#")) lines.push(line);
  }
  return lines;
}

function findings(where, message, { comments }) {
  const lines = comments ? stripComments(message) : message.split("\n");
  const problems = [];
  const subject = lines.find((line) => line.trim() !== "") ?? "";
  if (!SUBJECT.test(subject)) problems.push(`${where}: subject is not a Conventional Commit (<type>(<scope>): <description>)`);
  lines.forEach((line, index) => {
    const credit = CREDIT.exec(line) ?? GENERATED.exec(line);
    if (SESSION.test(line) || (credit && AI_NAMES.test(credit[1]))) {
      problems.push(`${where}:${index + 1}: AI attribution; remove the AI credit or session line (human co-authors are fine)`);
    }
  });
  return problems;
}

const args = process.argv.slice(2);
let problems;
if (args[0] === "--range") {
  if (!args[1]) throw new Error("--range needs <a..b>");
  const revisions = execFileSync("git", ["rev-list", "--reverse", args[1]], { encoding: "utf8" }).split("\n").filter(Boolean);
  problems = revisions.flatMap((rev) => findings(rev.slice(0, 7), execFileSync("git", ["log", "-1", "--format=%B", rev], { encoding: "utf8" }), { comments: false }));
} else if (args.length === 1) {
  problems = findings("commit message", readFileSync(args[0], "utf8"), { comments: true });
} else {
  throw new Error("usage: check_commit_msg.mjs <message-file> | --range <a..b>");
}
for (const problem of problems) process.stderr.write(`${problem}\n`);
process.exit(problems.length ? 1 : 0);
