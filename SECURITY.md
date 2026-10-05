# Security policy

This is a documentation and demonstration repository. It does not operate a service, accept market data, or require production credentials.

## Reporting a problem

Use GitHub's private security-advisory feature for this repository. Do not open a public issue containing a suspected credential or personal data.

## Credential boundary

No credential from an original project is intentionally included here. Any credential that has ever been committed elsewhere must be treated as exposed and rotated; deleting a file, rewriting a document, or changing repository visibility is not a substitute for revocation.

The examples use no network credential. All SQL fixtures are synthetic and run against an ephemeral local PostgreSQL container in the verification workflow.
