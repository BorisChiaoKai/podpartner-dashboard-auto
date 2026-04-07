"""
YouTube data collector for PODPartner Dashboard.

Searches for videos mentioning PODPartner and related keywords using YouTube Data API v3.

Required environment variables:
- YOUTUBE_API_KEY: YouTube Data API v3 key from Google Cloud Console
"""

import os
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def collect():
    """
    Collect YouTube video data for PODPartner mentions.

    Returns:
        dict: Contains keys:
            - videos: list of video objects with title, channel, date, view_count, comment_count, url
            - total_videos: int
            - keywords_monitored: list
            - collection_timestamp: ISO datetime string
    """

    print("[YouTube] Starting collection...")

    api_key = os.environ.get("YOUTUBE_API_KEY")

    if not api_key:
        print("[YouTube] Missing API key (YOUTUBE_API_KEY)")
        return {
            "videos": [],
            "total_videos": 0,
            "collection_timestamp": datetime.utcnow().isoformat(),
            "error": "Missing YouTube API key"
        }

    try:
        # Initialize YouTube API client
        youtube = build('youtube', 'v3', developerKey=api_key)
        print("[YouTube] API client initialized")

    except Exception as e:
        print(f"[YouTube] API initialization failed: {e}")
        return {
            "videos": [],
            "total_videos": 0,
            "collection_timestamp": datetime.utcnow().isoformat(),
            "error": f"API initialization failed: {str(e)}"
        }

    # Keywords to search
    keywords = ["podpartner", "pod partner"]

    videos = []

    try:
        # Set date range (last 30 days)
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)

        print(f"[YouTube] Searching for videos from {start_date.date()} to {end_date.date()}")

        for keyword in keywords:
            try:
                print(f"[YouTube] Searching for keyword: '{keyword}'")

                # Search for videos
                search_request = youtube.search().list(
                    q=keyword,
                    part='snippet',
                    type='video',
                    order='relevance',
                    publishedAfter=start_date.isoformat() + 'Z',
                    publishedBefore=end_date.isoformat() + 'Z',
                    maxResults=50,
                    relevanceLanguage='en'
                )

                search_response = search_request.execute()

                # Extract video IDs from search results
                video_ids = []
                for item in search_response.get('items', []):
                    if item['id']['kind'] == 'youtube#video':
                        video_ids.append(item['id']['videoId'])

                print(f"[YouTube] Found {len(video_ids)} videos for '{keyword}'")

                if not video_ids:
                    continue

                # Get detailed statistics for each video
                # Split into chunks if needed (API limit is 50 per request)
                for i in range(0, len(video_ids), 50):
                    chunk = video_ids[i:i+50]

                    stats_request = youtube.videos().list(
                        id=','.join(chunk),
                        part='snippet,statistics',
                        fields='items(id,snippet(title,channelTitle,publishedAt),statistics(viewCount,commentCount))'
                    )

                    stats_response = stats_request.execute()

                    for item in stats_response.get('items', []):
                        try:
                            video_id = item['id']
                            snippet = item.get('snippet', {})
                            statistics = item.get('statistics', {})

                            title = snippet.get('title', 'Unknown')
                            channel = snippet.get('channelTitle', 'Unknown')
                            published_at = snippet.get('publishedAt', '')

                            # Parse date
                            try:
                                date_obj = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                                video_date = date_obj.date().isoformat()
                            except:
                                video_date = published_at[:10] if published_at else 'Unknown'

                            view_count = int(statistics.get('viewCount', 0))
                            comment_count = int(statistics.get('commentCount', 0))

                            video_obj = {
                                "title": title,
                                "channel": channel,
                                "date": video_date,
                                "view_count": view_count,
                                "comment_count": comment_count,
                                "url": f"https://www.youtube.com/watch?v={video_id}",
                                "keyword_found": keyword
                            }
                            videos.append(video_obj)

                        except Exception as e:
                            print(f"[YouTube] Error processing video: {e}")
                            continue

            except HttpError as e:
                print(f"[YouTube] HTTP error searching '{keyword}': {e}")
                continue
            except Exception as e:
                print(f"[YouTube] Error searching '{keyword}': {e}")
                continue

        # Sort by view count (descending)
        videos = sorted(videos, key=lambda x: x['view_count'], reverse=True)

        print(f"[YouTube] Collection complete. Found {len(videos)} videos")

        return {
            "videos": videos,
            "total_videos": len(videos),
            "keywords_monitored": keywords,
            "collection_timestamp": datetime.utcnow().isoformat(),
            "period": f"Last 30 days ({start_date.date()} to {end_date.date()})"
        }

    except Exception as e:
        print(f"[YouTube] Collection failed: {e}")
        return {
            "videos": videos,
            "total_videos": len(videos),
            "keywords_monitored": keywords,
            "collection_timestamp": datetime.utcnow().isoformat(),
            "error": f"Collection error: {str(e)}"
        }
