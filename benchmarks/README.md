# Curated security benchmark

Run `python -m cede.benchmark` to measure binary precision and recall on the
manifest-labeled Rust fixtures. High and Medium findings count as actionable;
Low is advisory. Each fixture has a human-authored expected severity.

**Important:** these are small synthetic regression examples designed around
CEDE's supported patterns. High scores on them do **not** establish real-world
detection precision, security, or recall. For an independent evaluation, use
unseen, reviewed Rust repositories with documented ground truth and freeze
the rules before evaluating.

The runner returns nonzero if expected and observed severity disagree.
