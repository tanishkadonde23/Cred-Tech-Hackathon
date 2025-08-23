# backend/data_store.py
import sqlite3
from typing import Optional, Dict, Any

DB_PATH = "scores.db"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  ticker TEXT NOT NULL,
  change_1d REAL,
  debt_to_equity REAL,
  pe_ratio REAL,
  market_cap REAL,
  eps REAL,
  book_value REAL,
  news_sentiment REAL,
  rule_score REAL,
  ml_score REAL,
  final_score REAL
);
CREATE INDEX IF NOT EXISTS idx_snapshots_ticker_ts ON snapshots(ticker, ts);
"""

def ensure_schema(db_path: str = DB_PATH):
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        for stmt in SCHEMA_SQL.strip().split(";"):
            s = stmt.strip()
            if s:
                cur.execute(s)
        con.commit()
    finally:
        con.close()

def insert_snapshot(
    features: Dict[str, Any],
    ticker: str,
    rule_score: float,
    ml_score: Optional[float],
    final_score: float,
    db_path: str = DB_PATH,
):
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        cur.execute(
            """
            INSERT INTO snapshots
            (ts, ticker, change_1d, debt_to_equity, pe_ratio, market_cap, eps, book_value,
             news_sentiment, rule_score, ml_score, final_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                features.get("ts"),
                ticker,
                float(features.get("change_1d", 0) or 0),
                float(features.get("debt_to_equity", 0) or 0),
                float(features.get("pe_ratio", 0) or 0),
                float(features.get("market_cap", 0) or 0),
                float(features.get("eps", 0) or 0),
                float(features.get("book_value", 0) or 0),
                float(features.get("news_sentiment", 0) or 0),
                float(rule_score if rule_score is not None else 0),
                float(ml_score if ml_score is not None else 0),
                float(final_score if final_score is not None else rule_score),
            ),
        )
        con.commit()
    finally:
        con.close()

def recent_count(db_path: str = DB_PATH):
    con = sqlite3.connect(db_path)
    try:
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM snapshots")
        return cur.fetchone()[0]
    finally:
        con.close()
