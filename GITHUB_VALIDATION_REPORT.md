# GitHub Package Validation Report

Validation date: 2026-10-28

## Results

- Repository files: 20,069 before this report was added.
- Non-ASCII file paths: 0.
- Non-ASCII directory paths: 0.
- Paths containing spaces: 0.
- Duplicate SHA256 groups: 0.
- Largest tracked file: 20 MiB.
- Longest absolute path: 240 characters.
- Longest repository-relative path: 178 characters.
- Split assets verified against original size and SHA256: 13.
- Real API credential files excluded: 2.
- Weather source files preserved: 19,757.

## Large-file policy

GitHub warns for ordinary Git files larger than 50 MiB and blocks files larger than 100 MiB. Browser uploads are limited to 25 MiB per file. This package uses 20 MiB parts so every repository file remains below those thresholds.

Official reference: <https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github>

## Reproducibility

Run the following command before upload or after clone:

```bash
python tools/reassemble_large_files.py --verify-only
```

The script verifies every part set without writing reconstructed files.
