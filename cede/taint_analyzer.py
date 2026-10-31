"""TaintAnalyzer: traces untrusted input to command-execution sinks (spec 3.2).

Order-aware (for straight-line code), intra-procedural analysis inside each function:
  * sources  : calls matching DetectionRules.sources (stdin, env::args, env::var, fs reads, network)
  * propagate: let / assignment / for-loop / push_str-style mutators / `&mut x` out-params
               / format!-style macros (including inline `{name}` captures)
  * sanitizers: a call matching DetectionRules.sanitizers marks everything flowing through it as sanitized.
               If that function is defined in the scanned file, its body must do real work
               (not just return its input); passthrough bodies are never trusted.
Function parameters are NOT treated as sources (not one of the SDS source kinds).
"""
import re
from .detection_rules import DetectionRules
from .models import Sink, SourceKind, TaintPath
from .rust_parser import SyntaxTree

# most dangerous first
_PRIORITY = [SourceKind.USER_INPUT, SourceKind.NETWORK, SourceKind.ENV_VAR, SourceKind.FILE]
_MUTATORS = {"push", "push_str", "extend", "insert", "append", "write_str"}
_INLINE_CAPTURE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)")
_PATH_SPLIT = re.compile(r"::|\.")
# Calls that return the same data unchanged; they do not make a function a sanitizer.
_IDENTITY_CALLS = {
    "to_string", "clone", "to_owned", "into", "from", "as_str", "to_str", "as_ref",
    "unwrap", "expect", "chars", "bytes", "as_bytes", "iter", "into_iter", "collect", "to_vec",
}
# Control flow that suggests the body checks or branches on its input.
_CHECK_NODES = {"if_expression", "match_expression", "while_expression", "macro_invocation"}


