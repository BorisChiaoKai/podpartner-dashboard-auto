"""
Google Trends data collector for PODPartner Dashboard.

Retrieves interest over time and rising queries for PODPartner and related keywords.

Required environment variables:
None (pytrends uses public API)

Note: pytrends may require periodic updates as Google changes their Trends infrastructure.
If authentication fails, consider using selenium-based scraping as fallback.
"""

import os
from datetime import datetime, timedelta
from pytrends.request import TrendReq


def collect():
    """
    Collect Google Trends data.

    Returns:
        dict: Contains keys:
            - dates: list of ISO date strings (last 90 days)
            - keyword_data: dict with keyword -> list of interest values mapping
            - rising_queries: list of rising query objects with query, value, and keyword
            - collection_timestamp: ISO datetime string
    """

    print("[GoogleTrends] Starting collection...")

    keywords = ["podpartner", "print on demand", "printful", "printify", "tapstitch"]

    try:
        # Initialize pytrends with timeout and retries
        pytrends = TrendReq(hl='en-US', tz=360, timeout=(10, 25), retries=3)

        print("[GoogleTrends] Fetching interest over time...")

        # Get interest over time for last 90 days
        pytrends.build_payload(
            kw_list=keywords,
            cat=0,
            timeframe='today 3m',  # Last 3 months (90 days)
            geo='',
            gprop=''
        )

        interest_over_time = pytrends.interest_over_time()

        if interest_over_time.empty:
            print("[GoogleTrends] No data returned for interest over time")
            return _get_empty_response()

        # Extract dates (index) and convert to ISO format
        dates = [date.strftime('%Y-%m-%d') for date in interest_over_time.index]

        # Build keyword data dict (excluding 'isPartial' column)
        keyword_data = {}
        for keyword in keywords:
            if keyword in interest_over_time.columns:
                keyword_data[keyword] = interest_over_time[keyword].tolist()
            else:
                keyword_data[keyword] = [0] * len(dates)

        print(f"[GoogleTrends] Retrieved {len(dates)} days of trend data")

        # Get rising queries for each keyword
        rising_queries = []

        for keyword in keywords:
            try:
                print(f"[GoogleTrends] Fetching rising queries for '{keyword}'...")

                pytrends.build_payload(
                    kw_list=[keyword],
                    cat=0,
                    timeframe='today 1m',  # Last month for rising queries
                    geo='',
                    gprop=''
                )

                rising_data = pytrends.related_queries()

                if rising_data and keyword in rising_data:
                    rising_df = rising_data[keyword]['rising']

                    if rising_df is not None and not rising_df.empty:
                        for idx, row in rising_df.iterrows():
                            rising_queries.append({
                                "keyword": keyword,
                                "query": row['query'],
                                "value": int(row['value'])  # Rising value (0-100 scale)
                            })
                        print(f"[GoogleTrends] Found {len(rising_df)} rising queries for '{keyword}'")

            except Exception as e:
                print(f"[GoogleTrends] Error fetching rising queries for '{keyword}': {e}")
                continue

        # Sort rising queries by value (descending)
        rising_queries = sorted(rising_queries, key=lambda x: x['value'], reverse=True)

        print(f"[GoogleTrends] Collection complete. Total rising queries: {len(rising_queries)}")

        return {
            "dates": dates,
            "keyword_data": keyword_data,
            "rising_queries": rising_queries,
            "collection_timestamp": datetime.utcnow().isoformat(),
            "keywords_monitored": keywords,
            "timeframe": "90 days interest, 30 days rising queries"
        }

    except Exception as e:
        print(f"[GoogleTrends] Collection failed: {e}")
        return _get_empty_response(error=f"Collection error: {str(e)}")


def _get_empty_response(error=None):
    """Return empty response structure when collection fails."""
    # Generate empty dates for last 90 days
    today = datetime.utcnow().date()
    dates = [(today - timedelta(days=i)).isoformat() for i in range(89, -1, -1)]

    keywords = ["podpartner", "print on demand", "printful", "printify", "tapstitch"]
    keyword_data = {kw: [0] * len(dates) for kw in keywords}

    response = {
        "dates": dates,
        "keyword_data": keyword_data,
        "rising_queries": [],
        "collection_timestamp": datetime.utcnow().isoformat(),
        "keywords_monitored": keywords
    }

    if error:
        response["error"] = error

    return response
