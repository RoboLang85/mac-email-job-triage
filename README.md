# mac-email-job-triage

A local-first Python pipeline optimized for Apple Silicon:

`fetch -> classify -> store -> render`

The plumbing is deterministic. Ollama is used only for fuzzy classification and optional job-fit scoring. SQLite makes reruns idempotent, so messages that already have a triage decision do not consume another model pass.

## Safety defaults

- No email sending.
- No application submission.
- No LinkedIn automation.
- Frontier/cloud escalation is disabled by default.
- Gmail/Outlook credentials and OAuth caches stay outside Git.
- Job discovery is read-only against public Greenhouse, Lever, and Ashby job-board endpoints.
- Remote-only gating is enabled by default; explicit hybrid/on-site postings are rejected by the deterministic job gate before model scoring.

## Apple Silicon model defaults

Run:

```bash
triage model
```

The built-in defaults intentionally leave headroom for macOS and Python:

| Unified memory | Default |
|---|---|
| 16 GB or less | `qwen3:8b` |
| 18-24 GB | `qwen3:14b` |
| 32 GB+ | `qwen3:30b` |

You can override the choice with `OLLAMA_MODEL=` in `.env`. `gpt-oss:20b` is also a strong local alternative, but it is substantially larger than Qwen3 8B/14B.

## 1. Install prerequisites on macOS

Install Homebrew if you do not already have it, then:

```bash
brew install python@3.12 git gh
```

Install Ollama from the official macOS app, launch it once, and confirm:

```bash
ollama --version
curl http://127.0.0.1:11434/api/tags
```

Apple Silicon GPU acceleration uses Metal automatically in Ollama; no CUDA setup is required.

## 2. Bootstrap the app

From the repository root:

```bash
chmod +x scripts/bootstrap_macos.sh scripts/publish_to_github.sh
./scripts/bootstrap_macos.sh
```

Then:

```bash
.venv/bin/triage model
.venv/bin/triage pull-model
.venv/bin/triage doctor
```

## 3. Configure Gmail

Copy/edit `.env` and set:

```text
GMAIL_ENABLED=true
GMAIL_USER=you@example.com
GMAIL_APP_PASSWORD=your-app-password
```

Use a Gmail app password if your account supports it. Do not use your normal Gmail password and never commit `.env`.

## 4. Configure personal Outlook / Outlook.com

Register a public-client application in Microsoft Entra and enable delegated `Mail.Read`. Put only the application/client ID in `.env`:

```text
OUTLOOK_ENABLED=true
MS_CLIENT_ID=00000000-0000-0000-0000-000000000000
MS_TENANT_ID=consumers
```

The first run uses Microsoft device-code authentication. The MSAL token cache is written under `~/.mac-email-job-triage/` with owner-only permissions.

## 5. Run email triage

```bash
.venv/bin/triage run
.venv/bin/triage digest --minimum-urgency 1
```

Only unread messages not already classified in SQLite are sent to the local Ollama model. Messages are truncated to 4,000 characters by default and classified in small batches of four to reduce model-load overhead without creating large prompts.

## 6. Configure optional job discovery

```bash
cp job_boards.example.json job_boards.json
cp resume_profile.example.md resume_profile.md
```

Edit `job_boards.json` and enable only the boards you want to monitor. Put only verified professional facts in `resume_profile.md`.

Fetch listings without model scoring:

```bash
.venv/bin/triage jobs-refresh
```

Fetch and locally score against the verified resume profile:

```bash
.venv/bin/triage jobs-refresh --score
```

This command never submits an application.

## 7. Run automatically with launchd

For a noon local-time run on macOS, create `~/Library/LaunchAgents/com.langit.mac-email-job-triage.plist` using the example in `launchd.example.plist`. Replace `REPOSITORY_PATH` with the absolute repository path, then:

```bash
cp launchd.example.plist ~/Library/LaunchAgents/com.langit.mac-email-job-triage.plist
sed -i '' "s|REPOSITORY_PATH|$PWD|g" ~/Library/LaunchAgents/com.langit.mac-email-job-triage.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.langit.mac-email-job-triage.plist
```

The launchd task runs `triage run` followed by `triage digest` at 12:00 local Mac time.

## 8. Tests and publication preflight

```bash
./scripts/preflight.sh
```

This compiles the source, runs Ruff and pytest, and checks that common private runtime files are not tracked.

## 9. Publish to GitHub

Authenticate once:

```bash
gh auth login
```

Then create a private repository and push:

```bash
./scripts/publish_to_github.sh mac-email-job-triage private
```

Before pushing, always inspect:

```bash
git status --short
git diff --cached
```

## Architecture notes

### Why SQLite

`(source, external_id)` is unique. A separate triage row records that classification has completed. If the process crashes after fetching, rerunning safely continues. If a message already has a triage decision, the model is not called for it again.

### Why one local model call at a time

Apple Silicon has unified memory shared by the OS, applications, CPU, and GPU. Limiting model concurrency to one avoids loading multiple inference workloads into the same memory pool and generally improves responsiveness on laptops.

### Prompt-injection boundary

Email and job descriptions are explicitly treated as untrusted data. The model system instructions say not to follow commands found in message bodies or postings. The application does not expose tools to the model; Python controls every external action.

### Job providers

The implementation uses the public read endpoints documented by Greenhouse, Lever, and Ashby. Application-submission endpoints are intentionally not implemented.

## Current limitations

- It does not mark mail as read, move mail, send replies, or apply labels/categories.
- It does not yet ingest Slack or Teams messages. The normalized `MessageRecord` interface is intentionally connector-neutral so those sources can be added without changing the classifier/database/render stages.
- It does not create tailored DOCX/PDF resumes. Keep that capability in the existing approval-gated resume/application workflow rather than mixing document generation into the mailbox reader.
- Remote detection is conservative. If the posting is ambiguous, it is marked `unclear` rather than guessed.
