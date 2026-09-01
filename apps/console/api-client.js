/**
 * Frontend client for the InnerOS Alpha paper spine.
 * Never invent fills, positions or portfolio values. Fixture fallback is explicit.
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

  function numberOr(value, fallback = 0) {
    const n = Number(value);
    return Number.isFinite(n) ? n : fallback;
  }

  function createAlpacaApiClient(options) {
    const base = String(options.baseUrl || "").replace(/\/$/, "");
    const fixtureUrl = options.fixtureUrl || "./fixtures/session.json";
    const correlationId = options.correlationId || "alpaca-hackathon-ui-20260901";

    async function loadFixture() {
      const data = await fetchJson(fixtureUrl);
      return { ...data, source: "FIXTURE", live: false, paper: true, portfolio_source: "FIXTURE" };
    }

    async function health() {
      if (!base) return { ok: false, reason: "no_backend_base" };
      return fetchJson(`${base}/health`);
    }

    async function session() {
      return fetchJson(`${base}/api/session?correlation_id=${encodeURIComponent(correlationId)}`);
    }

    async function account() {
      if (!base) return { state: "NO_TRADE", source: "FIXTURE", reason: "no_backend_base" };
      return fetchJson(`${base}/api/account`);
    }

    async function positions() {
      if (!base) return { state: "NO_TRADE", source: "FIXTURE", positions: [], reason: "no_backend_base" };
      return fetchJson(`${base}/api/positions`);
    }

    function mapPortfolio(accountResult, fixturePortfolio) {
      if (accountResult?.state !== "PASS" || accountResult?.source !== "ALPACA_PAPER") {
        return { portfolio: fixturePortfolio, source: "FIXTURE" };
      }
      const a = accountResult.account || {};
      const equity = numberOr(a.equity);
      const lastEquity = numberOr(a.last_equity, equity);
      return {
        source: "ALPACA_PAPER",
        portfolio: {
          equity,
          cash: numberOr(a.cash),
          day_pl: equity - lastEquity,
          unrealized_pl: 0,
          buying_power: numberOr(a.buying_power),
          status: a.status || "unknown",
        },
      };
    }

    function mapLiveSession(live, fixture, accountResult, positionsResult) {
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
      const portfolioMapped = mapPortfolio(accountResult, fixture.portfolio);
      const verifiedPositions =
        positionsResult?.state === "PASS" && positionsResult?.source === "ALPACA_PAPER"
          ? positionsResult.positions || []
          : [];
      const strongestSource =
        liveFill || portfolioMapped.source === "ALPACA_PAPER" || verifiedPositions.length
          ? "ALPACA_PAPER"
          : "INNEROS";

      const trace = [
        {
          ts: new Date().toISOString(),
          source: strongestSource,
          from: "api-client",
          to: "session",
          event: "live_session",
          status: "PASS",
          correlation_id: live.correlation_id || correlationId,
          detail:
            portfolioMapped.source === "ALPACA_PAPER"
              ? "Backend session plus verified Alpaca paper account data."
              : "Backend session live; portfolio remains FIXTURE until Alpaca paper account is authenticated.",
        },
      ];
      if (accountResult?.state && accountResult.state !== "PASS") {
        trace.push({
          ts: new Date().toISOString(),
          source: "INNEROS",
          from: "api-client",
          to: "alpaca-account",
          event: "paper_account",
          status: normalizeState(accountResult.state, "NO_TRADE"),
          correlation_id: live.correlation_id || correlationId,
          detail: accountResult.reason || "Paper account data unavailable.",
        });
      }

      return {
        source: strongestSource,
        live: true,
        paper: live.mode === "paper",
        portfolio: portfolioMapped.portfolio,
        portfolio_source: portfolioMapped.source,
        positions: verifiedPositions,
        positions_source: verifiedPositions.length || positionsResult?.state === "PASS" ? "ALPACA_PAPER" : "FIXTURE",
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
        trace,
        live_session: live,
        account_result: accountResult,
        positions_result: positionsResult,
      };
    }

    async function loadSession() {
      const fixture = await loadFixture();
      if (!base) return fixture;
      try {
        const probe = await health();
        if (!probe.ok || probe.paper_only !== true) {
          return { ...fixture, health: probe, fallback: "health_not_paper_only" };
        }
        const [live, accountResult, positionsResult] = await Promise.all([
          session(),
          account(),
          positions(),
        ]);
        return mapLiveSession(live, fixture, accountResult, positionsResult);
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

    return {
      loadFixture,
      loadSession,
      health,
      session,
      account,
      positions,
      evaluateIntent,
      submitPaperOrder,
      normalizeState,
      mapPortfolio,
      mapLiveSession,
    };
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { createAlpacaApiClient, TERMINAL };
  }
  root.createAlpacaApiClient = createAlpacaApiClient;
})(typeof globalThis !== "undefined" ? globalThis : this);
