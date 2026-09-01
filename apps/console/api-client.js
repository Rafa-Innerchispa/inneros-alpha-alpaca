/**
 * Frontend client for the InnerOS Alpha paper spine.
 * Live paths:
 *   GET  /health
 *   GET  /api/session
 *   POST /api/intents/evaluate
 *   POST /api/orders/paper
 * Never invent fills. Fixture fallback is explicit.
 */
(function (root) {
  const TERMINAL = new Set(["PASS", "BLOCKED", "NO_TRADE", "FAIL"]);

  function normalizeState(value, fallback) {
    const state = String(value || "").toUpperCase();
    return TERMINAL.has(state) ? state : fallback;
  }

  async function fetchJson(url, options) {
    const response = await fetch(url, options);
    if (!response.ok) {
      const error = new Error(`http_${response.status}`);
      error.status = response.status;
      throw error;
    }
    return response.json();
  }

  function createAlpacaApiClient(options) {
    const base = String(options.baseUrl || "").replace(/\/$/, "");
    const fixtureUrl = options.fixtureUrl || "./fixtures/session.json";
    const correlationId = options.correlationId || "alpaca-hackathon-ui-20260901";

    async function loadFixture() {
      const data = await fetchJson(fixtureUrl);
      return { ...data, source: "FIXTURE", live: false, paper: true };
    }

    async function health() {
      if (!base) return { ok: false, reason: "no_backend_base" };
      return fetchJson(`${base}/health`);
    }

    async function session() {
      return fetchJson(`${base}/api/session?correlation_id=${encodeURIComponent(correlationId)}`);
    }

    function mapLiveSession(live, fixture) {
      const market = Array.isArray(live.market) ? live.market : [];
      const executions = Array.isArray(live.executions) ? live.executions : [];
      const liveFill = executions.some(
        (row) => row.alpaca_order_id && row.source === "ALPACA_PAPER" && row.state === "PASS"
      );
      const marketState = market.length ? "PASS" : "NO_TRADE";
      const execState = liveFill
        ? "PASS"
        : executions.some((row) => row.state === "BLOCKED")
          ? "BLOCKED"
          : executions.some((row) => row.state === "FAIL")
            ? "FAIL"
            : "NO_TRADE";
      return {
        source: liveFill
          ? "ALPACA_PAPER"
          : market[0]?.source === "ALPACA_PAPER"
            ? "ALPACA_PAPER"
            : "INNEROS",
        live: true,
        paper: live.mode === "paper",
        portfolio: fixture.portfolio,
        portfolio_source: "FIXTURE",
        positions: fixture.positions || [],
        pipeline: [
          {
            id: "market",
            label: "Market",
            state: marketState,
            detail: market.length
              ? market.map((m) => `${m.symbol} last=${m.last} (${m.source})`).join(" · ")
              : "Live session empty market.",
          },
          {
            id: "strategy",
            label: "Strategy",
            state: "NO_TRADE",
            detail: "TradeIntent only. UI does not auto-submit.",
          },
          {
            id: "risk",
            label: "Risk",
            state: executions.length
              ? normalizeState(executions.at(-1)?.risk?.state, "NO_TRADE")
              : "NO_TRADE",
            detail: "Deterministic PaperRiskEngine result only.",
          },
          {
            id: "execution",
            label: "Execution",
            state: execState,
            detail: liveFill
              ? "Verified Alpaca paper execution returned by the backend."
              : "No verified paper fill. Empty executions is NO_TRADE.",
          },
        ],
        trace: [
          {
            ts: new Date().toISOString(),
            source: liveFill ? "ALPACA_PAPER" : "INNEROS",
            from: "api-client",
            to: "session",
            event: "live_session",
            status: "PASS",
            correlation_id: live.correlation_id || correlationId,
            detail: liveFill
              ? "Connected to /api/session with verified Alpaca paper execution evidence."
              : "Connected to /api/session. Portfolio numbers remain FIXTURE until backend owns them.",
          },
        ],
        live_session: live,
      };
    }

    async function loadSession() {
      const fixture = await loadFixture();
      if (!base) return fixture;
      try {
        const probe = await health();
        if (!probe.ok || probe.paper_only !== true) {
          return {
            ...fixture,
            source: "FIXTURE",
            live: false,
            health: probe,
            fallback: "health_not_paper_only",
          };
        }
        const live = await session();
        return mapLiveSession(live, fixture);
      } catch (error) {
        return {
          ...fixture,
          source: "FIXTURE",
          live: false,
          fallback: error.message || "backend_unreachable",
        };
      }
    }

    async function evaluateIntent(intent) {
      if (!base) return { state: "BLOCKED", allowed: false, reasons: ["no_backend_base"] };
      return fetchJson(`${base}/api/intents/evaluate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...intent, paper_only: true }),
      });
    }

    async function submitPaperOrder(intent) {
      return {
        state: "BLOCKED",
        source: "DRY_RUN",
        reasons: ["console_execution_disabled", "use_backend_owner_flow_for_paper_order"],
        intent,
      };
    }

    return { loadFixture, loadSession, health, evaluateIntent, submitPaperOrder, normalizeState, mapLiveSession };
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { createAlpacaApiClient, TERMINAL };
  }
  root.createAlpacaApiClient = createAlpacaApiClient;
})(typeof globalThis !== "undefined" ? globalThis : this);
