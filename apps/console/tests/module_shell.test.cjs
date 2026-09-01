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
assert.equal(manifest.public_safe.real_money, false);
assert.equal(manifest.routes.health, "/health");
assert.equal(manifest.routes.session, "/api/session");
assert.ok(manifest.capabilities.includes("kill.switch"));

const standalone = resolveModuleEntry(new URLSearchParams(""));
assert.equal(standalone.mode, "standalone");
assert.equal(standalone.allowed, true);

const embeddedOpen = resolveModuleEntry(new URLSearchParams("embed=1&host_origin=https://inneros.local"));
assert.equal(embeddedOpen.mode, "embedded");
assert.equal(embeddedOpen.allowed, true);

const blocked = resolveModuleEntry(new URLSearchParams("embed=1&require_gateway=1&host_origin=https://inneros.local"));
assert.equal(blocked.allowed, false);
assert.equal(blocked.reason, "gateway_token_missing");

const embeddedAuthed = resolveModuleEntry(new URLSearchParams("embed=1&require_gateway=1&module_token=test-token"));
assert.equal(embeddedAuthed.allowed, true);
assert.equal(embeddedAuthed.tokenPresent, true);

const client = createAlpacaApiClient({ baseUrl: "" });
const fixture = {
  portfolio: { equity: 100000, cash: 100000, day_pl: 0, unrealized_pl: 0 },
  positions: [],
};
const paperSession = client.mapLiveSession(
  {
    mode: "paper",
    correlation_id: "corr-paper-1",
    market: [{ symbol: "SPY", last: 550.1, source: "ALPACA_PAPER" }],
    executions: [
      {
        state: "PASS",
        source: "ALPACA_PAPER",
        alpaca_order_id: "paper-order-123",
        risk: { state: "PASS" },
      },
    ],
  },
  fixture
);
assert.equal(paperSession.source, "ALPACA_PAPER");
assert.equal(paperSession.pipeline.find((row) => row.id === "execution").state, "PASS");
assert.equal(paperSession.trace[0].correlation_id, "corr-paper-1");

client.submitPaperOrder({ symbol: "SPY", side: "buy", qty: 1 }).then((result) => {
  assert.equal(result.state, "BLOCKED");
  assert.ok(result.reasons.includes("console_execution_disabled"));
  console.log("module_shell tests PASS");
});
