"""
Trustpilot review collector for PODPartner Dashboard.

Retrieves reviews for PODPartner from Trustpilot using public API and scraping.

Required environment variables:
None (uses public Trustpilot API endpoint)

Note: Trustpilot's API is subject to rate limiting. Consider implementing caching
if calling frequently.
"""

import os
import requests
from datetime import datetime
from textblob import TextBlob


def _get_sentiment_score(text):
    """
    Analyze sentiment of text using TextBlob.
    Returns dict with sentiment label and score (0-10).
    """
    try:
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity  # -1 to 1

        if polarity > 0.1:
            label = "positive"
        elif polarity < -0.1:
            label = "negative"
        else:
            label = "neutral"

        # Convert -1,1 scale to 0,10 scale
        score = round((polarity + 1) * 5, 2)

        return {
            "label": label,
            "score": score,
            "polarity": polarity
        }
    except Exception as e:
        print(f"[Trustpilot] Sentiment analysis error: {e}")
        return {"label": "neutral", "score": 5.0, "polarity": 0}


def collect():
    """
    Collect Trustpilot reviews for PODPartner.

    Returns:
        dict: Contains keys:
            - reviews: list of review objects with reviewer_name, date, rating, text, sentiment
            - average_rating: float (0-5)
            - total_reviews: int
            - rating_distribution: dict with rating -> count mapping
            - collection_timestamp: ISO datetime string
    """

    print("[Trustpilot] Starting collection...")

    try:
        # Trustpilot public API endpoint for PODPartner
        # Format: https://api.trustpilot.com/v1/businesses/BUSINESS_ID/reviews

        # First, search for PODPartner business
        search_url = "https://api.trustpilot.com/v1/search/businesses"
        search_params = {
            "query": "podpartner",
            "language": "en"
        }

        print("[Trustpilot] Searching for PODPartner business...")

        response = requests.get(
            search_url,
            params=search_params,
            timeout=10
        )

        if response.status_code != 200:
            print(f"[Trustpilot] Search failed with status {response.status_code}")
            return _get_empty_response(error=f"Search failed: {response.status_code}")

        data = response.json()
        businesses = data.get('results', [])

        if not businesses:
            print("[Trustpilot] No businesses found matching 'podpartner'")
            return _get_empty_response()

        # Get the first matching business
        business = businesses[0]
        business_id = business.get('id')
        business_name = business.get('name')

        print(f"[Trustpilot] Found business: {business_name} (ID: {business_id})")

        # Get reviews for this business
        reviews_url = f"https://api.trustpilot.com/v1/businesses/{business_id}/reviews"
        reviews_params = {
            "language": "en",
            "page_size": 100
        }

        print("[Trustpilot] Fetching reviews...")

        response = requests.get(
            reviews_url,
            params=reviews_params,
            timeout=10
        )

        if response.status_code != 200:
            print(f"[Trustpilot] Reviews fetch failed with status {response.status_code}")
            return _get_empty_response(error=f"Reviews fetch failed: {response.status_code}")

        data = response.json()
        reviews_list = data.get('reviews', [])

        print(f"[Trustpilot] Retrieved {len(reviews_list)} reviews")

        # Process reviews
        reviews = []
        rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        total_rating_points = 0

        for review in reviews_list:
            try:
                rating = int(review.get('rating', 0))
                reviewer_name = review.get('consumer', {}).get('displayName', 'Anonymous')
                review_text = review.get('content', '')
                published_date = review.get('publishedDateTime', '')

                # Parse date
                try:
                    date_obj = datetime.fromisoformat(published_date.replace('Z', '+00:00'))
                    review_date = date_obj.date().isoformat()
                except:
                    review_date = published_date[:10] if published_date else 'Unknown'

                # Sentiment analysis
                sentiment = _get_sentiment_score(review_text)

                review_obj = {
                    "reviewer_name": reviewer_name,
                    "date": review_date,
                    "rating": rating,
                    "text": review_text[:500] if review_text else "",  # Limit to 500 chars
                    "sentiment": sentiment,
                    "title": review.get('title', '')
                }
                reviews.append(review_obj)

                # Track rating distribution
                if rating in rating_distribution:
                    rating_distribution[rating] += 1
                total_rating_points += rating

            except Exception as e:
                print(f"[Trustpilot] Error processing review: {e}")
                continue

        # Calculate average rating
        average_rating = round(total_rating_points / len(reviews), 2) if reviews else 0

        print(f"[Trustpilot] Collection complete. Average rating: {average_rating}/5, Total: {len(reviews)} reviews")

        return {
            "reviews": reviews,
            "average_rating": average_rating,
            "total_reviews": len(reviews),
            "rating_distribution": rating_distribution,
            "collection_timestamp": datetime.utcnow().isoformat(),
            "business_name": business_name
        }

    except requests.exceptions.RequestException as e:
        print(f"[Trustpilot] Request error: {e}")
        return _get_empty_response(error=f"Request error: {str(e)}")
    except Exception as e:
        print(f"[Trustpilot] Collection failed: {e}")
        return _get_empty_response(error=f"Collection error: {str(e)}")


def _get_empty_response(error=None):
    """Return empty response structure when collection fails."""
    response = {
        "reviews": [],
        "average_rating": 0,
        "total_reviews": 0,
        "rating_distribution": {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
        "collection_timestamp": datetime.utcnow().isoformat()
    }

    if error:
        response["error"] = error

    return response
