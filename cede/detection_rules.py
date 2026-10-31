"""DetectionRules: what counts as a sink, a shell string, a source, or a sanitizer."""
from dataclasses import dataclass, field, fields, asdict
from pathlib import Path
import json
from .models import SourceKind


@dataclass
class DetectionRules:
    sink_apis: list[str] = field(default_factory=lambda: ["Command::new"])
    spawn_methods: list[str] = field(default_factory=lambda: ["spawn", "output", "status"])
    shell_patterns: list[str] = field(default_factory=lambda: ["sh", "bash", "cmd", "cmd.exe", "powershell"])
    shell_flags: list[str] = field(default_factory=lambda: ["-c", "/C", "/c", "-Command"])
    sanitizers: list[str] = field(default_factory=lambda: ["shell_escape", "shlex::quote", "validate", "sanitize", "escape"])
    # (substring in expression text) -> SourceKind name; used in step 4
    sources: dict[str, str] = field(default_factory=lambda: {
        "std::env::args": "UserInput", "env::args": "UserInput", "stdin": "UserInput", "read_line": "UserInput",
        "env::var": "EnvVar", "read_to_string": "File", "fs::read": "File",
        "TcpStream": "Network", "reqwest": "Network", "recv": "Network",
    })

    def __post_init__(self):
        for field_name in ("sink_apis", "spawn_methods", "shell_patterns",
                           "shell_flags", "sanitizers"):
            values = getattr(self, field_name)
            if not isinstance(values, list) or any(
                not isinstance(value, str) or not value for value in values
            ):
                raise ValueError(f"{field_name} must be a list of nonempty strings")
        if not isinstance(self.sources, dict) or any(
            not isinstance(key, str) or not key or not isinstance(value, str)
            or value not in {kind.value for kind in SourceKind}
            for key, value in self.sources.items()
        ):
            raise ValueError("sources must map nonempty strings to valid SourceKind values")

    @classmethod
    def load(cls, path: Path) -> "DetectionRules":
        """Load overrides from a JSON file; keys not present keep their defaults."""
        data = json.loads(Path(path).read_text())
        if not isinstance(data, dict):
            raise ValueError("rules file must contain a JSON object")
        known = {f.name for f in fields(cls)}
        unknown = set(data) - known
        if unknown:
            raise ValueError(f"unknown rule keys: {', '.join(sorted(unknown))}")
        return cls(**data)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    def save(self, path: Path) -> None:
        Path(path).write_text(self.to_json() + "\n")
