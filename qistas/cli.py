"""Command-line interface: `qistas init | run | gate | baseline update`."""
from __future__ import annotations

import sys
from importlib import resources
from pathlib import Path

import typer

from . import __version__

for _stream in (sys.stdout, sys.stderr):  # Arabic output must never crash a cp1252 console
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

app = typer.Typer(help="Quality gate for Arabic LLM applications.", no_args_is_help=True)
baseline_app = typer.Typer(help="Manage baseline.json.")
app.add_typer(baseline_app, name="baseline")

SCAFFOLD = {
    "qistas.yaml": "qistas.yaml",
    "qistas/cases/example.yaml": "example.yaml",
    ".github/workflows/qistas.yml": "qistas.yml",
}


def _version(value: bool) -> None:
    if value:
        typer.echo(f"qistas {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(False, "--version", callback=_version, is_eager=True, help="Show version."),
) -> None:
    """Qistas CLI."""


@app.command()
def init() -> None:
    """Create qistas.yaml, example cases and a GitHub workflow (never overwrites)."""
    for dest, src in SCAFFOLD.items():
        path = Path(dest)
        if path.exists():
            typer.echo(f"skip   {dest} (exists)")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(resources.files("qistas.scaffold").joinpath(src).read_text(encoding="utf-8"), encoding="utf-8")
        typer.echo(f"create {dest}")


def _fail(message: str, code: int = 2) -> None:
    typer.echo(f"qistas: {message}", err=True)
    raise typer.Exit(code)


@app.command()
def run(
    config: Path = typer.Option(Path("qistas.yaml"), "-c", "--config"),
    output: Path = typer.Option(Path("results.json"), "-o", "--output"),
    offline: bool = typer.Option(False, "--offline", help="No LLM judge: lexical and rule-based checks only."),
    target_url: str | None = typer.Option(None, "--target-url", help="Override target.url (e.g. PR preview)."),
    concurrency: int = typer.Option(4, "--concurrency"),
) -> None:
    """Run every case against the bot and write results.json."""
    from .cases import load_cases
    from .config import HttpTarget, load_config
    from .judge import JudgeError, make_judge
    from .runner import run as run_cases
    from .targets import make_target

    try:
        cfg = load_config(config)
        if target_url:
            if not isinstance(cfg.target, HttpTarget):
                _fail("--target-url needs an http target")
            cfg = cfg.model_copy(update={"target": cfg.target.model_copy(update={"url": target_url})})
        cases = load_cases(cfg.cases)
        judge = None if offline else make_judge(cfg.judge)
    except FileNotFoundError as e:
        _fail(f"file not found: {e.filename}")
    except (ValueError, JudgeError) as e:
        _fail(str(e))
    if not cases:
        _fail("no test cases found")

    target = make_target(cfg.target)
    try:
        target.wait_healthy()
    except TimeoutError as e:
        _fail(str(e), code=3)

    typer.echo(f"Qistas: {len(cases)} cas, juge {'hors ligne' if judge is None else judge.model}")
    result = run_cases(cfg, cases, target, judge, concurrency=concurrency)
    result.write(output)
    for c in result.cases:
        bad = c.error or next((m.error or m.reason for m in c.metrics if m.error or m.passed is False), None)
        if bad:
            typer.echo(f"  ✗ {c.id}: {bad} — {c.answer[:80]}")
    typer.echo(f"→ {output} ({result.errors} erreur(s), {result.security['failures']} échec(s) sécurité)")


@app.command()
def gate(
    results: Path = typer.Argument(..., exists=True, dir_okay=False),
    baseline: Path = typer.Option(Path("baseline.json"), "--baseline"),
    config: Path = typer.Option(Path("qistas.yaml"), "-c", "--config"),
    report_md: Path | None = typer.Option(None, "--report-md"),
    report_html: Path | None = typer.Option(None, "--report-html"),
) -> None:
    """Apply thresholds and baseline regression. Exit 0 = PASS, 1 = FAIL."""
    from .baseline import load_baseline
    from .config import GateConfig, load_config
    from .gate import evaluate
    from .report.html import to_html
    from .report.markdown import to_markdown
    from .results import RunResult

    try:
        gate_cfg = load_config(config).gate if config.exists() else GateConfig()
        res = RunResult.read(results)
        base = load_baseline(baseline)
    except ValueError as e:
        _fail(str(e))
    outcome = evaluate(res, base, gate_cfg)
    md = to_markdown(res, outcome, base, thresholds=gate_cfg.thresholds)
    if report_md:
        report_md.write_text(md, encoding="utf-8")
    if report_html:
        report_html.write_text(to_html(res, outcome), encoding="utf-8")
    typer.echo(md)
    raise typer.Exit(0 if outcome.passed else 1)


@baseline_app.command("update")
def baseline_update(
    results: Path = typer.Argument(..., exists=True, dir_okay=False),
    output: Path = typer.Option(Path("baseline.json"), "-o", "--output"),
) -> None:
    """Write baseline.json from a results file (commit it afterwards)."""
    from .baseline import write_baseline
    from .results import RunResult

    write_baseline(RunResult.read(results), output)
    typer.echo(f"baseline written to {output} — commit it to make it the new reference")
