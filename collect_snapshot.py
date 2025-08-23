# backend/collect_snapshot.py
import sys
from datetime import datetime, timezone
from dotenv import load_dotenv
load_dotenv()

from build_features import build_features
from model import explain_score
from data_store import ensure_schema, insert_snapshot, recent_count

def main():
    if len(sys.argv) < 2:
        print("Usage: python collect_snapshot.py <TICKER>")
        sys.exit(1)

    ticker = sys.argv[1].upper()

    ensure_schema()
    features = build_features(ticker)

    # ✅ ensure timestamp always exists
    features["ts"] = features.get("ts") or datetime.now(timezone.utc).isoformat()

    # rule-based score
    rule_score, explanation = explain_score(features)

    insert_snapshot(
        features,
        ticker,
        rule_score,
        ml_score=None,       # ML not yet
        final_score=rule_score
    )

    print(f"✅ snapshot stored for {ticker} @ {features['ts']}")
    print(f"   rule_score={rule_score} | headlines={len(features.get('headlines', []))}")
    print(f"   total rows in DB: {recent_count()}")

if __name__ == "__main__":
    main()
