# Privacy and publication boundary

This repository was created with a fresh Git history. Its documentation, synthetic fixtures, and independent executable example were reconstructed in an AI-assisted, user-directed review rather than copied from the private source.

It intentionally excludes:

- original source files and Git objects from private repositories;
- environment files, credentials, keys, tokens, and connection strings;
- logs, database dumps, database rows, and raw market data;
- cloud account, host, bucket, deployment, and container identifiers;
- personal email addresses, phone numbers, and absolute user-directory paths; and
- internal agent prompts, editor configuration, and operational runbooks.

The aggregate history metrics in `evidence/metrics.json` contain no author names or email addresses. They were derived locally from repository metadata and cannot independently prove code quality or authorship.

Every proposed change is checked by `scripts/privacy_guard.py`. A passing scan reduces accidental disclosure risk but is not a substitute for credential rotation or a human review.
