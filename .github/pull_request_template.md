## Description
<!-- Briefly explain what this PR does -->

## Type of Change
- [ ] Bug fix (fixes an issue without changing functionality)
- [ ] New feature (adds new functionality)
- [ ] Enhancement (improves existing functionality)
- [ ] Refactoring (code cleanup, no behavior change)
- [ ] Documentation update
- [ ] Test addition/improvement

## Related Issues
<!-- Link issues: Closes #123 -->

## Testing
<!-- How was this tested? Does it break any tests? -->
- [ ] All tests pass (`pytest`)
- [ ] Code passes linting (`ruff check`)
- [ ] New tests added (if applicable)

## Checklist
- [ ] Commits are clear and concise
- [ ] No hardcoded secrets or paths
- [ ] Command injection prevention: all shell invocations use `shq()` or `shlex.quote()`
- [ ] Existing functionality not broken
- [ ] Brief comments for "why", not "what"
