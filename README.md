# PenAgent

**Self-Improving Penetration Testing Agent** — powered by Gemini 2.5 Pro, Google ADK, Braintrust, Datadog, and ElevenLabs.

PenAgent is an autonomous security agent that runs reconnaissance, selects attack vectors via LLM reasoning, executes exploits, evaluates results, and rewrites its own strategy prompt to improve across iterations.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Recon      │────▶│  Gemini      │────▶│  Exploit     │
│  (nmap,      │     │  Reasoning   │     │  (sqlmap,    │
│   whatweb,   │     │  Core        │     │   nuclei,    │
│   subfinder) │     │              │     │   custom)    │
└─────────────┘     └──────────────┘     └──────┬───────┘
                           ▲                     │
                           │                     ▼
                    ┌──────┴───────┐     ┌──────────────┐
                    │  Self-       │◀────│  Braintrust  │
                    │  Improvement │     │  Eval        │
                    └──────────────┘     └──────┬───────┘
                                                │
                                                ▼
                                        ┌──────────────┐
                                        │  ElevenLabs  │
                                        │  Voice       │
                                        │  Reporter    │
                                        └──────────────┘
```

All steps are traced via **Datadog APM** for full observability.

## Project Structure

```
├── config.py                  # Env vars and constants
├── main.py                    # Entry point — runs the agent loop
├── agent/
│   ├── orchestrator.py        # Google ADK agent definition + loop
│   ├── recon.py               # Recon module (nmap, whatweb, subfinder)
│   ├── exploit.py             # Exploit executor (sqlmap, nuclei, custom)
│   ├── reasoning.py           # Gemini reasoning core (strategy + improvement)
│   ├── evaluator.py           # Braintrust eval scoring
│   └── reporter.py            # ElevenLabs voice reporting
├── observability/
│   └── datadog_tracer.py      # Datadog APM tracing wrapper
├── prompts/
│   ├── strategy.txt           # Base attack strategy prompt (Gemini rewrites this)
│   └── improvement.txt        # Self-improvement meta-prompt
├── docker/
│   └── dvwa-compose.yml       # DVWA target environment
├── requirements.txt
└── .env                       # API keys (never commit)
```

## Prerequisites

- **Python 3.11+**
- **Docker Desktop** (for DVWA target)
- **gcloud CLI** (authenticated with Vertex AI enabled)
- **System tools:** nmap, sqlmap, subfinder, nuclei

### Install System Tools (macOS)

```bash
# Homebrew packages
brew install nmap go

# Go-based tools (add Go bin to PATH)
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
# Nuclei: v3 may fail to build on Go 1.26; use v2 if so
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
# or: go install -v github.com/projectdiscovery/nuclei/v2/cmd/nuclei@latest

# sqlmap (use pipx when system Python is externally managed)
pipx install sqlmap
# or: pip3 install sqlmap  (inside a venv)

# Add to ~/.zshrc so tools are on PATH:
export PATH=$PATH:$(go env GOPATH)/bin
export PATH=$PATH:$HOME/.local/bin   # pipx
```

**Verify:** `nmap --version` · `subfinder -h` · `nuclei -version` · `sqlmap --version`

## Setup

### 1. Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Google Cloud

```bash
gcloud auth login
gcloud config set project penagent-hack-2025
gcloud services enable aiplatform.googleapis.com
gcloud auth application-default login
```

### 3. Configure API Keys

Copy `.env` and fill in your keys:

| Variable | Source |
|---|---|
| `BRAINTRUST_API_KEY` | [braintrust.dev](https://www.braintrust.dev) → Settings → API Keys |
| `DD_API_KEY` | [Datadog](https://app.datadoghq.com) → Organization Settings → API Keys |
| `ELEVENLABS_API_KEY` | [ElevenLabs](https://elevenlabs.io) → Profile → API Key |

### 4. Start DVWA Target

```bash
docker compose -f docker/dvwa-compose.yml up -d
```

Then visit `http://localhost:8080/setup.php`, click **Create / Reset Database**, and log in with `admin` / `password`. Set security level to **Low**.

### 5. Start Datadog Agent (optional)

```bash
docker run -d \
  -e DD_API_KEY=$DD_API_KEY \
  -e DD_SITE=datadoghq.com \
  -e DD_APM_ENABLED=true \
  -e DD_APM_NON_LOCAL_TRAFFIC=true \
  -p 8126:8126 \
  --name dd-agent \
  gcr.io/datadoghq/agent:latest
```

## Running

```bash
source .venv/bin/activate
export $(cat .env | xargs)

# With Datadog tracing
ddtrace-run python main.py

# Without Datadog
python main.py
```

## How It Works

1. **Recon** — nmap service scan, whatweb fingerprinting, subfinder subdomain enumeration
2. **Reasoning** — Gemini 2.5 Pro analyzes recon data and selects an attack vector + tool
3. **Exploit** — Runs sqlmap (SQL injection), nuclei (CVE/vuln templates), or custom scripts
4. **Eval** — Braintrust scores the attempt on vuln_found, false_positive_risk, tool_appropriateness, output_quality
5. **Report** — ElevenLabs speaks critical findings aloud when score > 0.4
6. **Self-Improve** — Gemini rewrites its own strategy prompt based on eval scores, then loops

The agent runs `MAX_LOOP_ITERATIONS` (default: 3) cycles, getting smarter each round.

## Dashboards

- **Braintrust:** [braintrust.dev](https://www.braintrust.dev) → `penagent-evals` project
- **Datadog APM:** [app.datadoghq.com/apm/services/penagent](https://app.datadoghq.com/apm/services/penagent)

## Troubleshooting

| Issue | Fix |
|---|---|
| nmap requires sudo | `sudo python main.py` or `sudo chmod u+s $(which nmap)` |
| Gemini quota errors | Add `time.sleep(5)` between iterations in `orchestrator.py` |
| sqlmap PHPSESSID invalid | Copy real PHPSESSID from browser DevTools into `exploit.py` |
| ElevenLabs audio not playing | `pip install playsound` as fallback |
| Braintrust experiment missing | Ensure `experiment.flush()` is called (already included) |
| Google ADK import errors | `pip install google-adk --upgrade` |
