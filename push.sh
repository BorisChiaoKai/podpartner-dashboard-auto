#!/bin/bash
# PODpartner Dashboard Auto-Update — Push to GitHub
# 在此專案資料夾內執行: bash push.sh

set -e

echo "🚀 Pushing dashboard-auto to GitHub..."

# Check if already a git repo
if [ ! -d ".git" ]; then
    echo "📦 Initializing git..."
    git init
    git remote add origin https://github.com/BorisChiaoKai/podpartner-dashboard-auto.git
    git fetch origin
    git reset origin/main
    git checkout -b main
fi

# Create .gitignore if not exists
cat > .gitignore << 'EOF'
__pycache__/
*.pyc
.env
output/
*.egg-info/
EOF

# Add and push
git add -A
git status
echo ""
echo "📋 Files to be committed (above). Pushing now..."
git commit -m "Add dashboard auto-update pipeline" || echo "Nothing new to commit"
git push -u origin main

echo ""
echo "✅ Done! Your code is now at:"
echo "   https://github.com/BorisChiaoKai/podpartner-dashboard-auto"
echo ""
echo "Next steps:"
echo "   1. Add API Keys as GitHub Secrets (see SETUP.md)"
echo "   2. Go to Actions tab and trigger 'Update Dashboard'"
