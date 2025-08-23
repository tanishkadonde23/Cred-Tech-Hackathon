console.log("✅ graphs.js loaded");

// Get ticker from URL
const ticker = window.location.pathname.split("/").pop();
document.getElementById("companyTitle").innerText = `${ticker} - Company Graphs`;

async function loadGraphs() {
  try {
    const response = await fetch(`/predict_one/${ticker}`);
    const data = await response.json();

    // Example 1: Score Trends
    new Chart(document.getElementById("scoreChart"), {
      type: "line",
      data: {
        labels: ["T1", "T2", "T3", "T4"], // Replace with real timestamps
        datasets: [
          { label: "Final Score", data: data.trends.final, borderColor: "#58a6ff", fill: false },
          { label: "Rule Score", data: data.trends.rule, borderColor: "#d29922", fill: false },
          { label: "ML Score", data: data.trends.ml, borderColor: "#2ea043", fill: false }
        ]
      }
    });

    // Example 2: Feature Importance
    new Chart(document.getElementById("featureChart"), {
      type: "bar",
      data: {
        labels: data.features.names,
        datasets: [{ label: "Importance", data: data.features.values, backgroundColor: "#58a6ff" }]
      }
    });

    // Example 3: Event Sentiment
    new Chart(document.getElementById("sentimentChart"), {
      type: "pie",
      data: {
        labels: ["Positive", "Neutral", "Negative"],
        datasets: [{
          data: [data.sentiment.positive, data.sentiment.neutral, data.sentiment.negative],
          backgroundColor: ["#2ea043", "#79c0ff", "#f85149"]
        }]
      }
    });
  } catch (err) {
    console.error(err);
    alert("⚠️ Could not load graphs");
  }
}

loadGraphs();
