# Security policy

## Supported versions

Security fixes are applied to the latest release on the default branch.

## Reporting a vulnerability

Do not open a public issue containing exploit details, credentials, or private
paths. Use the repository's GitHub private vulnerability reporting or Security
Advisory feature. Include:

- the affected version or commit;
- a minimal, sanitized reproduction;
- the expected and observed result;
- the likely impact.

The project performs static analysis and cannot guarantee that a Skill is safe
at runtime. Treat untrusted Skills as code and inspect every `REVIEW` or `BLOCK`
finding before activation.

The auditor does not require network access and should not install packages,
fonts, or other Skills while auditing a candidate.
