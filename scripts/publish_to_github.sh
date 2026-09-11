#!/usr/bin/env bash
set -euo pipefail

REPO_NAME="${1:-mac-email-job-triage}"
VISIBILITY="${2:-private}"

if [[ "$VISIBILITY" != "private" && "$VISIBILITY" != "public" ]]; then
  echo "Usage: $0 [repo-name] [private|public]"
  exit 2
fi

if ! command -v git >/dev/null 2>&1; then
  echo "git is required"
  exit 1
fi
if ! command -v gh >/dev/null 2>&1; then
  echo "GitHub CLI (gh) is required. Install it with: brew install gh"
  exit 1
fi

if [[ ! -d .git ]]; then
  git init -b main
fi

if [[ -f .env ]]; then
  if git check-ignore -q .env; then
    :
  else
    echo "Safety check failed: .env is not ignored"
    exit 1
  fi
fi

for risky in .env resume_profile.md job_boards.json; do
  if git ls-files --error-unmatch "$risky" >/dev/null 2>&1; then
    echo "Safety check failed: $risky is tracked. Remove it from git before publishing."
    exit 1
  fi
done

git status --short

echo "Review the status above. The script will publish source files only."

gh auth status >/dev/null

git add .

if git diff --cached --quiet; then
  echo "No new changes to commit."
else
  git commit -m "Initial Apple Silicon email and job triage app"
fi

if git remote get-url origin >/dev/null 2>&1; then
  echo "Remote origin already exists: $(git remote get-url origin)"
  git push -u origin main
else
  gh repo create "$REPO_NAME" --"$VISIBILITY" --source=. --remote=origin --push
fi

echo "Published: $(git remote get-url origin)"
