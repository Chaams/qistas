"""Mirror of the GitHub Action flow: start the bot, wait for health, run, gate."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_action_flow_against_http_echo_bot(tmp_path):
    bot = subprocess.Popen([sys.executable, "-m", "tests.fixtures.http_echo_bot"], cwd=ROOT)
    try:
        out = tmp_path / "results.json"
        run = subprocess.run([sys.executable, "-m", "qistas", "run", "--offline", "-c", "tests/selftest/qistas.yaml",
                              "-o", str(out)], cwd=ROOT, capture_output=True, timeout=60)
        assert run.returncode == 0, run.stderr.decode("utf-8", "replace")
        assert json.loads(out.read_text(encoding="utf-8"))["security"]["failed_ids"] == ["selftest-echo-leak"]
        gate = subprocess.run([sys.executable, "-m", "qistas", "gate", str(out), "-c", "tests/selftest/qistas.yaml",
                               "--baseline", str(tmp_path / "none.json")], cwd=ROOT, capture_output=True, timeout=60)
        assert gate.returncode == 1
    finally:
        bot.terminate()
        bot.wait(timeout=10)
