"""Conservative project-level analysis of explicitly named Rust module calls.

This intentionally resolves only unambiguous, file-backed functions referred to
as module::function, crate::module::function, or an explicit use import.
It does NOT perform Rust name resolution, trait dispatch, or macro expansion.
"""
import re
from pathlib import Path
from .taint_analyzer import TaintAnalyzer


_USE = re.compile(r"\buse\s+(?:crate::)?(?P<module>[A-Za-z_]\w*(?:::[A-Za-z_]\w*)*)::(?P<name>[A-Za-z_]\w*)\s*;")
_PATH = re.compile(r"^(?:crate::)?(?P<module>[A-Za-z_]\w*(?:::[A-Za-z_]\w*)*)::(?P<name>[A-Za-z_]\w*)$")


class ProjectLinker:
    def __init__(self, root: Path, trees: dict, rules):
        self.root = Path(root)
        self.trees = trees
        self.rules = rules
        self.modules = {}
        self.functions = {}
        self.imports = {}
        self.analyzers = {}
        for path, tree in trees.items():
            relative = path.relative_to(self.root).with_suffix("")
            segments = relative.parts
            if segments[-1] in ("main", "lib"):
                segments = segments[:-1]
            elif segments[-1] == "mod":
                segments = segments[:-1]
            module = "::".join(segments)
            if module:
                self.modules.setdefault(module, []).append(path)
            definitions = {}
            for fn in tree.functions():
                name_node = fn.child_by_field_name("name")
                if name_node is None:
                    continue
                name = tree.text(name_node)
                definitions.setdefault(name, []).append(fn)
            self.functions[path] = {
                name: nodes[0] for name, nodes in definitions.items()
                if len(nodes) == 1
            }
            imports = {}
            for node in tree.walk():
                if node.type == "use_declaration":
                    match = _USE.search(tree.text(node))
                    if match:
                        imports[match["name"]] = match["module"]
            self.imports[path] = imports
            analyzer = TaintAnalyzer(rules)
            analyzer.trace(tree, [])
            self.analyzers[path] = analyzer

    def _target(self, path, function_text):
        match = _PATH.fullmatch(function_text)
        if match:
            module, name = match["module"], match["name"]
        else:
            module = self.imports[path].get(function_text)
            name = function_text
        if module is None:
            return None
        files = self.modules.get(module, [])
        if len(files) != 1 or files[0] == path:
            return None
        target_path = files[0]
        fn = self.functions[target_path].get(name)
        return (target_path, fn) if fn is not None else None

    def resolve(self):
        links = []
        for path, tree in self.trees.items():
            for call in tree.walk():
                if call.type != "call_expression":
                    continue
                function = call.child_by_field_name("function")
                if function is None or function.type not in (
                    "identifier", "scoped_identifier"
                ):
                    continue
                target = self._target(path, tree.text(function))
                if target is not None:
                    links.append((path, call, *target))

        params = {path: {} for path in self.trees}
        call_returns = {path: {} for path in self.trees}
        # Bounded monotone propagation; recursion never expands indefinitely.
        for _round in range(12):
            for path, analyzer in self.analyzers.items():
                analyzer._external_param_flows = params[path]
                analyzer._external_call_returns = call_returns[path]
                analyzer._defs_cache.clear()

            next_params = {
                path: {key: set(value) for key, value in entries.items()}
                for path, entries in params.items()
            }
            next_calls = {
                path: {key: set(value) for key, value in entries.items()}
                for path, entries in call_returns.items()
            }
            for caller_path, call, target_path, target_fn in links:
                caller_tree = self.trees[caller_path]
                caller_analyzer = self.analyzers[caller_path]
                caller_fn = caller_analyzer._enclosing_function(call)
                args = call.child_by_field_name("arguments")
                if caller_fn is None or args is None:
                    continue
                names = caller_analyzer._parameter_names(
                    self.trees[target_path], target_fn
                )
                for name, arg in zip(names, args.named_children):
                    if name is None:
                        continue
                    defs = caller_analyzer._defs(caller_tree, caller_fn, arg.start_byte)
                    flows = caller_analyzer._flow(caller_tree, arg, defs, frozenset())
                    next_params[target_path].setdefault(
                        (target_fn.start_byte, name), set()
                    ).update(flows)

                # Evaluate a helper's returned value with the current
                # project-wide parameter flows, then feed its callers.
                target_tree = self.trees[target_path]
                target_analyzer = self.analyzers[target_path]
                body = target_fn.child_by_field_name("body")
                if body is None:
                    continue
                expressions = []
                for node in target_tree.walk(body):
                    if node.type == "return_expression":
                        expressions.extend(node.named_children)
                if body.named_children:
                    last = body.named_children[-1]
                    if last.type not in (
                        "expression_statement", "let_declaration",
                        "return_expression"
                    ):
                        expressions.append(last)
                for expr in expressions:
                    defs = target_analyzer._defs(
                        target_tree, target_fn, expr.start_byte
                    )
                    flow = target_analyzer._flow(
                        target_tree, expr, defs, frozenset()
                    )
                    next_calls[caller_path].setdefault(
                        call.start_byte, set()
                    ).update(flow)

            updated_params = {
                p: {k: sorted(v, key=lambda x: (x[0].value, x[1]))
                    for k, v in entries.items()}
                for p, entries in next_params.items()
            }
            updated_calls = {
                p: {k: sorted(v, key=lambda x: (x[0].value, x[1]))
                    for k, v in entries.items()}
                for p, entries in next_calls.items()
            }
            if updated_params == params and updated_calls == call_returns:
                break
            params, call_returns = updated_params, updated_calls
        return params, call_returns
