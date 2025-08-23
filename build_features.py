# build_features.py
from fetch_data import get_stock_data_yahoo, get_stock_data_alpha, get_news_sentiment

def build_features(ticker: str) -> dict:
    """Fetch and merge features from Yahoo Finance, Alpha Vantage, and NewsAPI without DB dependency."""

    yahoo = {}
    alpha = {}
    news = {}

    try:
        yahoo = get_stock_data_yahoo(ticker) or {}
    except Exception as e:
        yahoo = {"error": str(e)}

    try:
        alpha = get_stock_data_alpha(ticker) or {}
    except Exception as e:
        alpha = {"error": str(e)}

    try:
        news = get_news_sentiment(ticker) or {}
    except Exception as e:
        news = {"error": str(e)}

    features = {
        # numeric features (safe defaults)
        "change_1d": float(yahoo.get("change_1d") or 0.0),
        "pe_ratio": float(yahoo.get("pe_ratio") or 0.0),
        "debt_to_equity": float(yahoo.get("debt_to_equity") or 0.0),
        "market_cap": float(alpha.get("market_cap") or 0.0),
        "eps": float(alpha.get("eps") or 0.0),
        "book_value": float(alpha.get("book_value") or 0.0),
        "news_sentiment": float(news.get("sentiment") or 0.0),

        # unstructured
        "headlines": news.get("headlines", []),

        # collect source errors for transparency
        "errors": {
            "yahoo": yahoo.get("error"),
            "alpha": alpha.get("error"),
            "news": news.get("error"),
        },
    }

    return features
