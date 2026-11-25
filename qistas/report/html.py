"""Standalone HTML report (inline CSS, no external resources)."""
from __future__ import annotations

from jinja2 import Environment, PackageLoader, select_autoescape

from ..gate import GateOutcome
from ..results import RunResult

_env = Environment(loader=PackageLoader("qistas.report", "templates"), autoescape=select_autoescape(["html", "j2"]))


def to_html(result: RunResult, outcome: GateOutcome) -> str:
    return _env.get_template("report.html.j2").render(result=result, outcome=outcome)
