# app.py
from flask import Flask, request, jsonify, render_template
from build_features import build_features
from model import explain_score
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON, inspect, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import pickle
import os
import nltk

# Download punkt if not already available
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')

# ✅ Tell Flask where templates + static files are
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

# ----------------- Database Setup -----------------
engine = create_engine("sqlite:///scores.db", echo=False)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

class ScoreRecord(Base):
    __tablename__ = "scores"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    rule_score = Column(Integer)
    ml_score = Column(Float, nullable=True)
    final_score = Column(Float, nullable=True)
    features = Column(JSON)
    explanation = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)

def ensure_schema():
    insp = inspect(engine)
    if "scores" in insp.get_table_names():
        cols = [c["name"] for c in insp.get_columns("scores")]
        needed = {"rule_score", "ml_score", "final_score"}
        if not needed.issubset(cols):
            print("⚠️ Old schema detected. Dropping and recreating 'scores' table...")
            with engine.begin() as conn:
                conn.execute(text("DROP TABLE IF EXISTS scores"))
            Base.metadata.create_all(bind=engine)
            print("✅ Table rebuilt with new schema.")
        else:
            print("✅ DB schema is up to date.")
    else:
        Base.metadata.create_all(bind=engine)
        print("✅ Fresh table created.")

ensure_schema()
# --------------------------------------------------

# ✅ Load ML model (inside /backend, so no "backend/")
try:
    with open("ml_model.pkl", "rb") as f:
        ml_model = pickle.load(f)
    ml_model_loaded = True
    print("✅ ML model loaded successfully")
except Exception as e:
    print(f"⚠️ Could not load ML model: {e}")
    ml_model = None
    ml_model_loaded = False

latest_scores = {}

# ----------------- FRONTEND -----------------
@app.route("/", methods=["GET"])
def explorer_page():
    return render_template("main.html")

@app.route("/dashboard", methods=["GET"])
def home_page():
    return render_template("index.html")

@app.route("/graphs/<ticker>", methods=["GET"])
def graphs_page(ticker):
    return render_template("graphs.html", ticker=ticker)

# ----------------- API Routes -----------------
@app.route("/predict", methods=["POST"])
def predict():
    try:
        data = request.json
        tickers = data.get("tickers") or data.get("ticker")

        if not tickers:
            return jsonify({"error": "Please provide at least one ticker symbol"}), 400

        if isinstance(tickers, str):
            tickers = [tickers]

        results = []
        db = SessionLocal()
        for ticker in tickers:
            features = build_features(ticker)
            features["ticker"] = ticker  # important for explain_score

            result = explain_score(features)

            record = ScoreRecord(
                ticker=ticker,
                rule_score=result["rule_score"],
                ml_score=result["ml_score"],
                final_score=result["final_score"],
                features=features,
                explanation=result["explanation"]
            )
            db.add(record)
            db.commit()

            results.append(result)
        db.close()

        return jsonify({"results": results})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/latest", methods=["GET"])
def get_latest():
    return jsonify(latest_scores)

@app.route("/history/<ticker>", methods=["GET"])
def get_history(ticker):
    db = SessionLocal()
    records = db.query(ScoreRecord).filter(ScoreRecord.ticker == ticker).order_by(ScoreRecord.timestamp.desc()).limit(10).all()
    db.close()
    return jsonify([
        {
            "ticker": r.ticker,
            "rule_score": r.rule_score,
            "ml_score": r.ml_score,
            "final_score": r.final_score,
            "features": r.features,
            "explanation": r.explanation,
            "timestamp": r.timestamp.isoformat()
        } for r in records
    ])

# ----------------- Scheduler -----------------
def refresh_scores():
    tickers_to_track = ["TSLA", "AAPL", "MSFT"]
    global latest_scores
    db = SessionLocal()
    for ticker in tickers_to_track:
        try:
            features = build_features(ticker)
            features["ticker"] = ticker
            result = explain_score(features)

            latest_scores[ticker] = {
                "rule_score": result["rule_score"],
                "ml_score": result["ml_score"],
                "final_score": result["final_score"],
                "features": features,
                "explanation": result["explanation"],
                "timestamp": datetime.utcnow().isoformat()
            }

            record = ScoreRecord(
                ticker=ticker,
                rule_score=result["rule_score"],
                ml_score=result["ml_score"],
                final_score=result["final_score"],
                features=features,
                explanation=result["explanation"]
            )
            db.add(record)
            db.commit()

            print(f"[Scheduler] Updated {ticker}: rule={result['rule_score']}, ml={result['ml_score']}, final={result['final_score']}")
        except Exception as e:
            print(f"[Scheduler] Error updating {ticker}: {e}")
    db.close()

scheduler = BackgroundScheduler()
scheduler.add_job(func=refresh_scores, trigger="interval", minutes=10)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

# ----------------- Run -----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Railway provides PORT
    app.run(host="0.0.0.0", port=port, debug=True)
