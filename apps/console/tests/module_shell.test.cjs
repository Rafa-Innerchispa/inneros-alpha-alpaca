const fs = require("fs");
const path = require("path");
const assert = require("assert");
const { createAlpacaApiClient } = require("../api-client.js");
const { resolveModuleEntry } = require("../module-shell.js");

const root = path.join(__dirname, "..", "..", "..");
const manifest = JSON.parse(fs.readFileSync(path.join(root, "inneros.module.json"), "utf8"));

assert.equal(manifest.schema, "inneros.module/v1");
assert.equal(manifest.module_id, "alpaca-paper-console");
assert.equal(manifest.paper_only, true);
assert.equal(manifest.public_safe.fills, "never-fake");
assert.equal(manifest.routes.health, "/health");
assert.equal(manifest.routes.session, "/api/session");
assert.ok(manifest.capabilities.includes("kill.switch"));

const standalone = resolveModuleEntry(new URLSearchParams(""));
assert.equal(standalone.mode, "standalone");
assert.equal(standalone.allowed, true);

const embeddedOk = resolveModuleEntry(new URLSearchParams("embed=1&host_origin=https://inneros.local"));
assert.equal(embeddedOk.mode, "embedded");
assert.equal(embeddedOk.allowed, true);

const blocked = resolveModuleEntry(new URLSearchParams("embed=1&require_gateway=1"));
assert.equal(blocked.allowed, false);
assert.equal(blocked.reason, "gateway_token_missing");

const client = createAlpacaApiClient({ baseUrl: "", fixtureUrl: "http://invalid" });
client.submitPaperOrder({ symbol: "SPY", side: "buy", qty: 1 }).then((result) => {
  assert.equal(result.state, "BLOCKED");
  assert.ok(result.reasons.includes("console_never_submits_fills"));
  console.log("module_shell tests PASS");
});
