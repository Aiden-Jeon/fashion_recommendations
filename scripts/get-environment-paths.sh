#!/bin/bash
# Script to display workspace paths for environment files after bundle deploy

set -e

# Get current user email from Databricks CLI
USER_EMAIL=$(databricks current-user me 2>/dev/null | grep "userName" | awk -F'"' '{print $4}')

if [ -z "$USER_EMAIL" ]; then
    echo "Error: Could not determine Databricks user. Make sure you're authenticated with 'databricks auth login'"
    exit 1
fi

BUNDLE_NAME="fashion_recommendations"
TARGET="${1:-dev}"

echo "=================================="
echo "Databricks Environment File Paths"
echo "=================================="
echo ""
echo "Target: $TARGET"
echo "User: $USER_EMAIL"
echo ""
echo "Base Environment Paths (use in notebook Environment panel):"
echo ""
echo "📦 Core (ML + Data Engineering):"
echo "   /Workspace/Users/$USER_EMAIL/.bundle/$BUNDLE_NAME/$TARGET/environments/base-core.yml"
echo ""
echo "📊 Viz (Core + Matplotlib/Seaborn):"
echo "   /Workspace/Users/$USER_EMAIL/.bundle/$BUNDLE_NAME/$TARGET/environments/base-viz.yml"
echo ""
echo "🧠 Deep Learning (Core + PyTorch):"
echo "   /Workspace/Users/$USER_EMAIL/.bundle/$BUNDLE_NAME/$TARGET/environments/base-dl.yml"
echo ""
echo "=================================="
echo "How to use:"
echo "1. Run: databricks bundle deploy -t $TARGET"
echo "2. Open your notebook in Databricks"
echo "3. Click Environment panel → Base environment → Custom"
echo "4. Paste one of the paths above"
echo "5. Save and restart notebook environment"
echo "=================================="
