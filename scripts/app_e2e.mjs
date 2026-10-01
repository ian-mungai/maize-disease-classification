// End-to-end check of the running app: Laravel (web-app) -> Flask (flask-app) -> TensorFlow model -> database.
// Prerequisites: Flask on MAIZE_MODEL_URL's host, Laravel on APP_URL, both on 127.0.0.1; migrations and seeders run.
// Usage: node scripts/app_e2e.mjs [--fixtures artifacts/fixtures/leaf_images] [--synthetic]
// Each run registers two new users with run-scoped emails, so reruns never collide with earlier data.
// Report: artifacts/e2e/app_run_<RUN_ID>/report.json and report.md (local only).

import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, extname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const webApp = join(root, "web-app");
const args = process.argv.slice(2);
const synthetic = args.includes("--synthetic");
const fixturesDir = join(root, args.includes("--fixtures") ? args[args.indexOf("--fixtures") + 1] : "artifacts/fixtures/leaf_images");
const appUrl = process.env.APP_URL ?? "http://127.0.0.1:8000";
const modelUrl = process.env.MAIZE_MODEL_URL ?? "http://127.0.0.1:4040/disease-analyzer";
const classes = ["Blight", "Common Rust", "Gray Leaf Spot", "Healthy"];
const runId = new Date().toISOString().replace(/[-:]/g, "").replace(/\.\d+Z$/, "Z");
const outDir = join(root, "artifacts/e2e", `app_run_${runId}`);
const scenarios = [];
const sha256 = (buf) => createHash("sha256").update(buf).digest("hex");

function record(id, name, expected, observed, pass) {
  scenarios.push({ id, name, expected, observed, status: pass ? "pass" : "fail" });
  console.log(`${pass ? "PASS" : "FAIL"} ${id} ${name}: ${observed}`);
}

function loadFixtures() {
  if (synthetic) {
    // Deterministic 64x64 PNGs, one per class slot; labels are placeholders, not leaf images.
    return classes.map((label, i) => ({ label, file: `synthetic_${i}.png`, bytes: syntheticPng(i), mime: "image/png" }));
  }
  if (!existsSync(join(fixturesDir, "manifest.json"))) throw new Error(`No fixture manifest in ${relative(root, fixturesDir)}; run with --synthetic for a smoke test`);
  const fixtures = [];
  for (const dir of readdirSync(fixturesDir, { withFileTypes: true }).filter((d) => d.isDirectory()).sort((a, b) => a.name.localeCompare(b.name))) {
    for (const file of readdirSync(join(fixturesDir, dir.name)).sort()) {
      const ext = extname(file).toLowerCase();
      if (![".jpg", ".jpeg", ".png"].includes(ext)) continue;
      fixtures.push({ label: dir.name, file: `${dir.name}/${file}`, bytes: readFileSync(join(fixturesDir, dir.name, file)), mime: ext === ".png" ? "image/png" : "image/jpeg" });
    }
  }
  return fixtures;
}

function syntheticPng(seed) {
  const python = join(root, "flask-app/.venv/bin/python");
  const code = `import io,sys,numpy as np;from PIL import Image;b=io.BytesIO();Image.fromarray(np.random.default_rng(${seed}).integers(0,255,(64,64,3),dtype=np.uint8)).save(b,'PNG');sys.stdout.buffer.write(b.getvalue())`;
  return execFileSync(python, ["-c", code]);
}

class Browser {
  constructor() {
    this.cookies = new Map();
  }
  async request(path, { method = "GET", body } = {}) {
    const headers = { Cookie: [...this.cookies].map(([k, v]) => `${k}=${v}`).join("; "), Accept: "text/html" };
    const res = await fetch(new URL(path, appUrl), { method, body, headers, redirect: "manual" });
    for (const c of res.headers.getSetCookie()) {
      const [pair] = c.split(";");
      const i = pair.indexOf("=");
      this.cookies.set(pair.slice(0, i), pair.slice(i + 1));
    }
    return res;
  }
  async token(path) {
    const html = await (await this.request(path)).text();
    const match = html.match(/name="_token" value="([^"]+)"/);
    if (!match) throw new Error(`No CSRF token on ${path}`);
    return match[1];
  }
  async submit(formPath, action, fields, file) {
    const form = new FormData();
    form.set("_token", await this.token(formPath));
    for (const [k, v] of Object.entries(fields)) form.set(k, v);
    if (file) form.set("image", new Blob([file.bytes], { type: file.mime }), file.file.split("/").pop());
    return this.request(action, { method: "POST", body: form });
  }
}

const location = (res) => new URL(res.headers.get("location") ?? "", appUrl).pathname;

async function register(name, email) {
  const browser = new Browser();
  const res = await browser.submit("/register", "/register", { name, email, password: `pw-${runId}-x`, password_confirmation: `pw-${runId}-x` });
  return { browser, res };
}

