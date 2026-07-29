# Contributing

Contributions should improve detection accuracy, reduce false positives, add
portable tests, or document a verified renderer-specific behavior.

## Before submitting

1. Keep the candidate Skill inactive while investigating it.
2. Add a focused test for every rule change.
3. Include both a positive detection case and a nearby safe case when practical.
4. Avoid user-specific paths, credentials, migration data, generated caches,
   and bundled fonts without an explicit redistribution license.
5. Run:

   ```bash
   python skill-install-auditor/tests/test_audit_skill.py
   python tests/test_examples.py
   python tools/check_release.py .
   ```

6. Explain potential false positives and platform assumptions in the pull
   request.

Do not broaden automatic repair behavior without a dry-run diff, explicit
approval, rollback, and a realistic render test.
