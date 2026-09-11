# Security

This repository is intentionally designed so credentials and mailbox contents remain local.

## Never commit
- `.env`
- Gmail app passwords
- Microsoft OAuth tokens or MSAL token caches
- SQLite databases
- generated digests
- email exports
- applicant PII or private references
- `resume_profile.md` if it contains private information

The included `.gitignore` blocks these common paths, but you are responsible for reviewing every commit.

Before every push run:

```bash
git status --short
git diff --cached
```

For additional protection, enable GitHub secret scanning on the repository when available.