const fixtures = loadFixtures();
const fixtureRows = fixtures.map((f) => ({ file: f.file, label: f.label, bytes: f.bytes.length, sha256: sha256(f.bytes) }));

// S1 model service classifies every fixture directly.
const direct = [];
for (const f of fixtures) {
  const form = new FormData();
  form.set("image", new Blob([f.bytes], { type: f.mime }), f.file.split("/").pop());
  const res = await fetch(modelUrl, { method: "POST", body: form });
  direct.push({ file: f.file, label: f.label, status: res.status, prediction: (await res.json()).prediction });
}
record("S1", "Flask classifies each fixture", "HTTP 200 and one of the 4 classes", direct.map((d) => `${d.file}=${d.prediction}`).join(", "), direct.every((d) => d.status === 200 && classes.includes(d.prediction)));

// S2 guests are sent to the login page.
const guest = await new Browser().request("/dashboard");
record("S2", "Guest redirected to login", "302 to /login", `${guest.status} to ${location(guest)}`, guest.status === 302 && location(guest) === "/login");

// S3 registration signs the user in.
const userEmail = `e2e-user-${runId}@example.invalid`;
const adminEmail = `e2e-admin-${runId}@example.invalid`;
const otherEmail = `e2e-other-${runId}@example.invalid`;
const user = await register("E2E User", userEmail);
const dash = await user.browser.request("/dashboard");
record("S3", "Register and reach dashboard", "302 to /dashboard, then 200", `${user.res.status} to ${location(user.res)}, dashboard ${dash.status}`, user.res.status === 302 && location(user.res) === "/dashboard" && dash.status === 200);

// S4 only administrators manage recommendations.
const admin = await register("E2E Admin", adminEmail);
execFileSync("php", ["artisan", "app:make-admin", adminEmail], { cwd: webApp });
const adminList = await admin.browser.request("/diseases");
const userList = await user.browser.request("/diseases");
record("S4", "Disease admin is admin-only", "admin 200, user 403", `admin ${adminList.status}, user ${userList.status}`, adminList.status === 200 && userList.status === 403);

// S5 the admin stores one recommendation per class (update when one already exists).
const recommendation = (c) => `E2E placeholder recommendation for ${c} (${runId}); not agronomic advice.`;
const existing = await (await admin.browser.request("/diseases")).text();
const saved = [];
for (const c of classes) {
  const id = [...existing.matchAll(/<td>(\d+)<\/td>\s*<td>([^<]+)<\/td>/g)].find((m) => m[2].trim() === c.replace("&", "&amp;"))?.[1];
  const res = id
    ? await admin.browser.submit(`/diseases/${id}/edit`, `/diseases/${id}`, { _method: "PUT", diseaseName: c, recommendation: recommendation(c) })
    : await admin.browser.submit("/diseases/create", "/diseases", { diseaseName: c, recommendation: recommendation(c) });
  saved.push(`${c}:${res.status}->${location(res)}`);
}
record("S5", "Admin saves a recommendation per class", "4 redirects to /diseases", saved.join(", "), saved.every((s) => s.endsWith("302->/diseases")));

// S6 uploads go through Laravel to the model and show the class and recommendation.
const uploads = [];
for (const [i, f] of fixtures.entries()) {
  const res = await user.browser.submit("/predictions/create", "/predictions", { description: `e2e ${f.file}` }, f);
  const path = location(res);
  const html = await (await user.browser.request(path)).text();
  const shown = html.match(/<span id="prediction">([^<]+)<\/span>/)?.[1];
  const rec = html.match(/<span id="recommendation">([^<]+)<\/span>/)?.[1];
  uploads.push({ file: f.file, label: f.label, status: res.status, path, prediction: shown, recommendationMatches: rec === recommendation(shown), matchesDirect: shown === direct[i].prediction });
}
record(
  "S6",
  "Upload shows prediction and recommendation",
  "302 to /predictions/<id>; class equals the direct Flask result; recommendation matches",
  uploads.map((u) => `${u.file}=${u.prediction}`).join(", "),
  uploads.every((u) => u.status === 302 && /^\/predictions\/\d+$/.test(u.path) && u.matchesDirect && u.recommendationMatches),
);

// S7 uploading the same image again reuses the stored prediction.
const again = await user.browser.submit("/predictions/create", "/predictions", { description: "e2e repeat" }, fixtures[0]);
const rows = ((await (await user.browser.request("/predictions")).text()).match(/<a href="predictions\/\d+"/g) ?? []).length;
const distinct = new Set(fixtureRows.map((f) => f.sha256)).size;
record("S7", "Repeat upload is idempotent", `same URL ${uploads[0].path}; ${distinct} rows`, `${location(again)}; ${rows} rows`, location(again) === uploads[0].path && rows === distinct);

