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
assert.equal(manifest.routes.account, "/api/account");
assert.equal(manifest.routes.positions, "/api/positions");
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

const fixturePortfolio = client.mapPortfolio(
  { state: "NO_TRADE", source: "ALPACA_PAPER", reason: "alpaca_paper_credentials_missing" },
  fixture.portfolio
);
assert.equal(fixturePortfolio.source, "FIXTURE");
assert.equal(fixturePortfolio.portfolio.equity, 100000);

const realPaperPortfolio = client.mapPortfolio(
  {
    state: "PASS",
    source: "ALPACA_PAPER",
    account: { equity: "100250", last_equity: "100000", cash: "75000", buying_power: "150000", status: "ACTIVE" },
  },
  fixture.portfolio
);
assert.equal(realPaperPortfolio.source, "ALPACA_PAPER");
assert.equal(realPaperPortfolio.portfolio.equity, 100250);
assert.equal(realPaperPortfolio.portfolio.day_pl, 250);

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
  fixture,
  {
    state: "PASS",
    source: "ALPACA_PAPER",
    account: { equity: "100250", last_equity: "100000", cash: "75000", buying_power: "150000" },
  },
  {
    state: "PASS",
    source: "ALPACA_PAPER",
    positions: [{ symbol: "SPY", qty: "1", market_value: "550.10" }],
  }
);
assert.equal(paperSession.source, "ALPACA_PAPER");
assert.equal(paperSession.portfolio_source, "ALPACA_PAPER");
assert.equal(paperSession.positions_source, "ALPACA_PAPER");
assert.equal(paperSession.positions.length, 1);
assert.equal(paperSession.pipeline.find((row) => row.id === "execution").state, "PASS");
assert.equal(paperSession.trace[0].correlation_id, "corr-paper-1");

client.submitPaperOrder({ symbol: "SPY", side: "buy", qty: 1 }).then((result) => {
  assert.equal(result.state, "BLOCKED");
  assert.ok(result.reasons.includes("console_execution_disabled"));
  console.log("module_shell tests PASS");
});
