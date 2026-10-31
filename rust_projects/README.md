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

## Conventional Cargo examples

Projects `21_cargo_user_shell` through `30_cargo_static_shell` use standard
`Cargo.toml` and `src/` layouts, alongside the earlier minimal modules.
They are provided for CEDE parsing and project scans, not as dependencies or
complete runnable applications.

In the GUI, select **one numbered project directory at a time**. Scanning the
entire `rust_projects/` parent as one giant project is not equivalent to 30
independent projects and can introduce module-name collisions.
