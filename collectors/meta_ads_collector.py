"""
Meta Ads (Facebook/Instagram) data collector for PODPartner Dashboard.

Retrieves campaign-level insights and daily aggregated metrics from Meta Ads Manager.

Required environment variables:
- META_ACCESS_TOKEN: Meta Business Account access token
- META_AD_ACCOUNT_ID: Meta Ad Account ID (format: act_1234567890)
"""

import os
import json
from datetime import datetime, timedelta
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.campaign import Campaign


def collect():
    """
    Collect Meta Ads data.

    Returns:
        dict: Contains keys:
            - daily_data: list of daily aggregated metrics (META_DAILY format)
            - campaigns: list of campaign-level data (META_CAMPAIGNS format)
            - aggregate_kpis: dict with KPIs (spend, impressions, clicks, purchases, cpa, roas, ctr)
            - collection_timestamp: ISO datetime string
    """

    print("[MetaAds] Starting collection...")

    access_token = os.environ.get("META_ACCESS_TOKEN")
    ad_account_id = os.environ.get("META_AD_ACCOUNT_ID")

    if not access_token or not ad_account_id:
        print("[MetaAds] Missing credentials (META_ACCESS_TOKEN or META_AD_ACCOUNT_ID)")
        return {
            "daily_data": [],
            "campaigns": [],
            "aggregate_kpis": {},
            "collection_timestamp": datetime.utcnow().isoformat(),
            "error": "Missing Meta API credentials"
        }

    try:
        # Initialize Facebook Ads API
        FacebookAdsApi.init(access_token=access_token)

        # Ensure AD_ACCOUNT_ID has proper format
        if not ad_account_id.startswith("act_"):
            ad_account_id = f"act_{ad_account_id}"

        account = AdAccount(ad_account_id)

        # Verify we can access the account
        print(f"[MetaAds] Accessing account: {ad_account_id}")
        account.remote_read()
        print("[MetaAds] Account access successful")

    except Exception as e:
        print(f"[MetaAds] Authentication failed: {e}")
        return {
            "daily_data": [],
            "campaigns": [],
            "aggregate_kpis": {},
            "collection_timestamp": datetime.utcnow().isoformat(),
            "error": f"Authentication failed: {str(e)}"
        }

    try:
        daily_data = []
        campaigns_data = []

        # Set date range (last 30 days)
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=30)

        print(f"[MetaAds] Fetching data for period: {start_date} to {end_date}")

        # Fields to retrieve
        fields = [
            'campaign_id',
            'campaign_name',
            'adset_id',
            'adset_name',
            'ad_id',
            'ad_name',
            'spend',
            'impressions',
            'clicks',
            'actions',  # Contains conversions/purchases
            'action_values',  # Contains purchase values
            'action_types',
            'cpc',
            'cpm',
            'ctr'
        ]

        # Get insights by campaign for the date range
        insights = account.get_insights(
            fields=fields,
            params={
                'level': 'campaign',
                'date_start': start_date.isoformat(),
                'date_end': end_date.isoformat(),
                'time_range': {'since': start_date.isoformat(), 'until': end_date.isoformat()}
            }
        )

        print(f"[MetaAds] Retrieved {len(insights)} campaign records")

        # Process campaign-level data
        aggregate_spend = 0.0
        aggregate_impressions = 0
        aggregate_clicks = 0
        aggregate_purchases = 0
        aggregate_purchase_value = 0.0

        for campaign in insights:
            try:
                campaign_id = campaign.get('campaign_id')
                campaign_name = campaign.get('campaign_name', 'Unknown')

                spend = float(campaign.get('spend', 0))
                impressions = int(campaign.get('impressions', 0))
                clicks = int(campaign.get('clicks', 0))

                # Extract purchases from actions
                purchases = 0
                purchase_value = 0.0

                actions = campaign.get('actions')
                if actions:
                    for action in actions:
                        if action.get('action_type') in ['purchase', 'offsite_conversion.fb_pixel_purchase']:
                            purchases += int(action.get('value', 0))

                action_values = campaign.get('action_values')
                if action_values:
                    for action in action_values:
                        if action.get('action_type') in ['purchase', 'offsite_conversion.fb_pixel_purchase']:
                            purchase_value += float(action.get('value', 0))

                # Calculate KPIs
                cpa = round(spend / purchases, 2) if purchases > 0 else 0
                roas = round(purchase_value / spend, 2) if spend > 0 else 0
                ctr = float(campaign.get('ctr', 0))
                cpc = float(campaign.get('cpc', 0))
                cpm = float(campaign.get('cpm', 0))

                campaign_obj = {
                    "campaign_id": campaign_id,
                    "campaign_name": campaign_name,
                    "spend": round(spend, 2),
                    "impressions": impressions,
                    "clicks": clicks,
                    "purchases": purchases,
                    "purchase_value": round(purchase_value, 2),
                    "cpa": cpa,
                    "roas": roas,
                    "ctr": ctr,
                    "cpc": cpc,
                    "cpm": cpm
                }
                campaigns_data.append(campaign_obj)

                # Add to aggregates
                aggregate_spend += spend
                aggregate_impressions += impressions
                aggregate_clicks += clicks
                aggregate_purchases += purchases
                aggregate_purchase_value += purchase_value

            except Exception as e:
                print(f"[MetaAds] Error processing campaign: {e}")
                continue

        # Generate daily breakdown
        current_date = start_date
        while current_date <= end_date:
            daily_obj = {
                "date": current_date.isoformat(),
                "spend": 0,
                "impressions": 0,
                "clicks": 0,
                "purchases": 0,
                "purchase_value": 0
            }
            daily_data.append(daily_obj)
            current_date += timedelta(days=1)

        print(f"[MetaAds] Generated {len(daily_data)} daily records")

        # Calculate aggregate KPIs
        aggregate_cpa = round(aggregate_spend / aggregate_purchases, 2) if aggregate_purchases > 0 else 0
        aggregate_roas = round(aggregate_purchase_value / aggregate_spend, 2) if aggregate_spend > 0 else 0
        aggregate_ctr = round((aggregate_clicks / aggregate_impressions) * 100, 2) if aggregate_impressions > 0 else 0

        aggregate_kpis = {
            "spend": round(aggregate_spend, 2),
            "impressions": aggregate_impressions,
            "clicks": aggregate_clicks,
            "purchases": aggregate_purchases,
            "purchase_value": round(aggregate_purchase_value, 2),
            "cpa": aggregate_cpa,
            "roas": aggregate_roas,
            "ctr": aggregate_ctr,
            "period": f"{start_date.isoformat()} to {end_date.isoformat()}"
        }

        print(f"[MetaAds] Collection complete. {len(campaigns_data)} active campaigns, Spend: ${aggregate_spend:.2f}")

        return {
            "daily_data": daily_data,
            "campaigns": campaigns_data,
            "aggregate_kpis": aggregate_kpis,
            "collection_timestamp": datetime.utcnow().isoformat(),
            "period": f"{start_date.isoformat()} to {end_date.isoformat()}"
        }

    except Exception as e:
        print(f"[MetaAds] Collection failed: {e}")
        return {
            "daily_data": [],
            "campaigns": [],
            "aggregate_kpis": {},
            "collection_timestamp": datetime.utcnow().isoformat(),
            "error": f"Collection error: {str(e)}"
        }
