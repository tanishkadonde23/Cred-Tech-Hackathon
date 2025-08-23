# fetch_data.py
import os
import yfinance as yf
import requests
from textblob import TextBlob
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

ALPHA_VANTAGE_KEY = os.getenv("ALPHA_VANTAGE_KEY", "")
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")

REQUEST_TIMEOUT = 8  # seconds


def get_stock_data_yahoo(ticker: str) -> dict:
    """Fetch daily change, PE, debt-to-equity from Yahoo Finance."""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5d")

        if len(hist) < 2:
            return {
                "close_price": None,
                "change_1d": 0.0,
                "pe_ratio": 0.0,
                "debt_to_equity": 0.0,
                "error": "Not enough price history"
            }

        close_price = float(hist["Close"].iloc[-1])
        prev_close = float(hist["Close"].iloc[-2])
        change_1d = ((close_price - prev_close) / prev_close) * 100.0

        info = stock.info or {}
        pe_ratio = float(info.get("forwardPE") or 0.0)
        debt_to_equity = float(info.get("debtToEquity") or 0.0)

        return {
            "close_price": round(close_price, 2),
            "change_1d": round(change_1d, 2),
            "pe_ratio": pe_ratio,
            "debt_to_equity": debt_to_equity,
            "error": None,
        }
    except Exception as e:
        return {
            "close_price": None,
            "change_1d": 0.0,
            "pe_ratio": 0.0,
            "debt_to_equity": 0.0,
            "error": f"Yahoo error: {e}",
        }


def get_stock_data_alpha(ticker: str) -> dict:
    """Fetch market cap, EPS, book value from Alpha Vantage OVERVIEW."""
    if not ALPHA_VANTAGE_KEY:
        return {"market_cap": 0.0, "eps": 0.0, "book_value": 0.0, "error": "Missing Alpha Vantage API key"}

    try:
        url = "https://www.alphavantage.co/query"
        params = {"function": "OVERVIEW", "symbol": ticker, "apikey": ALPHA_VANTAGE_KEY}
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        data = resp.json()

        # Common AV errors / rate limits
        if not isinstance(data, dict) or ("Symbol" not in data and "Note" in data):
            return {"market_cap": 0.0, "eps": 0.0, "book_value": 0.0, "error": data.get("Note", "Alpha Vantage returned no data")}

        market_cap = float(data.get("MarketCapitalization", 0) or 0)
        eps = float(data.get("EPS", 0) or 0)
        book_value = float(data.get("BookValue", 0) or 0)

        return {
            "market_cap": market_cap,
            "eps": eps,
            "book_value": book_value,
            "error": None,
        }
    except Exception as e:
        return {"market_cap": 0.0, "eps": 0.0, "book_value": 0.0, "error": f"Alpha error: {e}"}


def get_news_sentiment(query: str) -> dict:
    """Fetch recent headlines via NewsAPI and compute average TextBlob polarity."""
    if not NEWS_API_KEY:
        return {"headlines": [], "sentiment": 0.0, "error": "Missing NewsAPI key"}

    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 10,
            "apiKey": NEWS_API_KEY,
        }
        resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        data = resp.json()

        if "articles" not in data:
            return {"headlines": [], "sentiment": 0.0, "error": data.get("message", "NewsAPI returned no articles")}

        headlines = [a.get("title", "").strip() for a in data["articles"] if a.get("title")]
        headlines = [h for h in headlines if h]  # non-empty only

        sentiments = [TextBlob(h).sentiment.polarity for h in headlines]
        avg = round(sum(sentiments) / len(sentiments), 2) if sentiments else 0.0

        return {"headlines": headlines[:10], "sentiment": avg, "error": None}
    except Exception as e:
        return {"headlines": [], "sentiment": 0.0, "error": f"News error: {e}"}
