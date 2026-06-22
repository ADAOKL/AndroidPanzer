# Contributing to Android Panzer

Thank you for your interest in contributing! Here's how to get started:

## Development Setup

```bash
# Clone the repo
git clone https://github.com/ADAOKL/android-panzer.git
cd android-panzer

# Install test dependencies
pip install pytest ruff

# Run tests
python -m pytest tests/ -v

# Lint code
ruff check apz/ tests/ panzer.py
```

## Code Style

- **Python:** Follow PEP 8 (configured in `pyproject.toml`)
- **Imports:** Sorted with `isort` (ruff handles this)
- **Line length:** 120 characters max (except URLs, long strings)
- **Security:** All shell invocations use `shlex.quote()` — see `apz/util.py:shq()`

## Testing

- Write tests in `tests/` using `pytest`
- Mock ADB interactions with `MockADB` (see `tests/mock_adb.py`)
- All tests must pass: `python -m pytest`

## Pull Request Checklist

- [ ] Code passes `ruff check`
- [ ] All tests pass (`pytest`)
- [ ] No hardcoded secrets or paths
- [ ] Functions documented (brief comments for "why", not "what")
- [ ] Commit messages are clear and concise

## Important Notes

- **Authorized use only:** This tool is for forensics on devices you own or have explicit permission to analyze.
- **No data fabrication:** If something requires Root/SDR/Hardware, document it rather than faking it.
- **Command injection prevention:** All untrusted input is quoted with `shq()` before shell execution.

## Reporting Issues

Found a bug? Please file an issue with:
- Device model & Android version
- Exact steps to reproduce
- Output/log files (from `logs/`)
