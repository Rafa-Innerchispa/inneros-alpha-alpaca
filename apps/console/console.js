const money = (n) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);

const kill = document.getElementById("kill");
const killState = document.getElementById("kill-state");
let killOn = true;

function renderPipeline(items) {
  document.getElementById("pipeline").innerHTML = items
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
  document.getElementById("trace").innerHTML = events
    .map(
      (e) => `<li class="${e.status}">
        <div class="meta">
          <span>${e.ts}</span>
          <span class="badge fixture">${e.source}</span>
          <span>${e.from} → ${e.to}</span>
          <span class="state ${e.status}">${e.status}</span>
        </div>
        <div>${e.event}: ${e.detail}</div>
        <code>${e.correlation_id}</code>
      </li>`
    )
    .join("");
}

function applySession(data) {
  document.getElementById("source-badge").textContent = data.source || "FIXTURE";
  document.getElementById("equity").textContent = money(data.portfolio.equity);
  document.getElementById("cash").textContent = money(data.portfolio.cash);
  document.getElementById("day-pl").textContent = money(data.portfolio.day_pl);
  document.getElementById("upl").textContent = money(data.portfolio.unrealized_pl);
  document.getElementById("corr").textContent = data.trace[0]?.correlation_id || "none";
  renderPipeline(data.pipeline);
  renderTrace(data.trace);
  if (!data.positions.length) {
    document.getElementById("positions").textContent =
      "No positions. Truth: empty book, not a simulated fill.";
  }
}

kill.addEventListener("click", () => {
  killOn = !killOn;
  kill.textContent = killOn ? "KILL SWITCH ON" : "KILL SWITCH OFF";
  kill.setAttribute("aria-pressed", String(killOn));
  kill.classList.toggle("off", !killOn);
  killState.textContent = killOn
    ? "BLOCKED · no broker submit"
    : "NO_TRADE · switch off, still no backend so no submit";
  const row = {
    ts: new Date().toISOString(),
    source: "FIXTURE",
    from: "console",
    to: "risk",
    event: "kill_switch",
    status: killOn ? "BLOCKED" : "NO_TRADE",
    correlation_id: "alpaca-hackathon-ui-20260901",
    detail: killOn ? "Kill switch armed. Execution path closed." : "Switch disarmed locally. Still no live broker.",
  };
  const li = document.createElement("li");
  li.className = row.status;
  li.innerHTML = `<div class="meta"><span>${row.ts}</span><span class="badge fixture">${row.source}</span><span class="state ${row.status}">${row.status}</span></div><div>${row.event}: ${row.detail}</div>`;
  document.getElementById("trace").prepend(li);
});

fetch("./fixtures/session.json")
  .then((r) => r.json())
  .then(applySession)
  .catch(() => {
    document.getElementById("source-badge").textContent = "FAIL";
    renderTrace([
      {
        ts: new Date().toISOString(),
        source: "FIXTURE",
        from: "console",
        to: "fixtures",
        event: "load_failed",
        status: "FAIL",
        correlation_id: "alpaca-hackathon-ui-20260901",
        detail: "Could not load fixtures/session.json. Serve via http.server, not file://.",
      },
    ]);
  });
