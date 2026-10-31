# Multi-file Rust test projects

Each numbered directory is a deliberately small Rust module project, with a
labeled expected set of CEDE findings in \`manifest.json\`.

Run:
\`\`\`
python -m pytest tests/test_rust_projects.py -q
\`\`\`

These cases cover file-qualified function calls, explicit imports, nested
module paths, return-value propagation, safe lookalikes, and multiple findings.

The files are parser fixtures and do not execute the suspicious commands.
Their layout is intentionally simplified (rather than full Cargo scaffolding);
compilation, ownership checking, and macro expansion are outside the scope
of these fixture tests. Ground-truth severities are reviewed expectations,
not independently verified exploitability.
