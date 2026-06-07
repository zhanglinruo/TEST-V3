# Contributing

This project uses GitHub commit history for exact code changes and `CHANGELOG.md` for human-readable product progress.

## Workflow

1. Pull the latest `main` before starting work.
2. Make a focused change.
3. Update `CHANGELOG.md` under `Unreleased` with one clear bullet.
4. Run the relevant checks, such as frontend build or backend smoke tests.
5. Commit with a concise message:

```bash
git add .
git commit -m "Describe the change"
git push
```

## Commit Style

Prefer short, concrete messages:

- `Add realtime Hermes run logs`
- `Embed Superset dashboard in workspace`
- `Fix Superset MCP runtime isolation`

## What Not To Commit

Do not commit local secrets, runtime logs, generated sessions, local databases, or dependency caches. The `.gitignore` already excludes the common local artifacts.
