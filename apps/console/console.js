const money = (n) =>
  new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(Number(n || 0));

const esc = (value) =>
  String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");

const params = new URLSearchParams(window.location.search);
const moduleEntry = window.resolveModuleEntry
  ? window.resolveModuleEntry(params)
  : { mode: "standalone", embed: false, allowed: true, reason: "ok" };
const API_BASE = (
  params.get("api") ||
  window.INNEROS_ALPHA_API ||
  "http://127.0.0.1:8088"
).replace(/\/$/, "");
const api = window.createAlpacaApiClient
  ? window.createAlpacaApiClient({ baseUrl: API_BASE })
  : null;

const kill = document.getElementById("kill");
const killState = document.getElementById("kill-state");
const sourceBadge = document.getElementById("source-badge");
const backendBadge = document.getElementById("backend-badge");
const truthBadge = document.getElementById("truth-badge");
const truthBanner = document.getElementById("truth-banner");
const runButton = document.getElementById("run-analysis");
const ticker = document.getElementById("ticker");

let killOn = true;
let backendOnline = false;

function setBadge(element, text, className = "") {
  if (!element) return;
  element.textContent = text;
  element.className = `badge ${className}`.trim();
}

function setTruth(state, detail) {
  setBadge(
    truthBadge,
    state,
    state === "LIVE" || state === "PASS" || state === "PAPER_LIVE" ? "live" : "fixture"
  );
  if (truthBanner) {
    truthBanner.className = `truth-banner ${state}`;
    truthBanner.textContent = `${state} · ${detail}`;
  }
}

function renderPipeline(items) {
  document.getElementById("pipeline").innerHTML = items
    .map(
      (s) => `<li>
        <strong>${esc(s.label)}</strong>
        <span>${esc(s.detail)}</span>
        <span class="state ${esc(s.state)}">${esc(s.state)}</span>
      </li>`
    )
    .join("");
}

function normalizeTrace(event) {
  return {
    ts: event.ts || new Date().toISOString(),
    source: event.source || "UNKNOWN",
    from: event.from || event.from_agent || "unknown",
    to: event.to || event.to_agent || "unknown",
    event: event.event || "event",
    status: event.status || "FAIL",
    correlation_id: event.correlation_id || "none",
    detail: event.detail || "",
  };
}

function renderTrace(events) {
  document.getElementById("trace").innerHTML = events
    .map(normalizeTrace)
    .map(
      (e) => `<li class="${esc(e.status)}">
        <div class="meta">
          <span>${esc(e.ts)}</span>
          <span class="badge ${e.source === "FIXTURE" ? "fixture" : "live"}">${esc(e.source)}</span>
          <span>${esc(e.from)} → ${esc(e.to)}</span>
          <span class="state ${esc(e.status)}">${esc(e.status)}</span>
        </div>
        <div>${esc(e.event)}: ${esc(e.detail)}</div>
        <code>${esc(e.correlation_id)}</code>
      </li>`
    )
    .join("");
}

function applyPortfolio(portfolio) {
  document.getElementById("equity").textContent = money(portfolio.equity);
  document.getElementById("cash").textContent = money(portfolio.cash);
  document.getElementById("day-pl").textContent = money(portfolio.day_pl);
  document.getElementById("upl").textContent = money(portfolio.unrealized_pl);
  document.getElementById("positions").textContent = portfolio.open_positions
    ? `${portfolio.open_positions} open paper position(s).`
    : "No open positions. Truth: empty book, not a simulated fill.";
}

function applyFixtureSession(data) {
  setBadge(sourceBadge, "FIXTURE", "fixture");
  setTruth("FIXTURE", "Backend unavailable. Explicit fixture session; no fills.");
  applyPortfolio({ ...data.portfolio, open_positions: data.positions?.length || 0 });
  document.getElementById("corr").textContent = data.trace[0]?.correlation_id || "fixture";
  renderPipeline(data.pipeline);
  renderTrace(data.trace);
}

function applyPipeline(result) {
  const source = result.snapshot?.source || "UNKNOWN";
  setBadge(sourceBadge, source, source === "FIXTURE" ? "fixture" : "live");
  document.getElementById("corr").textContent = result.correlation_id;

  const trace = result.trace || [];
  const byEvent = Object.fromEntries(trace.map((event) => [event.event, event]));
  const execution = byEvent.execution_result?.status || result.execution?.status || "FAIL";
  const risk = byEvent.risk_decision?.status || result.risk?.status || "FAIL";
  const contract = byEvent.contract_selection?.status || result.contract_selection?.status || "FAIL";
  const truth =
    execution === "blocked" || execution === "BLOCKED" || contract === "BLOCKED"
      ? "BLOCKED"
      : risk === "NO_TRADE" || execution === "NO_TRADE" || contract === "NO_TRADE"
        ? "NO_TRADE"
        : source === "FIXTURE"
          ? "FIXTURE"
          : "LIVE";
  setTruth(truth, `correlation ${result.correlation_id || "none"} · analysis only`);
  renderPipeline([
    {
      label: "Market",
      state: byEvent.market_snapshot?.status || "FAIL",
      detail: byEvent.market_snapshot?.detail || "No market evidence",
    },
    {
      label: "Strategy",
      state: byEvent.trade_intent?.status || "FAIL",
      detail: byEvent.trade_intent?.detail || "No TradeIntent",
    },
    {
      label: "Contract",
      state: byEvent.contract_selection?.status || "FAIL",
      detail: byEvent.contract_selection?.detail || "No deterministic contract selection",
    },
    {
      label: "Risk",
      state: byEvent.risk_decision?.status || "FAIL",
      detail: byEvent.risk_decision?.detail || "No risk decision",
    },
    {
      label: "Execution",
      state: byEvent.execution_result?.status || "FAIL",
      detail: byEvent.execution_result?.detail || "No execution result",
    },
  ]);
  renderTrace(trace);
}

