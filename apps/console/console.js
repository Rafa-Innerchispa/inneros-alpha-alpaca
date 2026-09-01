const money = (n) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);

const kill = document.getElementById("kill");
const killState = document.getElementById("kill-state");
const banner = document.getElementById("ui-banner");
const sourceBadge = document.getElementById("source-badge");
let killOn = true;
let client;

function setBanner(state, text) {
  banner.dataset.state = state;
  banner.textContent = `${state} · ${text}`;
  sourceBadge.textContent = state === "LOADING" ? "LOADING" : sourceBadge.textContent;
}

function renderPipeline(items) {
  document.getElementById("pipeline").innerHTML = (items || [])
    .map(
      (s) => `<li>
        <strong>${s.label}</strong>
        <span>${s.detail}</span>
        <span class="state ${s.state}">${s.state}</span>
      </li>`
    )
    .join("");
}

function renderTrace(events) {
  document.getElementById("trace").innerHTML = (events || [])
    .map(
      (e) => `<li class="${e.status}">
        <div class="meta">
          <span>${e.ts}</span>
          <span class="badge ${e.source === "FIXTURE" ? "fixture" : "paper"}">${e.source}</span>
          <span>${e.from} → ${e.to}</span>
          <span class="state ${e.status}">${e.status}</span>
        </div>
        <div>${e.event}: ${e.detail}</div>
        <code>${e.correlation_id || ""}</code>
      </li>`
    )
    .join("");
}

function prependTrace(row) {
  const li = document.createElement("li");
  li.className = row.status;
  li.innerHTML = `<div class="meta"><span>${row.ts}</span><span class="badge ${row.source === "FIXTURE" ? "fixture" : "paper"}">${row.source}</span><span class="state ${row.status}">${row.status}</span></div><div>${row.event}: ${row.detail}</div>`;
  document.getElementById("trace").prepend(li);
}

function applySession(data) {
  sourceBadge.textContent = data.source || "FIXTURE";
  sourceBadge.classList.toggle("fixture", data.source === "FIXTURE");
  sourceBadge.classList.toggle("paper", data.source === "ALPACA_PAPER");
  document.getElementById("equity").textContent = money(data.portfolio.equity);
  document.getElementById("cash").textContent = money(data.portfolio.cash);
  document.getElementById("day-pl").textContent = money(data.portfolio.day_pl);
  document.getElementById("upl").textContent = money(data.portfolio.unrealized_pl);
  document.getElementById("portfolio-source").textContent = `portfolio source: ${data.portfolio_source || data.source}`;
  document.getElementById("corr").textContent = data.trace?.[0]?.correlation_id || "alpaca-hackathon-ui-20260901";
  renderPipeline(data.pipeline);
  renderTrace(data.trace);
  document.getElementById("positions").textContent = data.positions?.length
    ? `${data.positions.length} verified positions`
    : "No positions proven by backend.";
  const fallback = data.fallback ? ` fallback=${data.fallback}` : "";
  setBanner(data.live ? "PASS" : "NO_TRADE", data.live ? `paper spine live${fallback}` : `fixture console${fallback}`);
}

kill.addEventListener("click", () => {
  killOn = !killOn;
  kill.textContent = killOn ? "KILL SWITCH ON" : "KILL SWITCH OFF";
  kill.setAttribute("aria-pressed", String(killOn));
  kill.classList.toggle("off", !killOn);
  killState.textContent = killOn
    ? "BLOCKED · console execution disabled"
    : "NO_TRADE · switch off, console still does not auto-submit";
  prependTrace({
    ts: new Date().toISOString(),
    source: "INNEROS",
    from: "console",
    to: "risk",
    event: "kill_switch",
    status: killOn ? "BLOCKED" : "NO_TRADE",
    detail: killOn ? "Kill switch armed. Console execution path closed." : "Switch disarmed. No order is sent automatically.",
  });
});

async function boot() {
  const entry = resolveModuleEntry();
  applyShellChrome(entry);
  if (!entry.allowed) {
    setBanner("BLOCKED", "embedded gateway token missing");
    sourceBadge.textContent = "BLOCKED";
    return;
  }
  setBanner("LOADING", "loading session");
  const params = new URLSearchParams(window.location.search);
  client = createAlpacaApiClient({
    baseUrl: params.get("api") || "",
    fixtureUrl: "./fixtures/session.json",
    correlationId: params.get("correlation_id") || "alpaca-hackathon-ui-20260901",
  });
  try {
    const session = await client.loadSession();
    applySession(session);
  } catch (error) {
    sourceBadge.textContent = "FAIL";
    setBanner("FAIL", error.message || "session load failed");
    renderTrace([
      {
        ts: new Date().toISOString(),
        source: "INNEROS",
        from: "console",
        to: "client",
        event: "load_failed",
        status: "FAIL",
        correlation_id: "alpaca-hackathon-ui-20260901",
        detail: String(error.message || error),
      },
    ]);
  }
}

boot();
