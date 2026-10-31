# Real-world scan validation

The GitHub Actions workflow \`Scan real-world Rust projects\` clones three
**tag-pinned** upstream projects (ripgrep 14.1.1, fd 10.2.0, hyperfine 1.18.0)
and parses their Rust source without compiling or executing it.

It stores individual JSON reports plus a summary as downloadable workflow
artifacts. Findings require human review before calling them vulnerabilities.
Project totals and unreviewed reports cannot establish precision or recall;
the curated fixture benchmark is a separate regression check.

This job may expose unsupported Rust syntax, analysis performance issues, or
false positives and should remain useful as a real-world smoke test.