function renderKillState() {
  kill.textContent = killOn ? "KILL SWITCH ON" : "KILL SWITCH OFF";
  kill.setAttribute("aria-pressed", String(killOn));
  kill.classList.toggle("off", !killOn);
  killState.textContent = killOn
    ? "BLOCKED · server execution path closed"
    : "PAPER path armed · contract selection + deterministic risk gates still apply";
}

async function loadFixture() {
  const response = await fetch("./fixtures/session.json");
  if (!response.ok) throw new Error("fixture load failed");
  applyFixtureSession(await response.json());
}

async function runAnalysis() {
  if (!api) return;
  runButton.disabled = true;
  runButton.textContent = "RUNNING LOCAL ANALYSIS…";
  setTruth("LOADING", "POST /api/pipeline?execute=false");
  try {
    const result = await api.runPipeline(ticker.value);
    applyPipeline(result);
  } catch (error) {
    setBadge(backendBadge, "API FAIL", "fixture");
    backendOnline = false;
    await loadFixture();
    renderTrace([
      {
        ts: new Date().toISOString(),
        source: "FIXTURE",
        from: "console",
        to: "backend",
        event: "analysis_fallback",
        status: "FAIL",
        correlation_id: "fixture-fallback",
        detail: `Backend unavailable: ${error.name || "Error"}. Fixture loaded explicitly.`,
      },
    ]);
  } finally {
    runButton.disabled = false;
    runButton.textContent = "RUN LOCAL ANALYSIS";
  }
}

kill.addEventListener("click", async () => {
  const requested = !killOn;
  if (!backendOnline) {
    killOn = requested;
    renderKillState();
    killState.textContent += " · local UI only, backend unavailable";
    return;
  }
  try {
    const state = await api.setKillSwitch(requested);
    killOn = Boolean(state.enabled);
    renderKillState();
    await runAnalysis();
  } catch (error) {
    setBadge(backendBadge, "API FAIL", "fixture");
    backendOnline = false;
    killState.textContent = "FAIL · could not synchronize server kill switch";
  }
});

runButton.addEventListener("click", runAnalysis);

async function boot() {
  if (window.applyShellChrome) window.applyShellChrome(moduleEntry);
  if (!moduleEntry.allowed) {
    backendOnline = false;
    setBadge(backendBadge, "BLOCKED", "fixture");
    setTruth("BLOCKED", "Embedded gateway token missing. Standalone demo remains separate from authenticated embedding.");
    renderKillState();
    if (runButton) runButton.disabled = true;
    renderTrace([
      {
        ts: new Date().toISOString(),
        source: "FIXTURE",
        from: "console",
        to: "module-gateway",
        event: "embed_blocked",
        status: "BLOCKED",
        correlation_id: "embed-blocked",
        detail: moduleEntry.reason,
      },
    ]);
    return;
  }

  setTruth("LOADING", `probing ${API_BASE}/health`);
  setBadge(backendBadge, "API CHECKING", "freeze");
  try {
    const [health, portfolio, killStateResponse] = await Promise.all([
      api.health(),
      api.portfolio(),
      api.getKillSwitch(),
    ]);
    backendOnline = Boolean(health.ok);
    setBadge(backendBadge, backendOnline ? "API LIVE" : "API FAIL", backendOnline ? "live" : "fixture");
    killOn = Boolean(killStateResponse.enabled);
    renderKillState();
    applyPortfolio(portfolio);
    const portfolioSource = String(portfolio.source || "FIXTURE");
    setBadge(sourceBadge, portfolioSource, portfolioSource === "FIXTURE" ? "fixture" : "live");
    await runAnalysis();
  } catch (error) {
    backendOnline = false;
    setBadge(backendBadge, "API OFFLINE", "fixture");
    renderKillState();
    try {
      await loadFixture();
    } catch {
      setBadge(sourceBadge, "FAIL", "fixture");
      setTruth("FAIL", "Backend and fixture session are unavailable. Serve apps/console over HTTP.");
      renderTrace([
        {
          ts: new Date().toISOString(),
          source: "FIXTURE",
          from: "console",
          to: "fixtures",
          event: "boot_failed",
          status: "FAIL",
          correlation_id: "boot-failed",
          detail: "Backend and fixture session are unavailable. Serve apps/console over HTTP.",
        },
      ]);
    }
  }
}

boot();
