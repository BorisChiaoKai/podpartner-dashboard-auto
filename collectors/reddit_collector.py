"""
Reddit data collector for PODPartner Dashboard.

Searches Reddit for mentions of PODPartner and competitors across relevant subreddits.
Performs sentiment analysis on collected posts.

Required environment variables:
- REDDIT_CLIENT_ID: Reddit API client ID
- REDDIT_CLIENT_SECRET: Reddit API client secret
- REDDIT_USER_AGENT: User agent string for Reddit API requests
"""

import os
import praw
from datetime import datetime, timedelta
from collections import defaultdict
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
        print(f"[Reddit] Sentiment analysis error: {e}")
        return {"label": "neutral", "score": 5.0, "polarity": 0}


def collect():
    """
    Collect Reddit mentions and sentiment data.

    Returns:
        dict: Contains keys:
            - mentions: list of mention objects with title, body, author, subreddit, date, score, url, sentiment
            - platform_breakdown: dict with subreddit mention counts
            - daily_mention_counts: dict with date -> count mapping for last 30 days
            - total_mentions: int
            - collection_timestamp: ISO datetime string
    """

    print("[Reddit] Starting collection...")

    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    user_agent = os.environ.get("REDDIT_USER_AGENT", "PODPartner-Dashboard/1.0")

    if not client_id or not client_secret:
        print("[Reddit] Missing credentials (REDDIT_CLIENT_ID or REDDIT_CLIENT_SECRET)")
        return {
            "mentions": [],
            "platform_breakdown": {},
            "daily_mention_counts": {},
            "total_mentions": 0,
            "collection_timestamp": datetime.utcnow().isoformat(),
            "error": "Missing Reddit API credentials"
        }

    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent
        )

        # Test connection
        reddit.user.me()
        print("[Reddit] Authentication successful")

    except Exception as e:
        print(f"[Reddit] Authentication failed: {e}")
        return {
            "mentions": [],
            "platform_breakdown": {},
            "daily_mention_counts": {},
            "total_mentions": 0,
            "collection_timestamp": datetime.utcnow().isoformat(),
            "error": f"Authentication failed: {str(e)}"
        }

    # Keywords to search
    keywords = ["podpartner", "pod partner", "printful", "printify", "gelato", "tapstitch"]

    # Subreddits to monitor
    subreddits = ["printondemand", "ecommerce", "shopify", "Entrepreneur", "streetwearstartup"]

    mentions = []
    platform_breakdown = defaultdict(int)
    daily_mention_counts = defaultdict(int)

    # Initialize last 30 days with 0
    today = datetime.utcnow().date()
    for i in range(30):
        date = (today - timedelta(days=i)).isoformat()
        daily_mention_counts[date] = 0

    try:
        for subreddit_name in subreddits:
            print(f"[Reddit] Searching subreddit: {subreddit_name}")
            try:
                subreddit = reddit.subreddit(subreddit_name)

                # Search for each keyword
                for keyword in keywords:
                    try:
                        # Search with time filter for last month
                        submissions = subreddit.search(
                            keyword,
                            time_filter="month",
                            limit=25
                        )

                        for submission in submissions:
                            post_date = datetime.fromtimestamp(submission.created_utc).date()
                            post_date_iso = post_date.isoformat()

                            # Only count if within last 30 days
                            if post_date_iso in daily_mention_counts:
                                daily_mention_counts[post_date_iso] += 1

                            platform_breakdown[subreddit_name] += 1

                            # Combine title and body for sentiment
                            text_to_analyze = f"{submission.title} {submission.selftext}"
                            sentiment = _get_sentiment_score(text_to_analyze)

                            mention = {
                                "title": submission.title,
                                "body": submission.selftext[:500] if submission.selftext else "",  # Limit to 500 chars
                                "author": str(submission.author) if submission.author else "[deleted]",
                                "subreddit": subreddit_name,
                                "date": post_date_iso,
                                "score": submission.score,
                                "url": submission.url,
                                "sentiment": sentiment,
                                "keyword_found": keyword
                            }
                            mentions.append(mention)

                    except Exception as e:
                        print(f"[Reddit] Error searching '{keyword}' in {subreddit_name}: {e}")
                        continue

            except Exception as e:
                print(f"[Reddit] Error accessing subreddit {subreddit_name}: {e}")
                continue

        print(f"[Reddit] Collection complete. Found {len(mentions)} mentions")

        # Convert defaultdicts to regular dicts for JSON serialization
        return {
            "mentions": mentions,
            "platform_breakdown": dict(platform_breakdown),
            "daily_mention_counts": dict(daily_mention_counts),
            "total_mentions": len(mentions),
            "collection_timestamp": datetime.utcnow().isoformat(),
            "keywords_monitored": keywords,
            "subreddits_monitored": subreddits
        }

    except Exception as e:
        print(f"[Reddit] Collection failed: {e}")
        return {
            "mentions": mentions,
            "platform_breakdown": dict(platform_breakdown),
            "daily_mention_counts": dict(daily_mention_counts),
            "total_mentions": len(mentions),
            "collection_timestamp": datetime.utcnow().isoformat(),
            "error": f"Collection error: {str(e)}"
        }
