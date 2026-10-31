"""RustParser: builds a real syntax tree (tree-sitter) so comments and doc strings never match.

Stands in for the `syn` crate named in the SDS.
"""
from pathlib import Path
import tree_sitter_rust
from tree_sitter import Language, Parser, Node
from .models import ParseError

_LANG = Language(tree_sitter_rust.language())


class SyntaxTree:
    def __init__(self, source: str, tree):
        self.source = source
        self.source_bytes = source.encode("utf-8")
        self.root: Node = tree.root_node

    def text(self, node: Node) -> str:
        return self.source_bytes[node.start_byte:node.end_byte].decode("utf-8", "replace")

    def walk(self, node: Node | None = None):
        """Yield every node depth-first. Comments are skipped entirely (spec 2.2)."""
        node = node or self.root
        if node.type in ("line_comment", "block_comment"):
            return
        yield node
        for child in node.children:
            yield from self.walk(child)

    def functions(self) -> list[Node]:
        return [n for n in self.walk() if n.type == "function_item"]

    def calls_in(self, fn: Node) -> list[Node]:
        return [n for n in self.walk(fn) if n.type == "call_expression"]


class RustParser:
    def __init__(self):
        self._parser = Parser(_LANG)

    def parse(self, source: str, path: Path) -> SyntaxTree:
        tree = self._parser.parse(source.encode("utf-8"))
        err = self._first_error(tree.root_node)
        if err is not None:
            kind = "missing " + err.type if err.is_missing else "unexpected syntax"
            raise ParseError(path, err.start_point[0] + 1, kind)
        return SyntaxTree(source, tree)

    def _first_error(self, node: Node) -> Node | None:
        if not node.has_error:
            return None
        if node.type == "ERROR" or node.is_missing:
            return node
        for child in node.children:
            found = self._first_error(child)
            if found is not None:
                return found
        return node
