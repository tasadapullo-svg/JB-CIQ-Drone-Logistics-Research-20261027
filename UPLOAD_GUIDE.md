# GitHub Upload Guide

This package uses ASCII-only paths, excludes local API credentials, and limits every tracked file to 20 MiB or less. Research-source bytes are preserved unless a file is represented as verified split parts.

## Upload workflow

```bash
git status
git add .
git commit -m "Prepare CIQ drone logistics SCI research package"
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git push -u origin main
```

Before committing, confirm that `git status` does not list real API keys, `.env` files, private keys, or reconstructed large files.

## Verify split files

```bash
python tools/reassemble_large_files.py --verify-only
```

Do not remove or weaken scientific labels such as `MODEL_NOT_OBSERVED`, `NOT_FLIGHT_ROUTES`, `NOT_AUTHORIZED`, or `UNVERIFIED`.
