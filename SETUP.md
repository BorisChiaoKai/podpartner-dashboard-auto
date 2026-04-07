# PODpartner Dashboard Auto-Update — 快速設定指南

## Step 1: 推送程式碼到 GitHub

在你的電腦終端機（Terminal）執行以下指令：

```bash
# 1. 進入專案資料夾（請替換成你電腦上的實際路徑）
cd "你的路徑/PODpartner Dashboard/dashboard-auto"

# 2. 初始化 Git 並推送
git init
git remote add origin https://github.com/BorisChiaoKai/podpartner-dashboard-auto.git
git fetch origin
git checkout -b main origin/main
cp -r . /tmp/dashboard-backup

# 3. 把所有檔案加入並推送
git add -A
git commit -m "Add dashboard auto-update pipeline"
git push origin main
```

> 如果 Git push 時要求登入，使用你的 GitHub 帳號 + Personal Access Token（不是密碼）

## Step 2: 申請 API Keys

### Reddit API
1. 前往 https://www.reddit.com/prefs/apps
2. 點「create another app...」
3. 選「script」, 填入名稱「PodPartner Dashboard」
4. Redirect URI 填 `http://localhost:8080`
5. 記下 `client_id`（app 名稱下方的字串）和 `client_secret`

### Meta Ads API
1. 前往 https://business.facebook.com/
2. 進入 Business Settings → System Users → Generate Token
3. 或使用 Graph API Explorer: https://developers.facebook.com/tools/explorer/
4. 記下 Access Token 和 Ad Account ID（格式：act_XXXXXXXXX）

### YouTube API
1. 前往 https://console.cloud.google.com/
2. 建立專案或選擇現有專案
3. 啟用「YouTube Data API v3」
4. 建立 Credentials → API Key
5. 記下 API Key

### Netlify
1. 前往 https://app.netlify.com/user/applications#personal-access-tokens
2. 建立 Personal Access Token
3. 前往你的 site 設定，記下 Site ID（在 Site information 裡面）
4. 你的 Site ID 來自: https://animated-taiyaki-82c707.netlify.app/

## Step 3: 設定 GitHub Secrets

1. 前往 https://github.com/BorisChiaoKai/podpartner-dashboard-auto/settings/secrets/actions
2. 點「New repository secret」，依序加入：

| Secret Name | Value |
|---|---|
| REDDIT_CLIENT_ID | 你的 Reddit Client ID |
| REDDIT_CLIENT_SECRET | 你的 Reddit Client Secret |
| REDDIT_USER_AGENT | PodPartnerDashboard/1.0 |
| META_ACCESS_TOKEN | 你的 Meta Access Token |
| META_AD_ACCOUNT_ID | 你的 Ad Account ID |
| YOUTUBE_API_KEY | 你的 YouTube API Key |
| NETLIFY_AUTH_TOKEN | 你的 Netlify Token |
| NETLIFY_SITE_ID | 你的 Netlify Site ID |
| TRUSTPILOT_BUSINESS_URL | https://www.trustpilot.com/review/podpartner.com |

## Step 4: 測試執行

1. 前往 https://github.com/BorisChiaoKai/podpartner-dashboard-auto/actions
2. 選「Update Dashboard」workflow
3. 點「Run workflow」手動觸發
4. 等待完成後，你的 dashboard 就會自動更新！

之後每天中午 UTC 會自動執行一次。
