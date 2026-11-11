# Contributing

Bug reports and small, focused pull requests are welcome. Include a minimal
synthetic example, the expected output and your Python/OS version. Never attach
your private vault or credentials.

Run `python -m unittest -v` and `python brainkit.py --root examples check` before
submitting. Keep the core dependency-free, read-only except for `note` and `release`, and
portable across Windows, macOS and Linux. Add regression tests for parser changes.

Useful next contributions: nested handoff layouts, validated heading anchors,
optional JSON context output, and better handling of Markdown edge cases.

## Reporting sensitive issues

Do not post private data or exploitable credential material in public issues.
Use GitHub's private vulnerability reporting if enabled, or describe the problem
without the sensitive payload. There is no guaranteed response-time SLA.
