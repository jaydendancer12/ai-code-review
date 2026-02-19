<div align="center">

# 🔍 codereview

**AI-powered code review in your terminal.**

One command. Instant feedback. Catches security vulnerabilities, bugs, and bad patterns before they hit production.

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://github.com/jaydendancer12/ai-code-review/actions/workflows/test.yml/badge.svg)](https://github.com/jaydendancer12/ai-code-review/actions)

[Install](#install) · [Quick Start](#quick-start-free-60-seconds) · [Usage](#usage) · [Providers](#providers) · [Contributing](#contributing)

</div>

---

## What It Does

codereview sends your code to an LLM and returns a structured, color-coded review directly in your terminal — with severity ratings, line references, and concrete fix suggestions.

No browser. No PR required. No waiting for teammates. Just:

~~~bash
codereview app.py
~~~

### Catching real security vulnerabilities — scored 2/10

<img width="933" height="655" alt="bad-code-review" src="https://github.com/user-attachments/assets/17e67488-9952-4cd8-be25-f04d4735a64a" />


### Reviewing its own source code — scored 9/10

<img width="915" height="619" alt="self-review" src="https://github.com/user-attachments/assets/fe4e5489-c1bc-4954-8118-03339a5f99a7" />

---

## Why

- **Solo developers** — get a second pair of eyes without waiting for anyone
- **Pre-commit check** — catch bugs before they reach the PR
- **Learning tool** — understand *why* code is problematic, not just *that* it is
- **CI integration** — add to your pipeline for automated review gates
- **Free** — works with Groq (free tier, no credit card) or fully offline with Ollama

---

## What It Catches

| Severity | What it finds | Example |
|----------|--------------|---------|
| 🔴 **Critical** | Security vulnerabilities, data loss, crashes | SQL injection, eval() on user input, hardcoded secrets |
| 🟡 **Warning** | Bugs, missing error handling, race conditions | Division by zero, unhandled exceptions, resource leaks |
| 🔵 **Info** | Performance improvements, better patterns | Unnecessary allocations, missing caching, N+1 queries |
| ⚪ **Style** | Naming, formatting, documentation | Missing docstrings, inconsistent naming, dead code |

---

## Install

### From source (recommended)

~~~bash
git clone https://github.com/jaydendancer12/ai-code-review.git
cd ai-code-review
./install.sh
~~~

Or manually:

~~~bash
git clone https://github.com/jaydendancer12/ai-code-review.git
cd ai-code-review
pip install -e .
~~~

All dependencies (rich, requests) install automatically. Nothing else to configure.

---

## Quick Start (free, 60 seconds)

codereview needs an LLM to analyze your code. The fastest free option is **Groq** — no credit card, no trial, just free.

### Step 1 — Get a free API key

1. Go to **[console.groq.com](https://console.groq.com)**
2. Sign up with Google or GitHub (takes 30 seconds)
3. Click **API Keys** then **Create API Key**
4. Copy the key (starts with gsk_)

### Step 2 — Set your key

~~~bash
export GROQ_API_KEY="gsk_your_key_here"
~~~

To make it permanent (so you don't have to set it every terminal session):

~~~bash
# For zsh (default on Mac)
echo 'export GROQ_API_KEY="gsk_your_key_here"' >> ~/.zshrc
source ~/.zshrc

# For bash (default on Linux)
echo 'export GROQ_API_KEY="gsk_your_key_here"' >> ~/.bashrc
source ~/.bashrc
~~~

### Step 3 — Initialize

~~~bash
codereview --init groq
~~~

### Step 4 — Review code

~~~bash
codereview yourfile.py
~~~

That's it. You're running AI code reviews.

> **First time running?** Just type codereview with no arguments and it will walk you through the entire setup.

---

## Usage

### Review a file

~~~bash
codereview app.py
~~~

### Review multiple files

~~~bash
codereview src/auth.py src/db.py src/api.py
~~~

### Review staged git changes (pre-commit)

~~~bash
git add .
codereview --staged
~~~

### Review the last N commits

~~~bash
codereview --last 3
~~~

### Review diff between branches

~~~bash
codereview --diff origin/main
~~~

### Pipe code from stdin

~~~bash
cat suspicious_code.py | codereview --stdin
~~~

### Use a specific model

~~~bash
codereview app.py --model gpt-4
~~~

### Use a specific provider for one review

~~~bash
codereview app.py --provider ollama
~~~

### Show setup instructions

~~~bash
codereview --setup
~~~

---

## Providers

codereview works with any OpenAI-compatible API. Pick what works for you:

### ⚡ Groq (recommended — free, fast)

~~~bash
export GROQ_API_KEY="gsk_your_key_here"
codereview --init groq
~~~

- **Cost:** Free tier, no credit card required
- **Speed:** Fastest inference available
- **Model:** Llama 3.3 70B
- **Get a key:** [console.groq.com](https://console.groq.com)

### 🏠 Ollama (free, fully offline)

~~~bash
# 1. Install Ollama
# Mac: Download from https://ollama.com
# Linux: curl -fsSL https://ollama.com/install.sh | sh

# 2. Pull a model
ollama pull llama3

# 3. Start the server
ollama serve

# 4. Initialize (no API key needed)
codereview --init ollama
~~~

- **Cost:** Free forever
- **Speed:** Depends on your hardware
- **Privacy:** Code never leaves your machine
- **Model:** Any model Ollama supports

### 🧠 OpenAI

~~~bash
export OPENAI_API_KEY="sk-..."
codereview --init openai
~~~

- **Cost:** Pay per token
- **Model:** GPT-3.5 Turbo (default), GPT-4 with --model gpt-4
- **Get a key:** [platform.openai.com](https://platform.openai.com)

### 🔮 Anthropic

~~~bash
export ANTHROPIC_API_KEY="sk-ant-..."
codereview --init anthropic
~~~

- **Cost:** Pay per token
- **Model:** Claude 3 Haiku (default)
- **Get a key:** [console.anthropic.com](https://console.anthropic.com)

---

## Configuration

Config is stored at ~/.codereview/config.json:

~~~json
{
  "provider": "groq",
  "model": "llama-3.3-70b-versatile",
  "base_url": "https://api.groq.com/openai/v1",
  "max_tokens": 2048,
  "temperature": 0.2
}
~~~

**API keys are never stored in the config file.** They are read from environment variables only.

### Override anything via environment variables

~~~bash
export CODEREVIEW_API_KEY="any-key"     # Universal override
export CODEREVIEW_MODEL="gpt-4"         # Override model
~~~

### Override via CLI flags

~~~bash
codereview app.py --model gpt-4 --provider openai
~~~

---

## How It Works

~~~
Your Code  -->  codereview CLI  -->  LLM API  -->  Structured Terminal Output
(file/diff)     (prompt builder)    (any provider)  (color-coded findings)
~~~

1. **Input** — codereview reads your file, git diff, staged changes, or stdin
2. **Prompt** — Constructs a focused review prompt with strict rules to prevent hallucinated issues
3. **LLM** — Sends to any OpenAI-compatible API (Groq, OpenAI, Anthropic, Ollama)
4. **Parse** — Extracts structured JSON from the LLM response
5. **Display** — Renders color-coded, severity-sorted findings in your terminal

### What makes this different from ChatGPT

- **Structured output** — Severity ratings, file references, concrete suggestions
- **No hallucinations** — Prompt engineering ensures the LLM only flags issues it can see in your code
- **Works on diffs** — Review only what changed, not the entire codebase
- **One command** — No copy-pasting into a browser
- **Offline capable** — Run with Ollama, your code never leaves your machine
- **Free** — No subscription required

---

## Examples

### Security audit on a suspicious file

~~~
$ codereview api/auth.py

Score: 3/10

🔴 CRITICAL — Hardcoded JWT secret
   Secret key is hardcoded on line 12.
   Suggestion: Use environment variable: os.environ["JWT_SECRET"]

🔴 CRITICAL — No password hashing
   Passwords stored in plaintext on line 34.
   Suggestion: Use bcrypt: bcrypt.hashpw(password, bcrypt.gensalt())

🟡 WARNING — Token never expires
   JWT tokens have no expiration set.
   Suggestion: Add exp claim with timedelta
~~~

### Pre-commit review of staged changes

~~~
$ git add .
$ codereview --staged

Score: 8/10

🔵 INFO — Consider adding error handling
   The new API endpoint doesn't catch ConnectionError.
   Suggestion: Wrap in try/except with retry logic.
~~~

### Review last 3 commits before pushing

~~~
$ codereview --last 3

Score: 9/10

⚪ STYLE — Inconsistent naming
   Mix of snake_case and camelCase in utils.py
   Suggestion: Stick to snake_case per PEP 8.
~~~

---

## Use in CI/CD

Add to your GitHub Actions workflow:

~~~yaml
name: Code Review
on: [pull_request]
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-python@v5
        with:
          python-version: "3.10"
      - run: pip install ai-code-review
      - run: codereview --diff origin/main
        env:
          GROQ_API_KEY: ${{ secrets.GROQ_API_KEY }}
~~~

---

## Project Structure

~~~
ai-code-review/
├── codereview/
│   ├── __init__.py          # Version
│   ├── cli.py               # Command-line interface + first-run setup
│   ├── reviewer.py          # LLM API calls + response parsing
│   ├── formatter.py         # Rich terminal output formatting
│   ├── git_utils.py         # Git diff/file extraction utilities
│   └── config.py            # Configuration management + API key handling
├── tests/
│   ├── test_reviewer.py     # Review parsing tests
│   └── test_git_utils.py    # Git utility tests
├── setup.py
├── pyproject.toml
├── LICENSE
└── README.md
~~~

---

## Troubleshooting

### "No API key found"

You haven't set your API key. The fastest free option:

~~~bash
# 1. Get a free key at https://console.groq.com
# 2. Set it:
export GROQ_API_KEY="gsk_your_key_here"
codereview --init groq
~~~

### "API error 403: error code 1010"

Your HTTP client is being blocked by Cloudflare. Make sure you're up to date:

~~~bash
git pull
pip install -e .
~~~

### "Model has been decommissioned"

The model was deprecated. Re-initialize to get the latest model:

~~~bash
codereview --init groq
~~~

### "Connection refused" (Ollama)

Ollama server isn't running:

~~~bash
ollama serve
~~~

Then try again in a new terminal.

### "No module named rich" or "No module named requests"

Dependencies didn't install. Run:

~~~bash
pip install rich requests
~~~

Or reinstall:

~~~bash
pip install -e .
~~~

### Command not found: codereview

The install didn't add it to your PATH. Use directly:

~~~bash
python3 -m codereview.cli yourfile.py
~~~

Or create an alias:

~~~bash
echo 'alias codereview="python3 -m codereview.cli"' >> ~/.zshrc
source ~/.zshrc
~~~

---

## Contributing

PRs welcome! This project is actively maintained.

### Setup dev environment

~~~bash
git clone https://github.com/jaydendancer12/ai-code-review.git
cd ai-code-review
pip install -e .
pip install pytest
~~~

### Run tests

~~~bash
pytest -v
~~~

### Code style

- Use type hints on all functions
- Write docstrings for all public functions
- Follow PEP 8
- Add tests for new features

### PR guidelines

1. Fork the repo
2. Create a feature branch: git checkout -b feat/my-feature
3. Make changes and add tests
4. Run pytest to verify
5. Submit a PR with a clear description

---

## Roadmap

- [ ] Directory scanning — codereview src/ reviews all files recursively
- [ ] Config profiles — switch between providers with codereview --profile work
- [ ] Output formats — JSON, Markdown, SARIF for CI integration
- [ ] Git hooks — auto-review on git commit
- [ ] VS Code extension — review from your editor
- [ ] Review history — track improvements over time
- [ ] Custom rules — define your own review criteria
- [ ] Multi-language support — language-specific review prompts

---

## License

MIT — see [LICENSE](LICENSE)

---

<div align="center">

**If codereview saved you from a bug, give it a ⭐**

Built by [Jayden Dancer](https://github.com/jaydendancer12)

</div>
