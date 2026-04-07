"""
Main build script for PodPartner Dashboard auto-update pipeline
Aggregates data from all collectors and renders the dashboard
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Tuple

from jinja2 import Environment, FileSystemLoader
import statistics

from config import (
    KEYWORDS,
    COMPETITORS,
    DATA_WINDOW_DAYS,
    TRACKED_TOPICS,
    SENTIMENT_POSITIVE_THRESHOLD,
    SENTIMENT_NEGATIVE_THRESHOLD,
    VELOCITY_WINDOW_DAYS,
    ACTION_TRIGGERS,
    OUTPUT_DIR,
    DATA_DIR,
    TEMPLATE_DIR,
    HISTORY_FILE,
    LOG_LEVEL,
    LOG_FILE,
    ENABLED_COLLECTORS,
)

# Setup logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class DashboardBuilder:
    """Orchestrates data collection, aggregation, and rendering"""

    def __init__(self):
        self.data = {}
        self.history = []
        self.report_date = datetime.now()

    def load_history(self) -> List[Dict]:
        """Load historical data from previous runs"""
        if not os.path.exists(HISTORY_FILE):
            logger.info(f"No history file found at {HISTORY_FILE}, starting fresh")
            return []

        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading history file: {e}")
            return []

    def save_history(self, history: List[Dict]):
        """Save aggregated stats to history file"""
        Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
        try:
            with open(HISTORY_FILE, "w") as f:
                json.dump(history, f, indent=2, default=str)
            logger.info(f"Saved history to {HISTORY_FILE}")
        except Exception as e:
            logger.error(f"Error saving history: {e}")

    def collect_reddit_data(self) -> Dict:
        """Collect data from Reddit collector"""
        if not ENABLED_COLLECTORS.get("reddit", True):
            return self._empty_reddit_data()

        try:
            from collectors.reddit_collector import RedditCollector
            collector = RedditCollector()
            data = collector.collect()
            logger.info(f"Collected {len(data.get('mentions', []))} mentions from Reddit")
            return data
        except Exception as e:
            logger.error(f"Reddit collection failed: {e}")
            return self._empty_reddit_data()

    def collect_google_trends(self) -> Dict:
        """Collect data from Google Trends"""
        if not ENABLED_COLLECTORS.get("google_trends", True):
            return self._empty_trends_data()

        try:
            from collectors.trends_collector import TrendsCollector
            collector = TrendsCollector()
            data = collector.collect()
            logger.info(f"Collected Google Trends data")
            return data
        except Exception as e:
            logger.error(f"Google Trends collection failed: {e}")
            return self._empty_trends_data()

    def collect_meta_ads(self) -> Dict:
        """Collect data from Meta Ads API"""
        if not ENABLED_COLLECTORS.get("meta_ads", True):
            return self._empty_meta_data()

        try:
            from collectors.meta_ads_collector import MetaAdsCollector
            collector = MetaAdsCollector()
            data = collector.collect()
            logger.info(f"Collected Meta Ads data")
            return data
        except Exception as e:
            logger.error(f"Meta Ads collection failed: {e}")
            return self._empty_meta_data()

    def collect_youtube(self) -> Dict:
        """Collect data from YouTube"""
        if not ENABLED_COLLECTORS.get("youtube", True):
            return self._empty_youtube_data()

        try:
            from collectors.youtube_collector import YouTubeCollector
            collector = YouTubeCollector()
            data = collector.collect()
            logger.info(f"Collected YouTube data")
            return data
        except Exception as e:
            logger.error(f"YouTube collection failed: {e}")
            return self._empty_youtube_data()

    def collect_trustpilot(self) -> Dict:
        """Collect data from Trustpilot"""
        if not ENABLED_COLLECTORS.get("trustpilot", True):
            return self._empty_trustpilot_data()

        try:
            from collectors.trustpilot_collector import TrustpilotCollector
            collector = TrustpilotCollector()
            data = collector.collect()
            logger.info(f"Collected Trustpilot data")
            return data
        except Exception as e:
            logger.error(f"Trustpilot collection failed: {e}")
            return self._empty_trustpilot_data()

    def _empty_reddit_data(self) -> Dict:
        """Fallback empty Reddit data"""
        return {
            "mentions": [],
            "platform": "Reddit",
            "data_points": 0,
        }

    def _empty_trends_data(self) -> Dict:
        """Fallback empty Trends data"""
        return {
            "raw": {"dates": [], "keywords": {}},
            "rising": [],
            "platform": "Google Trends",
            "data_points": 0,
        }

    def _empty_meta_data(self) -> Dict:
        """Fallback empty Meta data"""
        return {
            "daily": [],
            "campaigns": [],
            "platform": "Meta Ads",
            "metrics": {
                "total_spend": 0,
                "purchases": 0,
                "cpa": 0,
                "roas": 0,
                "ctr": 0,
            },
            "data_points": 0,
        }

    def _empty_youtube_data(self) -> Dict:
        """Fallback empty YouTube data"""
        return {
            "mentions": [],
            "platform": "YouTube",
            "data_points": 0,
        }

    def _empty_trustpilot_data(self) -> Dict:
        """Fallback empty Trustpilot data"""
        return {
            "feedback": [],
            "platform": "Trustpilot",
            "data_points": 0,
        }

    def aggregate_data(self, reddit: Dict, trends: Dict, meta: Dict,
                      youtube: Dict, trustpilot: Dict) -> Dict:
        """Aggregate all collector data into dashboard_data structure"""

        # Extract mentions from all sources
        all_mentions = []
        all_mentions.extend(reddit.get("mentions", []))
        all_mentions.extend(youtube.get("mentions", []))

        # Build mention platform breakdown
        platform_stats = self._calculate_platform_stats(all_mentions)

        # Calculate sentiment metrics
        sentiment_metrics = self._calculate_sentiment_metrics(all_mentions)

        # Calculate mention trend (last 30 days)
        mention_trend = self._calculate_mention_trend(all_mentions)

        # Calculate sentiment trajectory
        sentiment_traj = self._calculate_sentiment_trajectory(all_mentions)

        # Calculate velocity
        velocity = self._calculate_velocity(all_mentions)

        # Calculate share of voice
        share_of_voice = self._calculate_share_of_voice(all_mentions)

        # Extract topics from mentions
        topics = self._extract_topics(all_mentions)

        # Get week-over-week changes
        wow_changes = self._calculate_wow_changes(all_mentions)

        # Generate action items
        action_items = self._generate_action_items(
            sentiment_metrics, wow_changes, all_mentions
        )

        # Get historical data for charts
        history_data = self._calculate_history_data()

        # Get competitor data
        competitors_data = self._get_competitors_data(all_mentions)

        # Extract feedback items for the testimonial carousel
        feedback_items = self._extract_feedback_items(all_mentions, trustpilot)

        # Build Meta data section
        meta_data = self._process_meta_data(meta)

        # Build Trends data section
        trends_data = self._process_trends_data(trends)

        # Calculate derived metrics
        total_mentions = len(all_mentions)
        mentions_change = wow_changes.get("mentions_change_pct", 0)

        # Build dashboard data structure
        dashboard_data = {
            # Metadata
            "report_date": self.report_date.strftime("%Y-%m-%d %H:%M:%S"),
            "data_sources": self._get_data_sources(reddit, trends, meta, youtube, trustpilot),

            # Key metrics
            "total_mentions": total_mentions,
            "mentions_change": mentions_change,
            "sentiment_score": sentiment_metrics["overall_score"],
            "sentiment_change": sentiment_metrics["sentiment_change"],
            "mention_velocity": velocity["mentions_per_day"],
            "velocity_change": velocity["velocity_change_pct"],
            "share_of_voice": share_of_voice,

            # Sentiment breakdown
            "positive_pct": sentiment_metrics["positive_pct"],
            "positive_count": sentiment_metrics["positive_count"],
            "neutral_pct": sentiment_metrics["neutral_pct"],
            "neutral_count": sentiment_metrics["neutral_count"],
            "negative_pct": sentiment_metrics["negative_pct"],
            "negative_count": sentiment_metrics["negative_count"],

            # Action items
            "action_items_count": len(action_items),
            "high_priority_count": sum(1 for a in action_items if a["priority"] == "high"),
            "action_items": action_items,

            # Mention trend chart
            "mention_trend_labels": mention_trend["labels"],
            "mention_trend_data": mention_trend["data"],

            # Sentiment trajectory chart
            "sentiment_trajectory_data": sentiment_traj,

            # Historical runs chart
            "history_labels": history_data["labels"],
            "history_mentions": history_data["mentions"],
            "history_positive_pct": history_data["positive_pct"],

            # Platform breakdown
            "platform_labels": platform_stats["labels"],
            "platform_data": platform_stats["data"],
            "platform_colors": platform_stats["colors"],

            # Platform sentiment breakdown
            "sentiment_platform_labels": platform_stats["platform_labels"],
            "sentiment_platform_positive": platform_stats["positive"],
            "sentiment_platform_neutral": platform_stats["neutral"],
            "sentiment_platform_negative": platform_stats["negative"],

            # Topics
            "topic_labels": [t["name"] for t in topics],
            "topic_data": [t["mentions"] for t in topics],
            "topics": topics,

            # Google Trends
            "gt_raw": trends_data["raw"],
            "gt_rising": trends_data["rising"],

            # Meta Ads
            "meta_daily": meta_data["daily"],
            "meta_campaigns": meta_data["campaigns"],
            "meta_total_spend": meta_data["total_spend"],
            "meta_purchases": meta_data["purchases"],
            "meta_cpa": meta_data["cpa"],
            "meta_roas": meta_data["roas"],
            "meta_ctr": meta_data["ctr"],

            # Feedback items
            "feedback_items": feedback_items,

            # Competitors
            "competitors": competitors_data,
        }

        return dashboard_data

    def _get_data_sources(self, reddit, trends, meta, youtube, trustpilot) -> List[str]:
        """Build list of active data sources"""
        sources = []
        if reddit.get("data_points", 0) > 0:
            sources.append("Reddit")
        if trends.get("data_points", 0) > 0:
            sources.append("Google Trends")
        if meta.get("data_points", 0) > 0:
            sources.append("Meta Ads")
        if youtube.get("data_points", 0) > 0:
            sources.append("YouTube")
        if trustpilot.get("data_points", 0) > 0:
            sources.append("Trustpilot")
        return sources

    def _calculate_platform_stats(self, mentions: List[Dict]) -> Dict:
        """Calculate per-platform statistics"""
        platform_counts = {}
        platform_sentiments = {}

        for mention in mentions:
            platform = mention.get("platform", "Unknown")
            sentiment = mention.get("sentiment", 0)

            if platform not in platform_counts:
                platform_counts[platform] = 0
                platform_sentiments[platform] = {"positive": 0, "neutral": 0, "negative": 0}

            platform_counts[platform] += 1

            # Categorize sentiment
            if sentiment > SENTIMENT_POSITIVE_THRESHOLD:
                platform_sentiments[platform]["positive"] += 1
            elif sentiment < SENTIMENT_NEGATIVE_THRESHOLD:
                platform_sentiments[platform]["negative"] += 1
            else:
                platform_sentiments[platform]["neutral"] += 1

        # Define colors for each platform
        colors = {
            "Reddit": "#FF4500",
            "YouTube": "#FF0000",
            "Meta": "#1877F2",
            "Trustpilot": "#00B800",
            "Google Trends": "#4285F4",
        }

        return {
            "labels": list(platform_counts.keys()),
            "data": list(platform_counts.values()),
            "colors": [colors.get(p, "#999999") for p in platform_counts.keys()],
            "platform_labels": list(platform_sentiments.keys()),
            "positive": [platform_sentiments[p]["positive"] for p in platform_sentiments.keys()],
            "neutral": [platform_sentiments[p]["neutral"] for p in platform_sentiments.keys()],
            "negative": [platform_sentiments[p]["negative"] for p in platform_sentiments.keys()],
        }

    def _calculate_sentiment_metrics(self, mentions: List[Dict]) -> Dict:
        """Calculate overall sentiment metrics"""
        if not mentions:
            return {
                "overall_score": 0,
                "sentiment_change": 0,
                "positive_pct": 0,
                "positive_count": 0,
                "neutral_pct": 0,
                "neutral_count": 0,
                "negative_pct": 0,
                "negative_count": 0,
            }

        sentiments = []
        positive_count = 0
        neutral_count = 0
        negative_count = 0

        for mention in mentions:
            sentiment = mention.get("sentiment", 0)
            sentiments.append(sentiment)

            if sentiment > SENTIMENT_POSITIVE_THRESHOLD:
                positive_count += 1
            elif sentiment < SENTIMENT_NEGATIVE_THRESHOLD:
                negative_count += 1
            else:
                neutral_count += 1

        total = len(mentions)
        overall_score = statistics.mean(sentiments) if sentiments else 0

        return {
            "overall_score": round(overall_score, 3),
            "sentiment_change": 0,  # Would need previous data
            "positive_pct": round((positive_count / total) * 100, 1),
            "positive_count": positive_count,
            "neutral_pct": round((neutral_count / total) * 100, 1),
            "neutral_count": neutral_count,
            "negative_pct": round((negative_count / total) * 100, 1),
            "negative_count": negative_count,
        }

    def _calculate_mention_trend(self, mentions: List[Dict]) -> Dict:
        """Calculate mentions over the last N days"""
        labels = []
        data = []

        # Create daily buckets for the last 30 days
        for days_ago in range(DATA_WINDOW_DAYS - 1, -1, -1):
            date = (self.report_date - timedelta(days=days_ago)).date()
            labels.append(date.strftime("%m-%d"))

            day_mentions = sum(
                1 for m in mentions
                if m.get("date", "").startswith(str(date))
            )
            data.append(day_mentions)

        return {
            "labels": labels,
            "data": data,
        }

    def _calculate_sentiment_trajectory(self, mentions: List[Dict]) -> List[Dict]:
        """Calculate sentiment trend over time"""
        sentiment_by_day = {}

        for mention in mentions:
            mention_date = mention.get("date", "")[:10]
            sentiment = mention.get("sentiment", 0)

            if mention_date not in sentiment_by_day:
                sentiment_by_day[mention_date] = []
            sentiment_by_day[mention_date].append(sentiment)

        # Build trajectory
        trajectory = []
        for days_ago in range(DATA_WINDOW_DAYS - 1, -1, -1):
            date = (self.report_date - timedelta(days=days_ago)).date()
            date_str = str(date)

            if date_str in sentiment_by_day:
                avg_sentiment = statistics.mean(sentiment_by_day[date_str])
                trajectory.append({
                    "date": date.strftime("%m-%d"),
                    "value": round(avg_sentiment, 3),
                })

        return trajectory

    def _calculate_velocity(self, mentions: List[Dict]) -> Dict:
        """Calculate mention velocity (mentions per day)"""
        recent_mentions = []
        cutoff_date = self.report_date - timedelta(days=VELOCITY_WINDOW_DAYS)

        for mention in mentions:
            mention_date = datetime.fromisoformat(mention.get("date", "").replace("Z", "+00:00"))
            if mention_date >= cutoff_date:
                recent_mentions.append(mention)

        velocity = len(recent_mentions) / VELOCITY_WINDOW_DAYS if recent_mentions else 0

        return {
            "mentions_per_day": round(velocity, 2),
            "velocity_change_pct": 0,  # Would need previous data
        }

    def _calculate_share_of_voice(self, mentions: List[Dict]) -> float:
        """Calculate share of voice vs competitors"""
        brand_mentions = sum(
            1 for m in mentions
            if any(k.lower() in m.get("text", "").lower() for k in KEYWORDS)
        )

        total_mentions = len(mentions)

        if total_mentions == 0:
            return 0

        return round((brand_mentions / total_mentions) * 100, 1)

    def _extract_topics(self, mentions: List[Dict]) -> List[Dict]:
        """Extract topics from mention text"""
        topic_stats = {topic: {"mentions": 0, "positive": 0} for topic in TRACKED_TOPICS}

        for mention in mentions:
            text = mention.get("text", "").lower()
            sentiment = mention.get("sentiment", 0)

            for topic in TRACKED_TOPICS:
                if topic.lower() in text:
                    topic_stats[topic]["mentions"] += 1
                    if sentiment > SENTIMENT_POSITIVE_THRESHOLD:
                        topic_stats[topic]["positive"] += 1

        # Build topic list sorted by mention count
        topics = []
        for topic, stats in sorted(
            topic_stats.items(),
            key=lambda x: x[1]["mentions"],
            reverse=True
        ):
            if stats["mentions"] > 0:
                positive_pct = round(
                    (stats["positive"] / stats["mentions"]) * 100, 1
                )
                topics.append({
                    "name": topic.title(),
                    "mentions": stats["mentions"],
                    "positive_pct": positive_pct,
                })

        return topics

    def _calculate_wow_changes(self, mentions: List[Dict]) -> Dict:
        """Calculate week-over-week changes"""
        # This would require historical data; for now return placeholder
        return {
            "mentions_change_pct": 0,
            "sentiment_change_pct": 0,
        }

    def _generate_action_items(self, sentiment: Dict, wow: Dict,
                              mentions: List[Dict]) -> List[Dict]:
        """Generate action items based on trends"""
        action_items = []

        # Check for high negative sentiment
        if sentiment["negative_pct"] > ACTION_TRIGGERS["high_negative_pct"] * 100:
            action_items.append({
                "priority": "high",
                "title": "Address High Negative Sentiment",
                "description": f"Currently {sentiment['negative_pct']}% of mentions are negative. Investigate root causes and create response strategy.",
                "source": "Sentiment Analysis",
            })

        # Check for declining mentions
        mentions_change = wow.get("mentions_change_pct", 0)
        if mentions_change < -ACTION_TRIGGERS["declining_mentions"] * 100:
            action_items.append({
                "priority": "medium",
                "title": "Declining Brand Mentions",
                "description": f"Mentions declined {abs(mentions_change):.1f}% week-over-week. Review marketing activities and engagement strategy.",
                "source": "Mention Velocity",
            })

        # Check for negative sentiment spike
        sentiment_change = sentiment.get("sentiment_change", 0)
        if sentiment_change < -ACTION_TRIGGERS["negative_sentiment_spike"] * 100:
            action_items.append({
                "priority": "high",
                "title": "Negative Sentiment Spike Detected",
                "description": "Sentiment has declined significantly. Monitor conversations and prepare response.",
                "source": "Sentiment Trajectory",
            })

        # Always include at least one default action
        if not action_items:
            action_items.append({
                "priority": "low",
                "title": "Monitor Performance",
                "description": "Continue monitoring brand mentions and sentiment across all platforms.",
                "source": "System",
            })

        return action_items

    def _calculate_history_data(self) -> Dict:
        """Get historical data for multi-run charts"""
        history = self.load_history()

        labels = [h.get("date", "")[:10] for h in history[-30:]]
        mentions = [h.get("mentions", 0) for h in history[-30:]]
        positive_pct = [h.get("positive_pct", 0) for h in history[-30:]]

        return {
            "labels": labels,
            "mentions": mentions,
            "positive_pct": positive_pct,
        }

    def _get_competitors_data(self, mentions: List[Dict]) -> List[Dict]:
        """Extract competitor data"""
        competitors = []

        colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A"]

        for idx, competitor in enumerate(COMPETITORS):
            comp_mentions = sum(
                1 for m in mentions
                if competitor.lower() in m.get("text", "").lower()
            )

            # Get sentiment for competitor mentions
            comp_sentiment_scores = [
                m.get("sentiment", 0) for m in mentions
                if competitor.lower() in m.get("text", "").lower()
            ]

            comp_sentiment = (
                statistics.mean(comp_sentiment_scores)
                if comp_sentiment_scores else 0
            )

            comp_positive = sum(
                1 for s in comp_sentiment_scores
                if s > SENTIMENT_POSITIVE_THRESHOLD
            )

            comp_positive_pct = (
                round((comp_positive / len(comp_sentiment_scores)) * 100, 1)
                if comp_sentiment_scores else 0
            )

            competitors.append({
                "name": competitor.title(),
                "color": colors[idx % len(colors)],
                "mentions": comp_mentions,
                "sov": round((comp_mentions / len(mentions)) * 100, 1) if mentions else 0,
                "sentiment_score": round(comp_sentiment, 3),
                "positive_pct": comp_positive_pct,
            })

        return sorted(competitors, key=lambda x: x["mentions"], reverse=True)

    def _extract_feedback_items(self, mentions: List[Dict], trustpilot: Dict) -> List[Dict]:
        """Extract feedback items for carousel"""
        feedback = []

        # Get top mentions from trustpilot
        for item in trustpilot.get("feedback", [])[:5]:
            feedback.append({
                "avatar": "👤",
                "name": item.get("author", "Anonymous"),
                "platform": "Trustpilot",
                "date": item.get("date", ""),
                "text": item.get("text", ""),
                "sentiment": "positive" if item.get("rating", 3) >= 4 else "negative",
            })

        # Get top positive mentions from other sources
        positive_mentions = [m for m in mentions if m.get("sentiment", 0) > SENTIMENT_POSITIVE_THRESHOLD]
        for mention in positive_mentions[:3]:
            feedback.append({
                "avatar": "📱" if mention.get("platform") == "Reddit" else "▶",
                "name": mention.get("author", "User"),
                "platform": mention.get("platform", "Unknown"),
                "date": mention.get("date", "")[:10],
                "text": mention.get("text", "")[:150],
                "sentiment": "positive",
            })

        return feedback

    def _process_meta_data(self, meta: Dict) -> Dict:
        """Process Meta Ads data"""
        return {
            "daily": meta.get("daily", []),
            "campaigns": meta.get("campaigns", []),
            "total_spend": meta.get("metrics", {}).get("total_spend", 0),
            "purchases": meta.get("metrics", {}).get("purchases", 0),
            "cpa": meta.get("metrics", {}).get("cpa", 0),
            "roas": meta.get("metrics", {}).get("roas", 0),
            "ctr": meta.get("metrics", {}).get("ctr", 0),
        }

    def _process_trends_data(self, trends: Dict) -> Dict:
        """Process Google Trends data"""
        return {
            "raw": trends.get("raw", {"dates": [], "keywords": {}}),
            "rising": trends.get("rising", []),
        }

    def render_template(self, dashboard_data: Dict, template_name: str = "dashboard.html"):
        """Render Jinja2 template with dashboard data"""
        try:
            env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
            template = env.get_template(template_name)

            html_content = template.render(**dashboard_data)

            # Ensure output directory exists
            Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

            output_path = os.path.join(OUTPUT_DIR, "index.html")
            with open(output_path, "w") as f:
                f.write(html_content)

            logger.info(f"Dashboard rendered to {output_path}")
            return output_path
        except Exception as e:
            logger.error(f"Template rendering failed: {e}")
            raise

    def save_aggregate_stats(self, dashboard_data: Dict):
        """Save aggregate stats to history for multi-run tracking"""
        history = self.load_history()

        # Append current run's stats
        stats = {
            "date": self.report_date.isoformat(),
            "mentions": dashboard_data.get("total_mentions", 0),
            "positive_pct": dashboard_data.get("positive_pct", 0),
            "sentiment_score": dashboard_data.get("sentiment_score", 0),
        }

        history.append(stats)

        # Keep last 90 days of data
        cutoff_date = self.report_date - timedelta(days=90)
        history = [
            h for h in history
            if datetime.fromisoformat(h.get("date", "")) >= cutoff_date
        ]

        self.save_history(history)

    def build(self):
        """Execute the full build pipeline"""
        logger.info("Starting dashboard build...")

        try:
            # Collect data from all sources
            logger.info("Collecting data from all sources...")
            reddit_data = self.collect_reddit_data()
            trends_data = self.collect_google_trends()
            meta_data = self.collect_meta_ads()
            youtube_data = self.collect_youtube()
            trustpilot_data = self.collect_trustpilot()

            # Aggregate all data
            logger.info("Aggregating data...")
            dashboard_data = self.aggregate_data(
                reddit_data, trends_data, meta_data, youtube_data, trustpilot_data
            )

            # Save history
            logger.info("Saving history...")
            self.save_aggregate_stats(dashboard_data)

            # Render template
            logger.info("Rendering dashboard...")
            output_path = self.render_template(dashboard_data)

            logger.info(f"Dashboard build complete! Output: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Dashboard build failed: {e}", exc_info=True)
            return False


def main():
    """Main entry point"""
    builder = DashboardBuilder()
    success = builder.build()
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
