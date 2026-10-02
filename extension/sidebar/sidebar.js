const $ = (id) => document.getElementById(id);
const DEFAULT_API = "http://localhost:8000";

async function getSettings() {
  const data = await chrome.storage.local.get(["apiUrl", "detectedMatch"]);
  $("apiUrl").value = data.apiUrl || DEFAULT_API;
  if (data.detectedMatch) {
    $("homeTeam").value = data.detectedMatch.homeTeam || "";
    $("awayTeam").value = data.detectedMatch.awayTeam || "";
    $("source").textContent = "Match détecté automatiquement.";
  }
}
async function checkApi() {
  const api = $("apiUrl").value.replace(/\/$/, "");
  try {
    const response = await fetch(api + "/health");
    if (!response.ok) throw new Error("HTTP " + response.status);
    $("status").textContent = "API connectée à Neon";
  } catch {
    $("status").textContent = "API non disponible — vérifie l'URL et le serveur.";
  }
}
function percent(value) { return (Number(value) * 100).toFixed(1) + "%"; }

async function predict() {
  const api = $("apiUrl").value.replace(/\/$/, "");
  const payload = {
    home_team_id: $("homeTeam").value.trim(),
    away_team_id: $("awayTeam").value.trim(),
    home_attack: Number($("homeAttack").value),
    home_defense: Number($("homeDefense").value),
    away_attack: Number($("awayAttack").value),
    away_defense: Number($("awayDefense").value)
  };
  if (!payload.home_team_id || !payload.away_team_id) {
    $("status").textContent = "Renseigne les deux équipes.";
    return;
  }
  $("status").textContent = "Calcul en cours…";
  try {
    const response = await fetch(api + "/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Erreur API");
    const p = data.prediction;
    $("pHome").textContent = percent(p.prob_home);
    $("pDraw").textContent = percent(p.prob_draw);
    $("pAway").textContent = percent(p.prob_away);
    $("pOver").textContent = percent(p.prob_over_25);
    $("pBtts").textContent = percent(p.prob_btts_yes);
    $("score").textContent = p.most_likely_score.join("-");
    $("result").classList.remove("hidden");
    $("status").textContent = "Analyse terminée";
  } catch (error) { $("status").textContent = error.message; }
}
$("refresh").addEventListener("click", async () => { await getSettings(); await checkApi(); });
$("saveApi").addEventListener("click", async () => {
  await chrome.storage.local.set({ apiUrl: $("apiUrl").value.trim() || DEFAULT_API });
  await checkApi();
});
$("predict").addEventListener("click", predict);
getSettings().then(checkApi);