class TaintAnalyzer:
    def __init__(self, rules: DetectionRules | None = None):
        self.rules = rules or DetectionRules()
        self._source_res = [
            (re.compile(r"(?<!\w)" + re.escape(k) + r"(?!\w)"), SourceKind(v))
            for k, v in self.rules.sources.items()
        ]
        self._defs_cache: dict = {}
        # function name defined in the scanned file -> True if its body does real work
        self._local_fns: dict[str, bool] = {}

    # -- public API ---------------------------------------------------------
    def trace(self, tree: SyntaxTree, sinks: list[Sink]) -> list[TaintPath]:
        # Never carry syntax nodes/definitions from one source tree to another.
        self._defs_cache.clear()
        self._local_fns = self._collect_local_fns(tree, sinks)
        return [self._trace_sink(tree, s) for s in sinks]

    def _collect_local_fns(self, tree: SyntaxTree, sinks: list[Sink]) -> dict[str, bool]:
        """Every function defined in the scanned file, mapped to whether its body does real work."""
        fn = next((s.function_node for s in sinks if s.function_node is not None), None)
        if fn is None:
            return {}
        root = fn
        while root.parent is not None:
            root = root.parent
        result: dict[str, bool] = {}
        for n in tree.walk(root):
            if n.type == "function_item":
                name = n.child_by_field_name("name")
                if name is not None:
                    result[tree.text(name)] = self._body_does_work(tree, n)
        return result

    @staticmethod
    def _body_does_work(tree: SyntaxTree, fn_item) -> bool:
        """False for passthrough bodies (return the input, or only identity-style calls)."""
        body = fn_item.child_by_field_name("body")
        if body is None:
            return False
        for n in tree.walk(body):
            if n.type in _CHECK_NODES:
                return True
            if n.type == "call_expression":
                f = n.child_by_field_name("function")
                last = _PATH_SPLIT.split(tree.text(f))[-1] if f is not None else ""
                if last not in _IDENTITY_CALLS:
                    return True
        return False

    # -- per sink -----------------------------------------------------------
    def _trace_sink(self, tree: SyntaxTree, sink: Sink) -> TaintPath:
        if sink.function_node is None:                       # bare "sh -c" string
            return TaintPath(None, sink, sanitized=False, reachable=False)
        # Only include definitions that precede this command call.
        defs = self._defs(tree, sink.function_node, sink.node.start_byte)
        exprs = ([sink.program_node] if sink.program_node is not None else []) + list(sink.arg_nodes)
        flows: list[tuple[SourceKind, bool]] = []
        for e in exprs:
            flows += self._flow(tree, e, defs, frozenset())
        program_tainted = False
        if sink.program_node is not None:
            program_tainted = any(not s for _, s in self._flow(tree, sink.program_node, defs, frozenset()))
        unsanitized = [k for k, s in flows if not s]
        sanitized = [k for k, s in flows if s]
        if unsanitized:
            return TaintPath(self._worst(unsanitized), sink, sanitized=False, reachable=True, program_tainted=program_tainted)
        if sanitized:
            return TaintPath(self._worst(sanitized), sink, sanitized=True, reachable=True)
        return TaintPath(None, sink, sanitized=False, reachable=False)

    @staticmethod
    def _worst(kinds):
        return min(kinds, key=_PRIORITY.index)

    # -- expression flow ----------------------------------------------------
    def _flow(self, tree, node, defs, seen):
        out: list[tuple[SourceKind, bool]] = []
        t = node.type

        if t == "call_expression":
            fn = node.child_by_field_name("function")
            fn_text = tree.text(fn) if fn is not None else ""
            inner: list[tuple[SourceKind, bool]] = []
            for kind in self._sources_in(fn_text):
                inner.append((kind, False))
            for child in node.children:
                inner += self._flow(tree, child, defs, seen)
            if self._is_sanitizer(fn_text):
                return [(k, True) for k, _ in inner]
            return inner

        if t == "scoped_identifier":
            return out

        if t == "identifier":
            parent = node.parent
            if parent is not None and parent.type == "call_expression" and parent.child_by_field_name("function") == node:
                return out
            name = tree.text(node)
            if name not in seen:
                for d in defs.get(name, []):
                    out += self._flow(tree, d, defs, seen | {name})
            return out

        if t == "string_literal" and self._inside_macro(node):
            for name in _INLINE_CAPTURE.findall(tree.text(node)):
                if name not in seen:
                    for d in defs.get(name, []):
                        out += self._flow(tree, d, defs, seen | {name})
            return out

        for child in node.children:
            out += self._flow(tree, child, defs, seen)
        return out

    @staticmethod
    def _inside_macro(node) -> bool:
        p = node.parent
        while p is not None:
            if p.type == "macro_invocation":
                return True
            if p.type in ("function_item", "block"):
                return False
            p = p.parent
        return False

    def _sources_in(self, text: str):
        return [kind for rx, kind in self._source_res if rx.search(text)]

    def _is_sanitizer(self, fn_text: str) -> bool:
        # A function defined in this file is trusted only if its body does real work.
        last = _PATH_SPLIT.split(fn_text)[-1]
        if last in self._local_fns and not self._local_fns[last]:
            return False
        return any(fn_text == s or fn_text.endswith("::" + s) or fn_text.endswith("." + s)
                   for s in self.rules.sanitizers)

    # -- definitions inside a function -------------------------------------
    def _defs(self, tree, fn, cutoff):
        key = (fn.start_byte, fn.end_byte, cutoff)
        if key in self._defs_cache:
            return self._defs_cache[key]
        defs: dict[str, list] = {}

        def add(name, expr):
            defs.setdefault(name, []).append(expr)

        def pattern_names(pattern):
            return [tree.text(n) for n in tree.walk(pattern) if n.type == "identifier"]

        for n in tree.walk(fn):
            if n.start_byte >= cutoff:
                continue
            t = n.type
            if t in ("let_declaration", "let_condition"):
                pat, val = n.child_by_field_name("pattern"), n.child_by_field_name("value")
                if pat is not None and val is not None:
                    for name in pattern_names(pat):
                        defs[name] = [val]
            elif t in ("assignment_expression", "compound_assignment_expr"):
                left, right = n.child_by_field_name("left"), n.child_by_field_name("right")
                if left is not None and right is not None:
                    for name in pattern_names(left):
                        if t == "assignment_expression":
                            defs[name] = [right]
                        else:
                            add(name, right)
            elif t == "for_expression":
                pat, val = n.child_by_field_name("pattern"), n.child_by_field_name("value")
                if pat is not None and val is not None:
                    for name in pattern_names(pat):
                        add(name, val)
            elif t == "call_expression":
                f = n.child_by_field_name("function")
                args = n.child_by_field_name("arguments")
                if args is None:
                    continue
                # v.push_str(x)  ->  v depends on x
                if f is not None and f.type == "field_expression":
                    target = f.child_by_field_name("value")
                    method = tree.text(f.child_by_field_name("field"))
                    if method in _MUTATORS and target is not None and target.type == "identifier":
                        for a in args.named_children:
                            add(tree.text(target), a)
                # stdin().read_line(&mut x)  ->  x depends on the whole call
                for a in args.named_children:
                    if a.type == "reference_expression" and "mutable_specifier" in [c.type for c in a.children]:
                        ids = [i for i in tree.walk(a) if i.type == "identifier"]
                        if ids:
                            add(tree.text(ids[0]), n)
        self._defs_cache[key] = defs
        return defs