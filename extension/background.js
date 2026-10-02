// background.js

chrome.sidePanel.setPanelBehavior({ openPanelOnActionClick: true })
  .catch(err => console.error(err));

// Relaye les messages si besoin
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "MATCH_DETECTED") {
    // Stockage déjà fait côté content, on peut logger
    console.log("[FootPredict] Match reçu:", message.data?.homeTeam, "vs", message.data?.awayTeam);
  }
});
