
"""SinkDetector: identifies command-execution calls and shell invocations (spec 3.1).

Shell strings are only considered suspicious when associated with
an actual command-execution API, not when appearing in documentation
or ordinary string variables.
"""

from .detection_rules import DetectionRules
from .models import Sink
from .rust_parser import SyntaxTree


_CHAIN_METHODS = {
    "arg", "args", "env", "envs",
    "current_dir", "spawn", "output", "status"
}


class SinkDetector:
    def __init__(self, rules: DetectionRules | None = None):
        self.rules = rules or DetectionRules()

    def find_sinks(self, tree: SyntaxTree) -> list[Sink]:
        sinks: list[Sink] = []

        aliases = self._command_aliases(tree)
        for fn in tree.functions():
            for call in tree.calls_in(fn):
                if self._is_command_new(tree, call, aliases):
                    sinks.append(self._build_sink(tree, call, fn))

        # Do not independently report arbitrary shell-like strings.
        # Shell execution is identified through actual Command::new calls.
        return sorted(sinks, key=lambda s: s.line)

    # -- Command::new(...) chains ----------------------------

    @staticmethod
    def _command_aliases(tree) -> set[str]:
        import re
        aliases = set()
        for node in tree.walk():
            if node.type != "use_declaration":
                continue
            text = tree.text(node)
            for name in re.findall(
                r"\b(?:std::process::|process::)Command\s+as\s+([A-Za-z_]\w*)",
                text,
            ):
                aliases.add(name)
        return aliases

    def _is_command_new(self, tree, call, aliases: set[str]) -> bool:
        fn = call.child_by_field_name("function")
        if fn is None or fn.type != "scoped_identifier":
            return False
        text = tree.text(fn)
        return (
            any(text == api or text.endswith("::" + api) for api in self.rules.sink_apis)
            or any(text == alias + "::new" for alias in aliases)
        )

    def _build_sink(self, tree, call, fn_node) -> Sink:
        args = call.child_by_field_name("arguments")
        program = (
            args.named_children[0]
            if args is not None and args.named_children
            else None
        )

        node, last, methods, arg_nodes, arg_sites = call, call, [], [], []

        while True:
            parent = node.parent

            if (
                parent is None
                or parent.type != "field_expression"
                or parent.child_by_field_name("value") != node
            ):
                break

            outer = parent.parent

            if (
                outer is None
                or outer.type != "call_expression"
                or outer.child_by_field_name("function") != parent
            ):
                break

            name = tree.text(
                parent.child_by_field_name("field")
            )
            methods.append(name)

            if name in ("arg", "args"):
                a = outer.child_by_field_name("arguments")
                if a is not None:
                    for expr in a.named_children:
                        values = self._expand_args(expr) if name == "args" else [expr]
                        for value in values:
                            arg_nodes.append(value)
                            arg_sites.append((value, value.start_byte))

            if name in _CHAIN_METHODS:
                last = outer

            node = outer

        # Track calls made through a stored command variable.
        extra_args, extra_methods, extra_sites = self._linked_variable_calls(
            tree, last, fn_node
        )

        arg_nodes += extra_args
        methods += extra_methods
        arg_sites += extra_sites

        return Sink(
            line=call.start_point[0] + 1,
            api=" ".join(tree.text(last).split()),
            is_shell_invocation=self._is_shell(
                tree, program, arg_nodes
            ),
            node=last,
            program_node=program,
            arg_nodes=arg_nodes,
            arg_sites=arg_sites,
            methods=methods,
            function_node=fn_node,
        )

    def _linked_variable_calls(self, tree, chain_end, fn_node):
        var = self._bound_name(tree, chain_end)

        if var is None:
            return [], [], []

        args, methods, sites = [], [], []

        for call in sorted(tree.calls_in(fn_node), key=lambda n: n.start_byte):
            # A later .arg() cannot change a command that has already run.
            if call.start_byte <= chain_end.end_byte:
                continue
            f = call.child_by_field_name("function")

            if f is None or f.type != "field_expression":
                continue

            target = f.child_by_field_name("value")

            if (
                target is None
                or target.type != "identifier"
                or tree.text(target) != var
            ):
                continue

            name = tree.text(
                f.child_by_field_name("field")
            )

            if name not in _CHAIN_METHODS:
                continue

            methods.append(name)
            if name in self.rules.spawn_methods:
                break

            if name in ("arg", "args"):
                a = call.child_by_field_name("arguments")
                if a is not None:
                    for expr in a.named_children:
                        values = self._expand_args(expr) if name == "args" else [expr]
                        for value in values:
                            args.append(value)
                            sites.append((value, value.start_byte))

        return args, methods, sites

    @staticmethod
    def _expand_args(expr):
        # Only split array literals. Other iterables retain their original expression.
        if expr.type == "array_expression":
            return list(expr.named_children)
        if expr.type == "reference_expression":
            inner = next((c for c in expr.named_children if c.type == "array_expression"), None)
            if inner is not None:
                return list(inner.named_children)
        return [expr]

    @staticmethod
    def _bound_name(tree, chain_end) -> str | None:
        node = chain_end.parent

        while node is not None and node.type != "function_item":
            if node.type == "let_declaration":
                value = node.child_by_field_name("value")
                pattern = node.child_by_field_name("pattern")

                if (
                    value is not None
                    and pattern is not None
                    and value.start_byte <= chain_end.start_byte
                    and chain_end.end_byte <= value.end_byte
                ):
                    ids = [
                        n for n in tree.walk(pattern)
                        if n.type == "identifier"
                    ]
                    return tree.text(ids[0]) if ids else None

                return None

            if node.type in ("block", "expression_statement"):
                return None

            node = node.parent

        return None

    def _is_shell(self, tree, program, arg_nodes) -> bool:
        if program is None or program.type != "string_literal":
            return False

        exe = (
            tree.text(program)
            .strip('"')
            .replace("\\", "/")
            .rsplit("/", 1)[-1]
            .lower()
        )

        if exe.endswith(".exe"):
            exe = exe[:-4]

        shells = {
            p.lower().removesuffix(".exe")
            for p in self.rules.shell_patterns
        }

        if exe not in shells:
            return False

        flags = {
            f.lower()
            for f in self.rules.shell_flags
        }

        return any(
            a.type == "string_literal"
            and tree.text(a).strip('"').lower() in flags
            for a in arg_nodes
        )
