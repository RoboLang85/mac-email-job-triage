# mac-email-job-triage

A local-first Python application for private email triage and remote-job discovery on Apple Silicon.

The core design is deliberately simple:

```text
fetch -> normalize -> classify -> store -> render
```

Python owns the workflow. Local models are used only for fuzzy tasks such as classification, summarization, and optional job-fit scoring. SQLite provides durable, idempotent state so reruns do not repeatedly process the same message or waste inference cycles.

The project is optimized for M-series Macs and uses Ollama for local inference. It intentionally avoids agent frameworks and multi-step model tool loops.

## What it does

- Reads unread Gmail messages over IMAP without marking them read.
- Reads Outlook / Outlook.com mail through Microsoft Graph delegated authentication.
- Normalizes messages into a connector-neutral internal record.
- Classifies email locally with structured Ollama output.
- Stores message and triage state in SQLite for resumable, idempotent runs.
- Generates Markdown digests from recent classifications.
- Discovers jobs from configured Greenhouse, Lever, and Ashby boards.
- Applies deterministic remote-only filtering before optional model scoring.
- Scores job descriptions against a local, user-controlled professional profile.
- Runs interactively or on a macOS `launchd` schedule.

## Safety and privacy defaults

This project is intentionally read-oriented.

- **No email sending.**
- **No application submission.**
- **No LinkedIn automation.**
- **No automatic mailbox mutation.**
- **No cloud model use by default.**
- Frontier/cloud escalation exists only as an optional, disabled configuration path.
- Credentials, OAuth caches, SQLite databases, raw mail, logs, private resume data, and generated output are excluded from Git.
- Email bodies and job descriptions are treated as untrusted input. The model is not given tools or authority to perform external actions.

Review `SECURITY.md` before enabling connectors or adapting the project for a production environment.

## Architecture

```text
                 +------------------+
Gmail IMAP ----> |                  |
                 | Message          |       +------------------+
Outlook Graph -> | normalization    | ----> | SQLite state     |
                 |                  |       +---------+--------+
                 +------------------+                 |
                                                      v
                                             +------------------+
                                             | Ollama           |
                                             | classification   |
                                             +---------+--------+
                                                       |
                                                       v
                                             +------------------+
                                             | Markdown digest  |
                                             +------------------+

Greenhouse / Lever / Ashby
            |
            v
+-------------------------+
| deterministic job gate  |
| remote-only by default  |
+------------+------------+
             |
             v
+-------------------------+
| optional local fit      |
| scoring with Ollama     |
+-------------------------+
```

### Why deterministic plumbing?

The application does not ask a model to rediscover the workflow on every run. Fetching, deduplication, persistence, filtering, scheduling, and rendering are normal Python code. Models answer narrow questions only where semantic judgment is useful.

That architecture reduces token use, improves repeatability, makes failures easier to diagnose, and works well with smaller local models.

## Apple Silicon model defaults

Run:

```bash
triage model
```

The built-in selection intentionally leaves unified-memory headroom for macOS and other applications:

| Unified memory | Default model |
| --- | --- |
| 16 GB or less | `qwen3:8b` |
| 18-24 GB | `qwen3:14b` |
| 32 GB+ | `qwen3:30b` |

Override the automatic choice with `OLLAMA_MODEL` in `.env`.

Inference concurrency is intentionally conservative because CPU, GPU, and the operating system share the same memory pool on Apple Silicon.

## Requirements

- macOS on Apple Silicon
- Python 3.12+
- Ollama
- Git
- Gmail app password if Gmail IMAP is enabled
- Microsoft Entra public-client application with delegated `Mail.Read` if Outlook is enabled

The code may work on other platforms, but macOS/Apple Silicon is the primary target and the included bootstrap/scheduling scripts are macOS-specific.

## Quick start

Clone the repository:

```bash
git clone https://github.com/RoboLang85/mac-email-job-triage.git
cd mac-email-job-triage
```

Install prerequisites with Homebrew if needed:

```bash
brew install python@3.12 git
```

Install and launch Ollama, then verify it is reachable:

