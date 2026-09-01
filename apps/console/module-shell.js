(function (root) {
  function readQuery() {
    return new URLSearchParams(root.location ? root.location.search : "");
  }

  function resolveModuleEntry(search) {
    const params = search || readQuery();
    const embed = params.get("embed") === "1";
    const hostOrigin = params.get("host_origin") || "";
    const token = params.get("module_token") || "";
    const standalone = !embed;
    const gatewayRequired = embed && params.get("require_gateway") === "1";
    const allowed = standalone || !gatewayRequired || Boolean(token);
    return {
      mode: standalone ? "standalone" : "embedded",
      embed,
      hostOrigin,
      tokenPresent: Boolean(token),
      allowed,
      backHref: hostOrigin || params.get("back") || "",
      reason: allowed ? "ok" : "gateway_token_missing",
    };
  }

  function applyShellChrome(entry) {
    const hostLink = document.getElementById("host-back");
    const modeBadge = document.getElementById("mode-badge");
    if (modeBadge) modeBadge.textContent = entry.mode === "embedded" ? "EMBEDDED" : "STANDALONE";
    if (hostLink) {
      if (entry.embed && entry.backHref) {
        hostLink.hidden = false;
        hostLink.href = entry.backHref;
      } else {
        hostLink.hidden = true;
      }
    }
    if (entry.allowed && entry.embed && entry.hostOrigin && root.parent !== root) {
      root.parent.postMessage(
        { type: "inneros.module.ready", module_id: "alpaca-paper-console", paper_only: true },
        entry.hostOrigin
      );
    }
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { resolveModuleEntry };
  }
  root.resolveModuleEntry = resolveModuleEntry;
  root.applyShellChrome = applyShellChrome;
})(typeof globalThis !== "undefined" ? globalThis : this);
