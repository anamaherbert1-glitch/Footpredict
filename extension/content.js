(() => {
  const normalize = (value) => value.replace(/\\s+/g, " ").trim();

  function extractMatch() {
    const selectors = [
      "[data-testid*='team']",
      "[class*='team-name']",
      "[class*='participant']",
      "[class*='competitor']",
      "[class*='event-name']"
    ];

    const candidates = [];
    for (const selector of selectors) {
      document.querySelectorAll(selector).forEach((el) => {
        const text = normalize(el.textContent || "");
        if (text && text.length >= 2 && text.length <= 80) candidates.push(text);
      });
    }

    const unique = [...new Set(candidates)];
    for (let i = 0; i < unique.length - 1; i += 1) {
      const a = unique[i];
      const b = unique[i + 1];
      if (!/^\d/.test(a) && !/^\d/.test(b) && a !== b) {
        return { homeTeam: a, awayTeam: b, source: "dom" };
      }
    }

    const text = normalize(document.body?.innerText || "");
    const match = text.match(/([^\n|]{2,50})\\s+(?:vs?\\.?|–|—|-)\\s+([^\n|]{2,50})/i);
    if (match) {
      return {
        homeTeam: normalize(match[1]),
        awayTeam: normalize(match[2]),
        source: "text"
      };
    }

    return null;
  }

  function publish() {
    const match = extractMatch();
    if (!match) return;
    chrome.storage.local.set({ detectedMatch: { ...match, detectedAt: Date.now() } });
    chrome.runtime.sendMessage({ type: "MATCH_DETECTED", data: match });
  }

  publish();
  const observer = new MutationObserver(() => {
    clearTimeout(window.__footPredictTimer);
    window.__footPredictTimer = setTimeout(publish, 700);
  });
  observer.observe(document.documentElement, { childList: true, subtree: true });
})();