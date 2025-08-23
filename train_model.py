# backend/train_model.py
import sqlite3
import pandas as pd
import pickle
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_squared_error

DB_PATH = "scores.db"
MODEL_PATH = "ml_model.pkl"

def load_data(db_path=DB_PATH):
    """Load all snapshots from SQLite into a DataFrame."""
    con = sqlite3.connect(db_path)
    df = pd.read_sql("SELECT * FROM snapshots", con)
    con.close()
    return df

def train_ml_model():
    df = load_data()

    if len(df) < 20:
        raise ValueError(f"❌ Not enough rows in DB to train model. Have {len(df)}, need at least 20.")

    # Features (inputs) and Target (output)
    X = df[[
        "change_1d", "debt_to_equity", "pe_ratio",
        "market_cap", "eps", "book_value", "news_sentiment"
    ]]
    y = df["rule_score"]  # we use rule_score as proxy label

    # Split train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Train model
    model = RandomForestRegressor(n_estimators=200, random_state=42)
    model.fit(X_train, y_train)

    # Evaluate
    preds = model.predict(X_test)
    r2 = r2_score(y_test, preds)

    mse = mean_squared_error(y_test, preds)
    rmse = np.sqrt(mse)

    print(f"✅ Model trained: R²={r2:.3f}, RMSE={rmse:.2f}")

    # Save model
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)

    print(f"📦 Model saved to {MODEL_PATH}")

if __name__ == "__main__":
    train_ml_model()
