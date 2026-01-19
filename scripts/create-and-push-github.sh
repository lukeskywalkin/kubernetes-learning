#!/bin/bash
# Script to create GitHub repository and push code
# Usage: ./create-and-push-github.sh [repository-name] [username]

set -e

REPO_NAME="${1:-kubernetes-learning}"
GITHUB_USER="${2:-lukeskywalkin}"

echo "🚀 Creating GitHub repository: $REPO_NAME"

# Check if GitHub CLI is available
if command -v gh &> /dev/null; then
    echo "Using GitHub CLI..."
    gh repo create "$REPO_NAME" --public --source=. --remote=origin --push
    echo "✅ Repository created and pushed!"
    exit 0
fi

# If GitHub CLI not available, provide instructions
echo "GitHub CLI not found. Please create the repository manually:"
echo ""
echo "1. Go to: https://github.com/new"
echo "2. Repository name: $REPO_NAME"
echo "3. Description: Kubernetes learning environment with multi-service app"
echo "4. Choose Public or Private"
echo "5. DO NOT initialize with README, .gitignore, or license"
echo "6. Click 'Create repository'"
echo ""
echo "Then run these commands:"
echo ""
echo "  git remote add origin https://github.com/$GITHUB_USER/$REPO_NAME.git"
echo "  git branch -M main"
echo "  git push -u origin main"
echo ""
