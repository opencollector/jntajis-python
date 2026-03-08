# Documents for both humans and coding agents

* [README.md](./README.md)

# Documents for coding agents

* [`./.agents/docs/OVERVIEW.md`](./.agents/docs/OVERVIEW.md) ... project overview.
* [`./.agents/docs/ARCHITECTURE.md`](./.agents/docs/ARCHITECTURE.md) ... system architecture.
* [`./.agents/docs/JOURNAL.md`](./.agents/docs/JOURNAL.md) ... findings insights, and peer code review history.
* [`./.agents/docs/LTM/*.md`](./.agents/docs/LTM/INDEX.md) ... JOURNAL.md reorganized; a.k.a. long term memory.

# Rules and protocols

## File Management

* When you'd make summary documents for your work, be sure to write them under `./.agents/docs`, not under `/tmp`.
* Temporary files should be created under `./.agents/tmp`, not under `/tmp`.
* ❌ Do not randomly create a binary under the version controlled directory through `go build ./cmd/s3router`. Always put it under `./.agents/tmp`.
* ❌ Never delete user files without permission. Only safe to delete: files YOU created in THIS session that are in `./.agents/tmp/`. Always ask first if unsure. Assume all pre-existing files belong to user.

## Documentation

* Try to write your work summary to one of the existing documents.
* ❌ Avoid editing any existing sections of JOURNAL.md. You should rather just append texts to it.

## Testing

* Make sure that regression tests are ready for your fix.
* ❌ You shouldn't run the entire integration test suites at once. Or if you can spare them 2+ minutes, be patient with it. You should always specify `--maxfail=n` (n should be a number less than 10), and also be sure to specify `--lf` as well when you want to run the last failing tests.

## Python

* ✅ Always create a virtualenv under .venv if there is none, and activate it before doing anything related to Python.

## Git Workflow

* ❌ Neither do `git checkout` nor `git restore`. The other coding agent is concurrently working on the same directory.
* ❌ Never make discretionary commits.

## Documentation

* ❌ For repo-authored documentation only (e.g., `AGENTS.md`, `README.md`, `.agents/docs/**`), never use full-width parentheses (`（` `)`). Instead, use half-width parentheses (`(` `)`) with a half-width space being put before/after an open/close parenthesis when it's preceded/followed by a non-white-space character. This rule does **not** apply to generated or third-party reference files under `skills/**/references/**`.
* ❌ For repo-authored documentation only (e.g., `AGENTS.md`, `README.md`, `.agents/docs/**`), never use full-width colons (`：`). Instead, use a half-width colon followed by a half-width space. This rule does **not** apply to generated or third-party reference files under `skills/**/references/**`.
