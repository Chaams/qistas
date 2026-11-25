from typer.testing import CliRunner

from qistas.cli import app


def test_version():
    r = CliRunner().invoke(app, ["--version"])
    assert r.exit_code == 0 and "0.1.0.dev0" in r.stdout
