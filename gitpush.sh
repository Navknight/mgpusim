#!/bin/bash

# Check if a commit message is provided
if [ -z "$1" ]; then
  echo "Usage: $0 <commit-message>"
  exit 1
fi

# Store the commit message
COMMIT_MESSAGE="$1"

cd akita
git add .
git commit -m "$COMMIT_MESSAGE"
git push

cd ..

# Add all changes in the main repository
git add .

# Commit changes in the main repository
git commit -m "$COMMIT_MESSAGE"

# Push changes in the main repository
git push



echo "All changes pushed successfully."
