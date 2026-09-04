(function (root) {
  function createAlpacaApiClient(options) {
    const opts = options || {};
    const baseUrl = String(opts.baseUrl || "").replace(/\/$/, "");
    const fetchImpl = opts.fetchImpl || (typeof fetch === "function" ? fetch.bind(root) : null);
    const timeoutMs = opts.timeoutMs || 15000;

    async function request(path, init) {
      if (!baseUrl) throw new Error("no_api_base");
      if (!fetchImpl) throw new Error("no_fetch");
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), timeoutMs);
      try {
        const response = await fetchImpl(`${baseUrl}${path}`, {
          ...(init || {}),
          credentials: "same-origin",
          headers: {
            "Content-Type": "application/json",
            ...((init && init.headers) || {}),
          },
          signal: controller.signal,
        });
        if (response.status === 401) {
          root.location.href = "/login?next=/console/";
          throw new Error("authentication_required");
        }
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return await response.json();
      } finally {
        clearTimeout(timer);
      }
    }

    return {
      health() { return request("/health"); },
      ready() { return request("/ready"); },
      sovereignty() { return request("/api/sovereignty"); },
      mcpStatus() { return request("/api/mcp/status"); },
      portfolio() { return request("/api/portfolio"); },
      getKillSwitch() { return request("/api/kill-switch"); },
      setKillSwitch(enabled) {
        return request("/api/kill-switch", {
          method: "POST",
          body: JSON.stringify({ enabled: Boolean(enabled) }),
        });
      },
      runPipeline(ticker) {
        const symbol = encodeURIComponent(ticker || "SPY");
        return request(`/api/pipeline/${symbol}?execute=false`, { method: "POST" });
      },
      async submitPaperOrder() {
        return {
          status: "blocked",
          state: "BLOCKED",
          paper_only: true,
          reasons: ["console_never_submits_fills"],
          message: "Console never calls POST /api/execute. Kill switch, contract selection, and risk gates own execution on the server.",
        };
      },
    };
  }

  if (typeof module !== "undefined" && module.exports) module.exports = { createAlpacaApiClient };
  root.createAlpacaApiClient = createAlpacaApiClient;
})(typeof globalThis !== "undefined" ? globalThis : this);
