"""
Configuration for PodPartner Dashboard Auto-Update Pipeline
"""

# Brand and competitor keywords
KEYWORDS = ["podpartner", "pod partner"]
COMPETITORS = ["printful", "printify", "gelato", "tapstitch"]

# Subreddit monitoring
SUBREDDITS = [
    "printondemand",
    "ecommerce",
    "shopify",
    "Entrepreneur",
    "streetwearstartup",
]

# Data collection windows
DATA_WINDOW_DAYS = 30  # How many days back to collect data
TRENDS_WINDOW_DAYS = 90  # Google Trends window

# Topics to track (extracted from mention text)
TRACKED_TOPICS = [
    "product quality",
    "customization",
    "shipping",
    "customer service",
    "pricing",
    "platform integration",
    "embroidery",
]

# Sentiment thresholds
SENTIMENT_POSITIVE_THRESHOLD = 0.1  # TextBlob polarity threshold
SENTIMENT_NEGATIVE_THRESHOLD = -0.1

# Data sources to include
ENABLED_COLLECTORS = {
    "reddit": True,
    "google_trends": True,
    "meta_ads": True,
    "youtube": True,
    "trustpilot": True,
}

# Velocity calculation
VELOCITY_WINDOW_DAYS = 7  # Last N days for velocity calculation

# Action item triggers
ACTION_TRIGGERS = {
    "negative_sentiment_spike": 0.15,  # 15% increase in negative mentions
    "declining_mentions": 0.20,  # 20% decline week-over-week
    "high_negative_pct": 0.35,  # More than 35% negative mentions
}

# Output configuration
OUTPUT_DIR = "output"
DATA_DIR = "data"
TEMPLATE_DIR = "templates"
HISTORY_FILE = "data/history.json"

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = "dashboard-auto.log"
