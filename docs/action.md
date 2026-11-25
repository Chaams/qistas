# GitHub Action

```yaml
permissions:
  contents: read
  pull-requests: write   # needed for the PR comment

steps:
  - uses: actions/checkout@v4
  - uses: Chaams/qistas@v1
    with:
      config: qistas.yaml
      target-url: ${{ steps.preview.outputs.url }}   # bot built from this PR
    env:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

## Which bot gets tested

The gate only means something if it tests the bot built from the pull request. You have two ways to do that:

1. **`target-url`**: the URL of the PR's preview deployment (Vercel, Netlify, Render…), produced by an earlier step. Add `health-url` if the preview needs time to start.
2. **`start-command` + `health-url`**: the Action starts the bot inside the job (`docker compose up -d bot`, `uvicorn app:app`…), waits until `health-url` responds (120 s max), runs the evaluation, then stops the bot.

If you provide neither, Qistas calls the fixed `target.url` from `qistas.yaml`. The report then warns that the PR's code may not be what is being tested.

## Inputs

| Input | Default | Role |
|---|---|---|
| `config` | `qistas.yaml` | Configuration file |
| `target-url` | — | Overrides `target.url` |
| `start-command` | — | Starts the bot in the job |
| `health-url` | — | Polled until the bot responds |
| `baseline` | `baseline.json` | Reference to compare against |
| `judge-provider` | *(empty)* | Extra to install; empty = `judge.provider` from the config |
| `concurrency` | `4` | Cases evaluated in parallel (`1` on a free-tier quota) |
| `offline` | `false` | No LLM judge (rules and lexical checks only) |
| `version` | *(empty)* | Qistas version from PyPI; empty = the action's own source |
| `comment` | `true` | Posts or updates the comment marked `<!-- qistas-report -->` |

Output: `passed` (`true`, `false` or `skipped`).

Qistas runs in its own Python environment (`$RUNNER_TEMP/qistas-venv`) and does not change the job's `python`. The bot started by `start-command` therefore uses your own Python and dependencies. A `kind: python` target, by contrast, is imported into the Qistas environment: in CI, prefer an HTTP target.

## Pull requests from forks

GitHub does not pass secrets to pull requests opened from a fork. Without the judge key, the Action stops with a neutral status (exit code 0) and the message `Qistas skipped: secrets unavailable on fork PRs`. Qistas does **not** use `pull_request_target`, which would run the fork's code with your secrets.

## Updating the baseline

`baseline.json` is never written by the Action. Once a change has been accepted:

```bash
qistas run && qistas baseline update results.json
git add baseline.json && git commit -m "chore: update qistas baseline"
```