```bash
ollama --version
curl http://127.0.0.1:11434/api/tags
```

Bootstrap the Python environment:

```bash
chmod +x scripts/bootstrap_macos.sh scripts/preflight.sh
./scripts/bootstrap_macos.sh
```

Inspect the selected local model and pull it:

```bash
.venv/bin/triage model
.venv/bin/triage pull-model
.venv/bin/triage doctor
```

## Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Never commit `.env`.

### Gmail

Set:

```text
GMAIL_ENABLED=true
GMAIL_USER=you@example.com
GMAIL_APP_PASSWORD=your-app-password
```

Use a Gmail app password rather than your normal account password where supported.

### Outlook / Outlook.com

Register a Microsoft Entra public-client application with delegated `Mail.Read`, then set:

```text
OUTLOOK_ENABLED=true
MS_CLIENT_ID=00000000-0000-0000-0000-000000000000
MS_TENANT_ID=consumers
```

The first run uses device-code authentication. The MSAL token cache is stored outside the repository under `~/.mac-email-job-triage/`.

## Run email triage

```bash
.venv/bin/triage run
```

Render a recent digest:

```bash
.venv/bin/triage digest --minimum-urgency 1 --since-hours 24
```

By default, message bodies are truncated before inference and messages that already have a stored triage decision are not sent to the model again.

## Job discovery

Create local configuration files from the examples:

```bash
cp job_boards.example.json job_boards.json
cp resume_profile.example.md resume_profile.md
```

Enable the job boards you want to monitor and put only verified professional facts in `resume_profile.md`.

Fetch jobs without model scoring:

```bash
.venv/bin/triage jobs-refresh
```

Fetch jobs and perform local fit scoring:

```bash
.venv/bin/triage jobs-refresh --score
```

Job discovery is read-only. The project does not submit applications.

## Automated runs with launchd

The repository includes `launchd.example.plist` for a noon local-time run.

```bash
cp launchd.example.plist ~/Library/LaunchAgents/com.langit.mac-email-job-triage.plist
sed -i '' "s|REPOSITORY_PATH|$PWD|g" ~/Library/LaunchAgents/com.langit.mac-email-job-triage.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.langit.mac-email-job-triage.plist
```

The scheduled task runs email triage followed by digest generation.

## Development

Run the complete local preflight:

```bash
./scripts/preflight.sh
```

The preflight compiles the Python source, runs linting and tests, and checks that common private runtime files are not tracked by Git.

Useful commands:

```bash
make test
make lint
```

## Data handling

Runtime data should remain local. The supplied `.gitignore` excludes, among other things:

- `.env` and environment-specific configuration
- OAuth/MSAL token caches
- SQLite databases
- logs and generated output
- raw mailbox exports
- `resume_profile.md`
- user-specific job-board configuration

If you extend the application, keep secrets and user data outside the repository and avoid logging message bodies or authentication material.

## Prompt-injection boundary

Email and job descriptions can contain arbitrary text, including instructions designed to manipulate an LLM. This project treats that content strictly as data.

The model does not decide what tools to invoke, does not receive mailbox credentials, and cannot directly send mail, mutate a mailbox, browse authenticated sites, or submit forms. External actions remain deterministic Python operations with explicit code paths.

## Current limitations

- Mail is not marked read, moved, labeled, categorized, or replied to.
- Slack and Teams ingestion are not yet implemented, although the normalized message interface is connector-neutral.
- Tailored DOCX/PDF resume generation is intentionally outside this repository.
- Job-application submission is intentionally outside this repository.
- Remote-work detection is conservative; ambiguous postings are reported as unclear rather than guessed.
- Third-party job-board APIs and authentication requirements can change, so integrations should be revalidated before production deployment.

## Roadmap

Potential additions include:

- Slack and Teams read-only connectors
- richer deterministic mailbox rules
- configurable digest destinations
- pluggable local-model profiles
- improved job deduplication and provenance tracking
- optional integration with a separate approval-gated application workflow

Contributions should preserve the local-first design, deterministic orchestration, explicit safety boundaries, and secret-free repository history.

## License

Released under the [MIT License](LICENSE).
