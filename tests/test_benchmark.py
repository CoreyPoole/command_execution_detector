"""Labeled fixture benchmark. These fixtures are not an independent real-world sample."""
from cede.benchmark import evaluate


def test_curated_corpus_classifications():
    result = evaluate()
    assert result["cases"] >= 12
    assert result["severity_mismatches"] == []
    assert result["precision"] == 1.0
    assert result["recall"] == 1.0
