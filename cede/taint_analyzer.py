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


class TaintAnalyzer:
    def __init__(self, rules: DetectionRules | None = None):
        self.rules = rules or DetectionRules()
        self._source_res = [
            (re.compile(r"(?<!\w)" + re.escape(k) + r"(?!\w)"), SourceKind(v))
            for k, v in self.rules.sources.items()
        ]
        self._defs_cache: dict = {}
        # function name defined in this file -> True only for a verified allow-list sanitizer
        self._local_fns: dict[str, bool] = {}
        self._function_nodes: dict = {}
        self._callsites: dict = {}

    # -- public API ---------------------------------------------------------
    def trace(self, tree: SyntaxTree, sinks: list[Sink]) -> list[TaintPath]:
        # Never carry syntax nodes/definitions from one source tree to another.
        self._defs_cache.clear()
        self._local_fns = self._collect_local_fns(tree, sinks)
        self._index_local_calls(tree)
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
                    result[tree.text(name)] = self._body_sanitizes(tree, n)
        return result

    @staticmethod
    def _body_sanitizes(tree: SyntaxTree, fn_item) -> bool:
        """Recognize only the narrow, inspectable alphanumeric filter used by our sample.

        An arbitrary branch, log statement, or function call is NOT proof of
        sanitization. Unknown local helpers fail closed (remain unsanitized).
        """
        body = fn_item.child_by_field_name("body")
        params = fn_item.child_by_field_name("parameters")
        if body is None or params is None:
            return False
        body_text = tree.text(body).strip()
        if not (body_text.startswith("{") and body_text.endswith("}")):
            return False
        expr = re.sub(r"\s+", "", body_text[1:-1])
        match = re.fullmatch(
            r"(?P<src>[A-Za-z_]\w*)\.chars\(\)"
            r"\.filter\(\|(?P<item>[A-Za-z_]\w*)\|"
            r"(?P=item)\.is_(?:ascii_)?alphanumeric\(\)\)"
            r"\.collect\(\);?",
            expr,
        )
        return bool(
            match and re.search(r"\b" + re.escape(match["src"]) + r"\s*:", tree.text(params))
        )

    # -- local function parameter propagation -------------------------------
    def _index_local_calls(self, tree: SyntaxTree) -> None:
        """Index direct local calls only; do not guess the target of methods."""
        groups = {}
        for fn in tree.functions():
            name = fn.child_by_field_name("name")
            if name is not None:
                groups.setdefault(tree.text(name), []).append(fn)
        # Duplicate names across modules cannot safely be resolved here.
        self._function_nodes = {name: nodes[0] for name, nodes in groups.items()
                                if len(nodes) == 1}
        self._callsites = {name: [] for name in self._function_nodes}
        for call in tree.walk():
            if call.type == "call_expression":
                fn = call.child_by_field_name("function")
                if fn is not None and fn.type == "identifier":
                    name = tree.text(fn)
                    if name in self._callsites:
                        self._callsites[name].append(call)

    @staticmethod
    def _enclosing_function(node):
        while node is not None:
            if node.type == "function_item":
                return node
            node = node.parent
        return None

    @staticmethod
    def _parameter_names(tree, fn):
        params = fn.child_by_field_name("parameters")
        if params is None:
            return []
        names = []
        for p in params.named_children:
            if p.type != "parameter":
                continue
            pattern = p.child_by_field_name("pattern")
            if pattern is None:
                pattern = next((n for n in p.named_children
                                if n.type == "identifier"), None)
            names.append(tree.text(pattern) if pattern is not None and
                         pattern.type == "identifier" else None)
        return names

    def _parameter_flow(self, tree, node, name, seen, bindings=None):
        """Propagate values from direct same-file caller arguments into a parameter."""
        fn = self._enclosing_function(node)
        if fn is None:
            return []
        key = (fn.start_byte, name)
        if bindings is not None and key in bindings:
            actual, caller_defs, caller_bindings = bindings[key]
            return self._flow(tree, actual, caller_defs, seen, caller_bindings)
        fn_name = fn.child_by_field_name("name")
        if fn_name is None or self._function_nodes.get(tree.text(fn_name)) != fn:
            return []
        params = self._parameter_names(tree, fn)
        if name not in params:
            return []
        index = params.index(name)
        flows = []
        for call in self._callsites.get(tree.text(fn_name), []):
            args = call.child_by_field_name("arguments")
            if args is None or len(args.named_children) <= index:
                continue
            caller = self._enclosing_function(call)
            if caller is None:
                continue
            actual = args.named_children[index]
            defs = self._defs(tree, caller, actual.start_byte)
            flows += self._flow(tree, actual, defs, seen)
        return flows

    def _local_return_flow(self, tree, call, local_fn, seen, parent_defs, parent_bindings):
        """Follow simple return expressions through a direct same-file call.

        Return values from branches are conservatively combined. Only unique
        direct function names are resolved; imports and traits are not.
        """
        marker = ("return", local_fn.start_byte)
        if marker in seen:
            return []
        args = call.child_by_field_name("arguments")
        body = local_fn.child_by_field_name("body")
        if args is None or body is None:
            return []
        bindings = dict(parent_bindings or {})
        for name, actual in zip(self._parameter_names(tree, local_fn), args.named_children):
            if name is not None:
                bindings[(local_fn.start_byte, name)] = (
                    actual, parent_defs, parent_bindings
                )
        expressions = []
        for node in tree.walk(body):
            if node.type == "return_expression":
                expressions.extend(node.named_children)
        if body.named_children:
            last = body.named_children[-1]
            if last.type not in ("expression_statement", "let_declaration", "return_expression"):
                expressions.append(last)
        flows = []
        for expr in expressions:
            inner_defs = self._defs(tree, local_fn, expr.start_byte)
            flows += self._flow(tree, expr, inner_defs, seen | {marker}, bindings)
        return flows

    # -- per sink -----------------------------------------------------------
    def _trace_sink(self, tree: SyntaxTree, sink: Sink) -> TaintPath:
        if sink.function_node is None:                       # bare "sh -c" string
            return TaintPath(None, sink, sanitized=False, reachable=False)
        # Trace each argument at its own source position, not at Command::new.
        # Builder variables may receive arguments long after construction.
        flows: list[tuple[SourceKind, bool]] = []
        program_tainted = False
        if sink.program_node is not None:
            program_defs = self._defs(tree, sink.function_node, sink.program_node.start_byte)
            program_flows = self._flow(tree, sink.program_node, program_defs, frozenset())
            flows += program_flows
            program_tainted = any(not sanitized for _, sanitized in program_flows)
        sites = sink.arg_sites or [(arg, arg.start_byte) for arg in sink.arg_nodes]
        for arg, position in sites:
            defs = self._defs(tree, sink.function_node, position)
            flows += self._flow(tree, arg, defs, frozenset())
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
    def _flow(self, tree, node, defs, seen, bindings=None):
        out: list[tuple[SourceKind, bool]] = []
        t = node.type

        if t == "call_expression":
            fn = node.child_by_field_name("function")
            fn_text = tree.text(fn) if fn is not None else ""
            sources = [(kind, False) for kind in self._sources_in(fn_text)]
            local_fn = (self._function_nodes.get(fn_text)
                        if fn is not None and fn.type == "identifier" else None)
            if local_fn is not None and not self._is_sanitizer(fn_text):
                return sources + self._local_return_flow(
                    tree, node, local_fn, seen, defs, bindings
                )
            inner = list(sources)
            for child in node.children:
                inner += self._flow(tree, child, defs, seen, bindings)
            if self._is_sanitizer(fn_text):
                return [(k, True) for k, _ in inner]
            return inner

        if t == "scoped_identifier":
            return out

        if t == "identifier":
            parent = node.parent
            if (parent is not None and parent.type == "call_expression"
                    and parent.child_by_field_name("function") == node):
                return out
            name = tree.text(node)
            scope = self._enclosing_function(node)
            marker = ("identifier", scope.start_byte if scope is not None else -1, name)
            if marker not in seen:
                if name in defs:
                    for definition in defs[name]:
                        out += self._flow(tree, definition, defs, seen | {marker}, bindings)
                else:
                    out += self._parameter_flow(tree, node, name, seen | {marker}, bindings)
            return out

        if t == "string_literal" and self._inside_macro(node):
            for name in _INLINE_CAPTURE.findall(tree.text(node)):
                scope = self._enclosing_function(node)
                marker = ("identifier", scope.start_byte if scope is not None else -1, name)
                if marker not in seen:
                    if name in defs:
                        for definition in defs[name]:
                            out += self._flow(tree, definition, defs, seen | {marker}, bindings)
                    else:
                        out += self._parameter_flow(tree, node, name, seen | {marker}, bindings)
            return out

        for child in node.children:
            out += self._flow(tree, child, defs, seen, bindings)
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

        # Visibility of a local declaration is limited to its enclosing block.
        # An inner `let` must not overwrite a different outer binding.
        site = min(
            (n for n in tree.walk(fn)
             if n.start_byte <= cutoff <= n.end_byte),
            key=lambda n: n.end_byte - n.start_byte,
            default=fn,
        )
        visible_blocks = set()
        cursor = site
        while cursor is not None:
            if cursor.type == "block":
                visible_blocks.add(cursor.id)
            cursor = cursor.parent

        def conditional(n):
            parent = n.parent
            while parent is not None and parent != fn:
                if parent.type in ("if_expression", "match_expression",
                                   "while_expression", "for_expression",
                                   "loop_expression"):
                    return True
                parent = parent.parent
            return False

        def add(name, expr):
            defs.setdefault(name, []).append(expr)

        def pattern_names(pattern):
            return [tree.text(n) for n in tree.walk(pattern) if n.type == "identifier"]

        for n in tree.walk(fn):
            if n.start_byte >= cutoff:
                continue
            t = n.type
            if t in ("let_declaration", "let_condition"):
                # Do not leak inner-block shadowed locals into outer scope.
                block = n.parent
                while block is not None and block.type not in ("block", "function_item"):
                    block = block.parent
                if block is not None and block.type == "block" and block.id not in visible_blocks:
                    continue
                pat, val = n.child_by_field_name("pattern"), n.child_by_field_name("value")
                if pat is not None and val is not None:
                    for name in pattern_names(pat):
                        if conditional(n):
                            add(name, val)
                        else:
                            defs[name] = [val]
            elif t in ("assignment_expression", "compound_assignment_expr"):
                left, right = n.child_by_field_name("left"), n.child_by_field_name("right")
                if left is not None and right is not None:
                    for name in pattern_names(left):
                        if t == "assignment_expression" and not conditional(n):
                            defs[name] = [right]
                        else:
                            # A branch/loop may not execute, so merge the
                            # incoming and assigned paths conservatively.
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