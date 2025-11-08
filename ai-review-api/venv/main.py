from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from utils.extract_id import extract_amazon_asin, extract_flipkart_pid
from scrapers.amazon_scraper import fetch_amazon_reviews
from scrapers.flipkart_scraper import fetch_flipkart_reviews
from textblob import TextBlob

app = FastAPI()

# Pydantic model for incoming request
class URLRequest(BaseModel):
    url: str

# Analyze Sentiment from review comment
def analyze_sentiment(comment: str):
    polarity = TextBlob(comment).sentiment.polarity
    if polarity > 0.2:
        return "positive"
    if polarity < -0.2:
        return "negative"
    return "neutral"

# Detect rating vs sentiment mismatch
def detect_mismatch(rating: float, sentiment: str):
    if sentiment == "positive" and rating <= 2.5:
        return True
    if sentiment == "negative" and rating >= 3.5:
        return True
    return False


@app.post("/fetch-reviews")
def get_reviews(data: URLRequest):
    url = data.url

    # Fetch platform wise data
    if "amazon" in url:
        asin = extract_amazon_asin(url)
        if not asin:
            raise HTTPException(status_code=400, detail="Invalid Amazon URL")
        reviews = fetch_amazon_reviews(asin)
        platform = "amazon"

    elif "flipkart" in url:
        pid = extract_flipkart_pid(url)
        if not pid:
            raise HTTPException(status_code=400, detail="Invalid Flipkart URL")
        reviews = fetch_flipkart_reviews(pid)
        platform = "flipkart"

    else:
        raise HTTPException(status_code=400, detail="Unsupported URL")

    processed_reviews = []
    sentiment_scores = []

    # Add AI Analysis for every review
    for r in reviews:
        sentiment = analyze_sentiment(r["comment"])
        mismatch = detect_mismatch(r["rating"], sentiment)

        processed_reviews.append({
            **r,
            "sentiment": sentiment,
            "mismatch": mismatch
        })

        sentiment_scores.append(TextBlob(r["comment"]).sentiment.polarity)

    # Compute sentiment summary
    average_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0.0
    mismatches_count = sum(1 for r in processed_reviews if r["mismatch"])

    return {
        "platform": platform,
        "total_reviews": len(processed_reviews),
        "average_sentiment": round(average_sentiment, 3),
        "mismatches_detected": mismatches_count,
        "reviews": processed_reviews
    }
