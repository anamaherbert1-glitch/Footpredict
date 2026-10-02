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
    return true;
  } catch {
    $("status").textContent = "API non disponible — vérifie l'URL et le serveur.";
    return false;
  }
}

function percent(value) {
  return (Number(value) * 100).toFixed(1) + "%";
}

async function findTeam(api, name) {
  const response = await fetch(api + "/teams/search?q=" + encodeURIComponent(name) + "&limit=5");
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || "Recherche équipe impossible");
  if (!data.length) throw new Error("Équipe introuvable dans Neon : " + name);
  const exact = data.find(t =>
    (t.name || "").toLowerCase() === name.toLowerCase() ||
    (t.short_name || "").toLowerCase() === name.toLowerCase()
  );
  if (!exact && data.length > 1) {
    throw new Error("Plusieurs équipes correspondent à « " + name + " ». Recherche plus précise nécessaire.");
  }
  return exact || data[0];
}

async function predict() {
  const api = $("apiUrl").value.replace(/\/$/, "");
  const homeName = $("homeTeam").value.trim();
  const awayName = $("awayTeam").value.trim();

  if (!homeName || !awayName) {
    $("status").textContent = "Aucun match détecté.";
    return;
  }

  $("status").textContent = "Recherche des équipes dans Neon…";
  $("teamStatus").textContent = "Identification des équipes…";

  try {
    const [home, away] = await Promise.all([
      findTeam(api, homeName),
      findTeam(api, awayName)
    ]);

    $("teamStatus").textContent =
      home.name + " vs " + away.name + " — équipes trouvées dans Neon.";

    $("status").textContent = "Calcul en cours…";

    const response = await fetch(api + "/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        home_team_id: home.id,
        away_team_id: away.id,
        league_id: home.league_id || null
      })
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
  } catch (error) {
    $("teamStatus").textContent = error.message;
    $("status").textContent = "Analyse impossible";
  }
}

$("refresh").addEventListener("click", async () => {
  await getSettings();
  await checkApi();
});

$("saveApi").addEventListener("click", async () => {
  await chrome.storage.local.set({ apiUrl: $("apiUrl").value.trim() || DEFAULT_API });
  await checkApi();
});

$("predict").addEventListener("click", predict);
getSettings().then(checkApi);
