# Exact GitHub Upload and Mac Installation Instructions

The recommended repository name is `mac-email-job-triage` and the recommended visibility is **Private** until you intentionally decide otherwise.

## A. Put these files on your Mac

1. Download and expand `mac-email-job-triage.zip`.
2. Move the extracted folder to a permanent location, for example:

```bash
mkdir -p ~/Documents/GitHub
mv ~/Downloads/mac-email-job-triage ~/Documents/GitHub/
cd ~/Documents/GitHub/mac-email-job-triage
```

If macOS gives the extracted folder a different location/name, use that actual path instead.

## B. Verify/install prerequisites

```bash
xcode-select -p >/dev/null 2>&1 || xcode-select --install
```

If Homebrew is already installed:

```bash
brew update
brew install python@3.12 git gh
```

Install the current Ollama macOS application from Ollama's official site and launch it once. On Apple Silicon, Ollama uses Metal GPU acceleration automatically.

Verify:

```bash
python3 --version
git --version
gh --version
ollama --version
curl http://127.0.0.1:11434/api/tags
```

Python must be 3.12 or newer.

## C. Bootstrap the application

```bash
cd ~/Documents/GitHub/mac-email-job-triage
chmod +x scripts/*.sh
./scripts/bootstrap_macos.sh
```

Then determine and pull the recommended local model:

```bash
.venv/bin/triage model
.venv/bin/triage pull-model
.venv/bin/triage doctor
```

Default model selection is intentionally conservative:

- <=16 GB unified memory: `qwen3:8b`
- 18-24 GB: `qwen3:14b`
- >=32 GB: `qwen3:30b`

Override in `.env` with `OLLAMA_MODEL=...` if desired.

## D. Configure Gmail and/or Outlook locally

Edit `.env`:

```bash
nano .env
```

For Gmail:

```text
GMAIL_ENABLED=true
GMAIL_USER=YOUR_GMAIL_ADDRESS
GMAIL_APP_PASSWORD=YOUR_GMAIL_APP_PASSWORD
```

For personal Outlook/Outlook.com:

```text
OUTLOOK_ENABLED=true
MS_CLIENT_ID=YOUR_ENTRA_APPLICATION_CLIENT_ID
MS_TENANT_ID=consumers
```

Save the file. `.env` is deliberately excluded from Git.

## E. Test locally before creating the GitHub repository

```bash
./scripts/preflight.sh
.venv/bin/triage doctor
```

Then perform a controlled read-only run:

```bash
.venv/bin/triage run
.venv/bin/triage digest --minimum-urgency 1 --since-hours 24
```

The program does not mark email read, send mail, or submit applications.

## F. Create the GitHub repository automatically (recommended)

Authenticate GitHub CLI:

```bash
gh auth login
```

Choose GitHub.com, HTTPS, and browser authentication when prompted.

From the project root:

```bash
./scripts/preflight.sh
./scripts/publish_to_github.sh mac-email-job-triage private
```

The script will:

1. initialize Git with `main` if needed;
2. verify that `.env`, `resume_profile.md`, and `job_boards.json` are not tracked;
3. create the first commit;
4. create the GitHub repository;
5. configure `origin`;
6. push `main`.

Verify:

```bash
git remote -v
git status
git log -1 --oneline
gh repo view --web
```

## G. Manual Git/GitHub method if you do not want to use the publish script

Create a new **private** empty repository named `mac-email-job-triage` in GitHub. Do NOT initialize the GitHub repository with a README, `.gitignore`, or license because those already exist locally.

Then run:

```bash
cd ~/Documents/GitHub/mac-email-job-triage
./scripts/preflight.sh

git init -b main
git add .
git status --short
git diff --cached
```

Carefully verify that `.env`, `resume_profile.md`, `job_boards.json`, token caches, databases, and logs are absent from the staged files.

Then:

```bash
git commit -m "Initial Apple Silicon email and job triage app"
git remote add origin git@github.com:YOUR_GITHUB_USERNAME/mac-email-job-triage.git
git push -u origin main
```

If you use HTTPS instead of SSH, GitHub will show the appropriate repository URL after creation.

## H. Configure the job-board scanner (optional)

The bootstrap creates private local copies from the examples. Edit:

```bash
nano job_boards.json
nano resume_profile.md
```

Then:

```bash
.venv/bin/triage jobs-refresh
.venv/bin/triage jobs-refresh --score
```

The implemented discovery endpoints are read-only. No application submission is implemented.

## I. Schedule the noon run (optional)

From the repository root:

```bash
mkdir -p logs
cp launchd.example.plist ~/Library/LaunchAgents/com.langit.mac-email-job-triage.plist
sed -i '' "s|REPOSITORY_PATH|$PWD|g" ~/Library/LaunchAgents/com.langit.mac-email-job-triage.plist
plutil -lint ~/Library/LaunchAgents/com.langit.mac-email-job-triage.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.langit.mac-email-job-triage.plist
```

Check it:

```bash
launchctl print gui/$(id -u)/com.langit.mac-email-job-triage
```

To unload it later:

```bash
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.langit.mac-email-job-triage.plist
```

## J. Final security check before every future push

```bash
git status --short
git diff --cached
./scripts/preflight.sh
```

Never commit `.env`, Gmail app passwords, OAuth token caches, raw email, local SQLite databases, private applicant data, or generated digests.
