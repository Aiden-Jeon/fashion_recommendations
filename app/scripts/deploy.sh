#!/bin/bash
# Databricks App Deployment Script - Sync & Deploy
# Usage: ./deploy.sh [dev|prod]

set -e

TARGET="${1:-dev}"
APP_NAME="fashion-rec-app-${TARGET}"
WORKSPACE_PATH="/Workspace/Users/jongseob.jeon@databricks.com/fashion-rec-app-${TARGET}"

echo "=========================================="
echo "Deploying Fashion Recommendations App"
echo "Target: $TARGET"
echo "App Name: $APP_NAME"
echo "=========================================="
echo

# Check if databricks CLI is installed
if ! command -v databricks &> /dev/null; then
    echo "❌ Error: Databricks CLI not found"
    echo "Install it with: pip install databricks-cli"
    exit 1
fi

# Check authentication
echo "Checking Databricks authentication..."
if ! databricks auth profiles | grep -q "YES"; then
    echo "❌ Not authenticated with Databricks"
    echo "Please run: databricks auth login --host <your-workspace-url>"
    exit 1
fi
echo "✓ Authentication verified"
echo

# Change to app directory (parent of scripts)
cd "$(dirname "$0")/.."

# Check required files
echo "Validating configuration files..."
for file in app.yaml requirements.txt app.py; do
    if [ ! -f "$file" ]; then
        echo "❌ Missing required file: $file"
        exit 1
    fi
done
echo "✓ All required files present"
echo

# Run the Python deployment script
echo "Running deployment script..."
python3 scripts/deploy.py "$TARGET"

exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo
    echo "=========================================="
    echo "✅ Deployment completed successfully!"
    echo "=========================================="
else
    echo
    echo "=========================================="
    echo "❌ Deployment failed!"
    echo "=========================================="
    exit $exit_code
fi
