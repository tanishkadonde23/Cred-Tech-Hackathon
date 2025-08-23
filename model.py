# backend/model.py
import pickle
import numpy as np
import shap
import sqlite3
import spacy
from textblob import TextBlob
from build_features import build_features

# -------------------------------
# Globals
# -------------------------------
NEGATIVE_KEYWORDS = [
    "bankruptcy", "lawsuit", "restructuring", "default",
    "fraud", "investigation", "downgrade"
]
POSITIVE_KEYWORDS = [
    "record profit", "partnership", "acquisition", "expansion",
    "new product", "upgrade", "beat estimates"
]

DB_PATH = "scores.db"

# Load ML model
try:
    with open("ml_model.pkl", "rb") as f:
        ml_model = pickle.load(f)
except Exception:
    ml_model = None

# Load spaCy English model
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    nlp = None


# -------------------------------
# Rule-based score
# -------------------------------
def rule_based_score(features: dict):
    score = 70
    explanation = []

    # Stock movement
    if features["change_1d"] < -2:
        explanation.append(f"Stock fell {features['change_1d']:.2f}% → -20 points")
        score -= 20
    elif features["change_1d"] > 2:
        explanation.append(f"Stock rose {features['change_1d']:.2f}% → +10 points")
        score += 10
    else:
        explanation.append(f"Stock change {features['change_1d']:.2f}% → no major effect")

    # Debt-to-equity
    if features["debt_to_equity"] > 200:
        explanation.append(f"High debt ratio {features['debt_to_equity']:.2f} → -15 points")
        score -= 15
    else:
        explanation.append(f"Debt ratio {features['debt_to_equity']:.2f} is stable → no penalty")

    # P/E ratio
    if features["pe_ratio"] > 30:
        explanation.append(f"High P/E ratio {features['pe_ratio']:.2f} → -5 points")
        score -= 5
    elif features["pe_ratio"] > 0:
        explanation.append(f"P/E ratio {features['pe_ratio']:.2f} is reasonable → +5 points")
        score += 5

    # Market cap
    if features["market_cap"] > 1e11:
        explanation.append("Large market cap company → +5 points")
        score += 5
    elif features["market_cap"] > 0:
        explanation.append("Smaller market cap company → -5 points")
        score -= 5

    # EPS
    if features["eps"] > 0:
        explanation.append(f"Profitable with EPS {features['eps']} → +5 points")
        score += 5
    else:
        explanation.append("No EPS data or negative → -5 points")
        score -= 5

    # Book value
    if features["book_value"] > 0:
        explanation.append(f"Positive book value {features['book_value']} → +3 points")
        score += 3

    # News sentiment
    sentiment_effect = int(features["news_sentiment"] * 20)
    explanation.append(
        f"News sentiment {features['news_sentiment']:.2f} → {sentiment_effect:+} points"
    )
    score += sentiment_effect

    return max(min(score, 100), 0), explanation


# -------------------------------
# NLP Event Detection
# -------------------------------
def detect_events(headlines):
    events = []
    if not headlines:
        return events

    for h in headlines:
        entry = {"headline": h, "entities": [], "sentiment": 0, "impact": "neutral"}

        # sentiment
        s = TextBlob(h).sentiment.polarity
        entry["sentiment"] = s

        # entity recognition
        if nlp:
            doc = nlp(h)
            entry["entities"] = [(ent.text, ent.label_) for ent in doc.ents]

        # classify impact
        h_lower = h.lower()
        if any(word in h_lower for word in NEGATIVE_KEYWORDS) or s < -0.2:
            entry["impact"] = "negative"
        elif any(word in h_lower for word in POSITIVE_KEYWORDS) or s > 0.2:
            entry["impact"] = "positive"

        events.append(entry)

    return events


# -------------------------------
# Trend analysis (only from scores table)
# -------------------------------
def get_score_trend(ticker: str, days: int = 7):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        SELECT timestamp, final_score FROM scores
        WHERE ticker = ?
        ORDER BY timestamp DESC
        LIMIT ?
    """, (ticker, days))
    rows = cur.fetchall()
    con.close()

    if not rows:
        return {"trend": "no data", "change": 0, "history": []}

    scores = [r[1] for r in rows if r[1] is not None]
    if len(scores) < 2:
        return {"trend": "stable (insufficient data)", "change": 0, "history": scores}

    change = scores[0] - scores[-1]
    if change > 5:
        trend = f"📈 improving (+{change:.1f} points in {days} days)"
    elif change < -5:
        trend = f"📉 deteriorating ({change:.1f} points in {days} days)"
    else:
        trend = "➖ stable"

    return {"trend": trend, "change": change, "history": scores}


# -------------------------------
# Final blended explainable score
# -------------------------------
def explain_score(features: dict):
    ticker = features.get("ticker", "UNKNOWN")
    print(f"\n📊 Analyzing {ticker} ...")

    # Rule score
    rule_score, explanation = rule_based_score(features)
    print(f"📊 [ {ticker} ] Initial Rule-Based Score: {rule_score}")
    for e in explanation:
        print(f"   └ {e}")

    ml_score, shap_values = None, {}
    if ml_model:
        X = np.array([[features.get("change_1d", 0),
                       features.get("debt_to_equity", 0),
                       features.get("pe_ratio", 0),
                       features.get("market_cap", 0),
                       features.get("eps", 0),
                       features.get("book_value", 0),
                       features.get("news_sentiment", 0)]])
        ml_score = ml_model.predict(X)[0]
        ml_score = max(min(float(ml_score), 100), 0)
        print(f"\n🤖 ML Model Score: {ml_score:.2f}")

        # SHAP explanations
        explainer = shap.TreeExplainer(ml_model)
        shap_vals = explainer.shap_values(X)
        shap_values = dict(zip(
            ["change_1d", "debt_to_equity", "pe_ratio", "market_cap",
             "eps", "book_value", "news_sentiment"],
            shap_vals[0]
        ))
    else:
        print("\n🤖 ML Model Score: N/A (model not loaded)")

    # Blend scores
    final_score = rule_score
    if ml_score is not None:
        final_score = int(0.5 * rule_score + 0.5 * ml_score)

    # NLP Events
    events = detect_events(features.get("headlines", []))
    for e in events:
        if e["impact"] == "negative":
            print(f"📰 Event Detected: \"{e['headline']}\" → NEGATIVE → -10 points")
            final_score -= 10
        elif e["impact"] == "positive":
            print(f"📰 Event Detected: \"{e['headline']}\" → POSITIVE → +10 points")
            final_score += 10

    final_score = max(min(final_score, 100), 0)
    print(f"\n✅ Final Blended Score for {ticker} = {final_score} / 100")
    print("------------------------------------------------------")

    return {
        "rule_score": rule_score,
        "ml_score": ml_score,
        "final_score": final_score,
        "explanation": explanation,
        "ml_feature_importance": shap_values,
        "events": events
    }



# -------------------------------
# Test run
# -------------------------------
if __name__ == "__main__":
    f = build_features("TSLA")
    f["ticker"] = "TSLA"
    result = explain_score(f)
    print(result)
