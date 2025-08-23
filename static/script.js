console.log("✅ script.js loaded");

async function getScores() {
  const tickerInput = document.getElementById("tickerInput");
  if (!tickerInput) return alert("Missing input field with id='tickerInput'");

  const tickersText = tickerInput.value.trim();
  if (!tickersText) return alert("Enter at least one ticker");

  const tickers = tickersText.split(",").map(t => t.trim());

  try {
    const response = await fetch("/predict", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ tickers })
    });

    const data = await response.json();
    const resultsDiv = document.getElementById("results");
    if (!resultsDiv) return alert("Missing container with id='results'");
    resultsDiv.innerHTML = "";

    // Map tickers to company details
    const companyInfo = {
      TSLA: { name: "Tesla", logo: "https://logo.clearbit.com/tesla.com" },
      AAPL: { name: "Apple", logo: "https://logo.clearbit.com/apple.com" },
      MSFT: { name: "Microsoft", logo: "https://logo.clearbit.com/microsoft.com" }
    };

    data.results.forEach((result, index) => {
      const card = document.createElement("div");
      card.className = "card";

      const ticker = tickers[index]?.toUpperCase() || "UNKNOWN";
      const company = companyInfo[ticker] || { name: ticker, logo: "https://logo.clearbit.com/yahoo.com" };

      // Header
      const header = `
        <div class="card-header">
          <img src="${company.logo}" alt="${company.name} logo" class="company-logo">
          <span class="company-name">${company.name}</span>
        </div>
      `;

      // Scores
      const scores = `
        <div><strong>Final Score:</strong> ${result.final_score}</div>
        <div><strong>Rule Score:</strong> ${result.rule_score}</div>
        <div><strong>ML Score:</strong> ${result.ml_score ?? "N/A"}</div>
      `;

      // Explanation
      const explanation = `
        <h4>Explanation</h4>
        <ul>${result.explanation.map(e => `<li>${e}</li>`).join("")}</ul>
      `;

      // Events
      let eventsHTML = "";
      if (result.events && result.events.length > 0) {
        eventsHTML = "<h4>Events</h4><div class='events-container'>";
        
        result.events.forEach(ev => {
          let icon = "📰";
          if (ev.sentiment > 0.2) icon = "📈";
          if (ev.sentiment < -0.2) icon = "⚠️";

          const shortHeadline = ev.headline.length > 60 
            ? ev.headline.substring(0, 60) + "…" 
            : ev.headline;

          eventsHTML += `
            <div class="event-card" title="${ev.headline}">
              <span class="event-icon">${icon}</span>
              <span class="event-text">${shortHeadline}</span>
              <span class="event-sentiment">(${ev.sentiment})</span>
            </div>
          `;
        });

        eventsHTML += "</div>";
      }

      // Graph button
      const graphButton = `
        <button class="graph-btn" onclick="viewGraphs('${ticker}')">📊 View Graphs</button>
      `;

      card.innerHTML = header + scores + explanation + eventsHTML + graphButton;
      resultsDiv.appendChild(card);
    });
  } catch (err) {
    console.error(err);
    alert("⚠️ Failed to fetch scores");
  }
}

// Navigate to graphs page
function viewGraphs(ticker) {
  window.location.href = `/graphs/${ticker}`;
}
