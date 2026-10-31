"""SeverityScorer: classifies a TaintPath as High / Medium / Low (spec 3.3) and explains it.

Scoring uses the three inputs named in the spec: source type, sanitization presence, reachability.

  untrusted data reaches the command, NOT sanitized
      user input / network data            -> High
      env var / file contents              -> Medium, raised to High when a shell is invoked
      untrusted data picks the executable  -> High
  untrusted data reaches the command, sanitized -> Low  (verify the sanitizer)
  no untrusted data, but a shell is invoked     -> Low  (worth a look)
  no untrusted data, plain command              -> not reported
"""
from .models import Severity, SourceKind, TaintPath

_SOURCE_LABEL = {
    SourceKind.USER_INPUT: "user input (stdin / command-line arguments)",
    SourceKind.ENV_VAR: "environment-variable data",
    SourceKind.FILE: "file contents",
    SourceKind.NETWORK: "network data",
}


class SeverityScorer:
    def should_report(self, p: TaintPath) -> bool:
        return p.reachable or p.sink.is_shell_invocation

    def score(self, p: TaintPath) -> Severity:
        if p.reachable and not p.sanitized:
            if p.program_tainted or p.source in (SourceKind.USER_INPUT, SourceKind.NETWORK):
                return Severity.HIGH
            return Severity.HIGH if p.sink.is_shell_invocation else Severity.MEDIUM
        return Severity.LOW

    def reason(self, p: TaintPath) -> str:
        shell = " in a shell invocation" if p.sink.is_shell_invocation else ""
        if p.reachable and not p.sanitized:
            what = _SOURCE_LABEL.get(p.source, "untrusted data")
            if p.program_tainted:
                return f"Unsanitized {what} chooses the program that is executed{shell}."
            return f"Unsanitized {what} reaches a command{shell}."
        if p.reachable:
            what = _SOURCE_LABEL.get(p.source, "untrusted data")
            return f"{what.capitalize()} reaches a command{shell} but passes through a sanitizer; verify it is sufficient."
        return "Shell invocation with no untrusted input detected; any future dynamic argument would be injectable."

    def remediation(self, p: TaintPath) -> str:
        if p.reachable and not p.sanitized:
            if p.program_tainted:
                return "Never let external data pick the program; choose it from a fixed allow-list."
            if p.sink.is_shell_invocation:
                return "Avoid the shell; run the program directly and pass validated values as separate .arg() items."
            return "Validate the value against an allow-list and pass it as its own .arg(); do not build command strings."
        if p.reachable:
            return "Prefer an allow-list over escaping, and pass values as separate .arg() items."
        return "Avoid 'sh -c' / 'cmd /C'; call the program directly with separate .arg() items."
