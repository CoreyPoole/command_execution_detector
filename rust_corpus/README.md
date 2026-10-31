# Expanded Rust regression corpus

The \`rust_corpus/\` directory contains small, individually labeled Rust source
fixtures designed for testing CEDE's **static parser and detector**.

* \`safe/\`: fixed commands and misleading lookalikes that should not trigger
* \`advisory/\`: static shell commands and configured sanitizers (Low)
* \`high/\`: user/network data in command execution (High)
* \`medium/\`: environment/file data supplied to a fixed executable (Medium)
* \`flow/\`: assignments, formatting, shadowing, local functions, builders
* \`invalid/\`: deliberately malformed syntax that must raise ParseError

\`manifest.json\` defines the expected severity for each case. Run:
\`\`\`
python -m pytest tests/test_rust_corpus.py -q
python -m pytest tests -q
\`\`\`

All samples are source fixtures: **do not run them**, especially those with
user-controlled shell commands. Some examples refer to optional crates
(e.g. reqwest or shlex), so the corpus tests Rust syntax / CEDE detection, not
compilation of each fixture into an executable.

These are intentionally curated regression cases. The fact that CEDE passes
this corpus does **not** measure its sensitivity to real, unseen vulnerabilities.
Add independently reviewed positive/negative cases before drawing broader
accuracy conclusions. A change to a fixture's expected label needs review:
never silently relabel failures to make a green CI run.