// S8 another user cannot see the prediction or its image.
const other = await register("E2E Other", otherEmail);
const peek = await other.browser.request(uploads[0].path);
const peekImg = await other.browser.request(`${uploads[0].path}/image`);
record("S8", "Other users are refused", "403 and 403", `${peek.status} and ${peekImg.status}`, peek.status === 403 && peekImg.status === 403);

// S9 the owner gets back the exact stored bytes.
const img = await user.browser.request(`${uploads[0].path}/image`);
const imgHash = sha256(Buffer.from(await img.arrayBuffer()));
record("S9", "Owner downloads the stored image", `200 and sha256 ${fixtureRows[0].sha256.slice(0, 12)}`, `${img.status} and sha256 ${imgHash.slice(0, 12)}`, img.status === 200 && imgHash === fixtureRows[0].sha256);

// S10 Laravel rejects a non-image before calling the model.
const bad = await user.browser.submit("/predictions/create", "/predictions", { description: "e2e bad" }, { file: "not_image.png", bytes: Buffer.from("not an image"), mime: "image/png" });
const after = ((await (await user.browser.request("/predictions")).text()).match(/<a href="predictions\/\d+"/g) ?? []).length;
record("S10", "Non-image upload rejected", `302 back to the form; still ${distinct} rows`, `${bad.status} to ${location(bad)}; ${after} rows`, bad.status === 302 && location(bad) === "/predictions/create" && after === distinct);

const revision = execFileSync("git", ["rev-parse", "HEAD"], { cwd: root }).toString().trim();
const dirty = execFileSync("git", ["status", "--porcelain"], { cwd: root }).toString().trim().split("\n").filter(Boolean);
const versions = {
  node: process.version,
  php: execFileSync("php", ["-r", "echo PHP_VERSION;"]).toString(),
  laravel: execFileSync("php", ["artisan", "--version"], { cwd: webApp }).toString().trim(),
  database: execFileSync("php", ["artisan", "tinker", "--execute=echo config('database.default').' '.DB::selectOne(config('database.default')==='sqlite'?'select sqlite_version() v':'select version() v')->v;"], { cwd: webApp }).toString().trim(),
  python_packages: execFileSync(join(root, "flask-app/.venv/bin/python"), ["-c", "from importlib.metadata import version as v;print(', '.join(f'{p} {v(p)}' for p in ('tensorflow','flask','pillow','numpy')))"]).toString().trim(),
};
const report = {
  run_id: runId,
  feature: "Maize app end to end: Laravel upload -> Flask/TensorFlow -> database -> result page",
  mode: synthetic ? "smoke with synthetic images (labels are placeholders)" : "fixture leaf images",
  revision,
  uncommitted_changes: dirty,
  environment: { app_url: appUrl, model_url: modelUrl, platform: `${process.platform} ${process.arch}`, ...versions },
  reproduction: "Start flask-app/server.py and the Laravel server on 127.0.0.1, then: node scripts/app_e2e.mjs" + (synthetic ? " --synthetic" : ""),
  fixtures: fixtureRows,
  direct_predictions: direct,
  uploads,
  scenarios,
  summary: { passed: scenarios.filter((s) => s.status === "pass").length, total: scenarios.length },
  limits: [
    "Accuracy is not asserted: predictions are compared with the direct Flask result, not with the folder label.",
    "Recommendations are run-scoped placeholders, not agronomic advice.",
    "Model-service outage handling, password reset email and the roles screens are not exercised.",
  ],
};
mkdirSync(outDir, { recursive: true });
writeFileSync(join(outDir, "report.json"), JSON.stringify(report, null, 2) + "\n");
const md = [
  `# App E2E Run ${runId}`,
  "",
  `- Mode: ${report.mode}`,
  `- Revision: ${revision}${dirty.length ? ` with ${dirty.length} uncommitted paths` : ""}`,
  `- Result: ${report.summary.passed}/${report.summary.total} scenarios passed`,
  "",
  "| ID | Scenario | Expected | Observed | Status |",
  "| --- | --- | --- | --- | --- |",
  ...scenarios.map((s) => `| ${s.id} | ${s.name} | ${s.expected} | ${s.observed} | ${s.status} |`),
  "",
  "## Fixtures",
  "",
  "| File | Folder label | Direct prediction | SHA-256 |",
  "| --- | --- | --- | --- |",
  ...fixtureRows.map((f, i) => `| ${f.file} | ${f.label} | ${direct[i].prediction} | ${f.sha256} |`),
  "",
  "## Limits",
  "",
  ...report.limits.map((l) => `- ${l}`),
  "",
].join("\n");
writeFileSync(join(outDir, "report.md"), md);
console.log(`Report: ${relative(root, join(outDir, "report.json"))} (${report.summary.passed}/${report.summary.total})`);
process.exitCode = report.summary.passed === report.summary.total ? 0 : 1;
