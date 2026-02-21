# PenAgent — Claude Code Build Instructions
### Self-Improving Penetration Testing Agent × DVWA × Google ADK

> **Target audience:** Claude Code  
> **Platform:** Mac (Apple Silicon)/windows
> **Pre-installed:** Docker Desktop, Python 3.11+, gcloud CLI  
> ⚠️ Gemini 2.5 Pro is used as the reasoning core. Update `MODEL_ID` in `config.py` to `gemini-3` the moment it becomes available.

> **Documentation:** Continuously create and update a `README.md` as we go. Keep it in sync with the project: add or revise sections when new components, phases, or run instructions are introduced so the repo stays self-describing.

---

## Project Structure to Create

```
penagent/
├── README.md                  # Project overview and run instructions (keep updated as we go)
├── config.py                  # All env vars and constants
├── main.py                    # Entry point — runs the agent loop
├── agent/
│   ├── __init__.py
│   ├── orchestrator.py        # Google ADK agent definition
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
└── .env                       # API keys (never commit this)
```

---

## Phase 0 — Environment Setup

### 0.1 Install system tools (Apple Silicon)

```bash
# Install Homebrew if not present
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install security tools
brew install nmap
brew install go
go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest
go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest

# Install sqlmap
pip3 install sqlmap

# Add Go binaries to PATH (add to ~/.zshrc too)
export PATH=$PATH:$(go env GOPATH)/bin

# Verify
nmap --version
subfinder --version
nuclei --version
sqlmap --version
```

### 0.2 Create Python virtual environment

```bash
mkdir penagent && cd penagent
python3 -m venv .venv
source .venv/bin/activate
```

### 0.3 Create requirements.txt

```
google-adk>=0.1.0
google-cloud-aiplatform>=1.60.0
google-generativeai>=0.7.0
braintrust>=0.0.100
datadog-api-client>=2.25.0
ddtrace>=2.8.0
elevenlabs>=1.1.2
python-dotenv>=1.0.0
requests>=2.31.0
python-nmap>=0.7.1
pyyaml>=6.0.1
rich>=13.7.1
asyncio
aiohttp>=3.9.0
```

```bash
pip install -r requirements.txt
```

---

## Phase 1 — Google Cloud Setup

### 1.1 Create GCP project

```bash
# Login
gcloud auth login

# Create project (replace YOUR_PROJECT_ID with something unique)
gcloud projects create penagent-hack-2025 --name="PenAgent Hackathon"

# Set as active project
gcloud config set project penagent-hack-2025

# Enable billing (required for Vertex AI)
# Go to: https://console.cloud.google.com/billing
# Link your billing account to penagent-hack-2025

# Enable required APIs
gcloud services enable aiplatform.googleapis.com
gcloud services enable cloudresourcemanager.googleapis.com

# Create application default credentials
gcloud auth application-default login

# Set region
gcloud config set compute/region us-central1
```

### 1.2 Verify Vertex AI + Gemini access

```bash
# Quick test — should return model info
python3 -c "
import vertexai
vertexai.init(project='penagent-hack-2025', location='us-central1')
from vertexai.generative_models import GenerativeModel
model = GenerativeModel('gemini-2.5-pro')
r = model.generate_content('Say: Gemini online.')
print(r.text)
"
```

---

## Phase 2 — Spin Up DVWA Target

### 2.1 Create docker/dvwa-compose.yml

```yaml
version: "3.8"
services:
  dvwa:
    image: vulnerables/web-dvwa
    ports:
      - "8080:80"
    environment:
      - MYSQL_PASS=password
    restart: unless-stopped
  db:
    image: mysql:5.7
    environment:
      MYSQL_ROOT_PASSWORD: password
      MYSQL_DATABASE: dvwa
    restart: unless-stopped
```

### 2.2 Start DVWA

```bash
cd docker
docker compose -f dvwa-compose.yml up -d

# Wait ~15 seconds then verify
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080/login.php
# Should return: 200
```

### 2.3 Initialize DVWA database

```bash
# Open browser to: http://localhost:8080/setup.php
# Click "Create / Reset Database"
# Default creds: admin / password
# Set security level to LOW (for demo purposes):
# DVWA Security tab → Security Level → Low → Submit
```

---

## Phase 3 — API Keys & Config

### 3.1 Create .env file

```bash
cat > .env << 'EOF'
# Google Cloud
GCP_PROJECT_ID=penagent-hack-2025
GCP_LOCATION=us-central1

# ⚠️ Update to gemini-3 when available
MODEL_ID=gemini-2.5-pro

# Braintrust (get from: https://www.braintrust.dev → Settings → API Keys)
BRAINTRUST_API_KEY=your_braintrust_key_here
BRAINTRUST_PROJECT=penagent-evals

# Datadog (get from: https://app.datadoghq.com → Organization Settings → API Keys)
DD_API_KEY=your_datadog_api_key_here
DD_APP_KEY=your_datadog_app_key_here
DD_SITE=datadoghq.com
DD_SERVICE=penagent
DD_ENV=hackathon

# ElevenLabs (get from: https://elevenlabs.io → Profile → API Key)
ELEVENLABS_API_KEY=your_elevenlabs_key_here
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM  # Rachel voice (default)

# Target
TARGET_URL=http://localhost:8080
TARGET_NAME=DVWA
EOF
```

### 3.2 Create config.py

```python
import os
from dotenv import load_dotenv

load_dotenv()

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1")
MODEL_ID = os.getenv("MODEL_ID", "gemini-2.5-pro")  # swap to gemini-3 when live

BRAINTRUST_API_KEY = os.getenv("BRAINTRUST_API_KEY")
BRAINTRUST_PROJECT = os.getenv("BRAINTRUST_PROJECT", "penagent-evals")

DD_API_KEY = os.getenv("DD_API_KEY")
DD_APP_KEY = os.getenv("DD_APP_KEY")
DD_SITE = os.getenv("DD_SITE", "datadoghq.com")
DD_SERVICE = os.getenv("DD_SERVICE", "penagent")
DD_ENV = os.getenv("DD_ENV", "hackathon")

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

TARGET_URL = os.getenv("TARGET_URL", "http://localhost:8080")
TARGET_NAME = os.getenv("TARGET_NAME", "DVWA")

MAX_LOOP_ITERATIONS = 3  # How many self-improvement cycles to run
```

---

## Phase 4 — Build the Agent Modules

### 4.1 Create observability/datadog_tracer.py

```python
"""
Datadog APM wrapper. Every module calls trace_step() to create a span.
View live at: https://app.datadoghq.com/apm/traces
"""
import os
from ddtrace import tracer, patch_all
from ddtrace.filters import FilterRequestsOnUrl
from config import DD_SERVICE, DD_ENV

patch_all()

os.environ["DD_SERVICE"] = DD_SERVICE
os.environ["DD_ENV"] = DD_ENV

def trace_step(step_name: str, resource: str = None):
    """Decorator factory. Use @trace_step('recon') on any async function."""
    def decorator(fn):
        async def wrapper(*args, **kwargs):
            with tracer.trace(step_name, service=DD_SERVICE, resource=resource or fn.__name__) as span:
                span.set_tag("penagent.target", os.getenv("TARGET_URL"))
                span.set_tag("penagent.env", DD_ENV)
                try:
                    result = await fn(*args, **kwargs)
                    span.set_tag("penagent.status", "success")
                    return result
                except Exception as e:
                    span.set_tag("penagent.status", "error")
                    span.set_tag("error.msg", str(e))
                    raise
        return wrapper
    return decorator
```

### 4.2 Create agent/recon.py

```python
"""
Recon Module — runs nmap, whatweb, subfinder against the target.
Returns structured findings dict for Gemini to reason about.
"""
import subprocess
import json
import nmap
from observability.datadog_tracer import trace_step
from config import TARGET_URL

@trace_step("recon", "network-scan")
async def run_recon(target_url: str = TARGET_URL) -> dict:
    host = target_url.replace("http://", "").replace("https://", "").split(":")[0]
    port = target_url.split(":")[-1].split("/")[0] if ":" in target_url else "80"

    findings = {"host": host, "port": port, "services": [], "tech_stack": [], "subdomains": []}

    # nmap scan
    nm = nmap.PortScanner()
    nm.scan(hosts=host, ports=port, arguments="-sV -sC --script=http-headers")
    for proto in nm[host].all_protocols():
        for p in nm[host][proto]:
            s = nm[host][proto][p]
            findings["services"].append({
                "port": p, "state": s["state"],
                "name": s["name"], "version": s.get("version", ""),
                "script_output": s.get("script", {})
            })

    # whatweb fingerprint
    try:
        r = subprocess.run(
            ["whatweb", "--log-json=-", target_url],
            capture_output=True, text=True, timeout=30
        )
        findings["tech_stack"] = json.loads(r.stdout) if r.stdout else []
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        # whatweb optional — install via: brew install whatweb
        findings["tech_stack"] = [{"note": "whatweb not available"}]

    # subfinder (localhost won't have subdomains, but included for real targets)
    try:
        r = subprocess.run(
            ["subfinder", "-d", host, "-silent"],
            capture_output=True, text=True, timeout=30
        )
        findings["subdomains"] = r.stdout.strip().split("\n") if r.stdout.strip() else []
    except (subprocess.TimeoutExpired, FileNotFoundError):
        findings["subdomains"] = []

    return findings
```

### 4.3 Create agent/reasoning.py

```python
"""
Gemini Reasoning Core — two functions:
  1. decide_strategy(): takes recon data, returns attack plan
  2. improve_strategy(): takes eval scores, rewrites the strategy prompt
"""
import vertexai
from vertexai.generative_models import GenerativeModel
from config import GCP_PROJECT_ID, GCP_LOCATION, MODEL_ID
from observability.datadog_tracer import trace_step
import os

vertexai.init(project=GCP_PROJECT_ID, location=GCP_LOCATION)
model = GenerativeModel(MODEL_ID)

def _load_prompt(filename: str) -> str:
    path = os.path.join(os.path.dirname(__file__), "..", "prompts", filename)
    with open(path) as f:
        return f.read()

def _save_prompt(filename: str, content: str):
    path = os.path.join(os.path.dirname(__file__), "..", "prompts", filename)
    with open(path, "w") as f:
        f.write(content)

@trace_step("reasoning", "decide-strategy")
async def decide_strategy(recon_findings: dict, iteration: int = 0) -> dict:
    """Given recon data, return a structured attack plan."""
    base_prompt = _load_prompt("strategy.txt")
    
    user_prompt = f"""
{base_prompt}

## Recon Findings (Iteration {iteration}):
{recon_findings}

Return a JSON object with this exact schema:
{{
  "attack_vector": "sql_injection|xss|lfi|auth_bypass|command_injection",
  "target_endpoint": "/path/to/endpoint",
  "tool": "sqlmap|nuclei|custom",
  "payload_hint": "brief description of what to try",
  "rationale": "why this vector based on recon",
  "severity_prediction": "critical|high|medium|low"
}}
"""
    response = model.generate_content(user_prompt)
    import json, re
    text = response.text
    match = re.search(r'\{.*\}', text, re.DOTALL)
    return json.loads(match.group()) if match else {"error": text}

@trace_step("reasoning", "self-improve")
async def improve_strategy(eval_scores: list[dict], current_iteration: int) -> str:
    """Gemini rewrites the strategy prompt based on Braintrust eval scores."""
    improvement_prompt = _load_prompt("improvement.txt")
    current_strategy = _load_prompt("strategy.txt")
    
    user_prompt = f"""
{improvement_prompt}

## Current Strategy Prompt:
{current_strategy}

## Eval Scores from Previous Runs:
{eval_scores}

Rewrite the strategy prompt to improve future attack success rates.
Keep it under 500 words. Output only the new prompt text, no preamble.
"""
    response = model.generate_content(user_prompt)
    new_prompt = response.text.strip()
    _save_prompt("strategy.txt", new_prompt)
    return new_prompt
```

### 4.4 Create agent/exploit.py

```python
"""
Exploit Executor — runs the tool specified in the attack plan.
All execution is sandboxed to localhost:8080 (DVWA only).
"""
import subprocess
import asyncio
from observability.datadog_tracer import trace_step
from config import TARGET_URL

ALLOWED_HOST = "localhost"  # Safety guard — never run against external targets

@trace_step("exploit", "run-exploit")
async def run_exploit(attack_plan: dict) -> dict:
    target_url = TARGET_URL
    host = target_url.replace("http://", "").split(":")[0]
    
    # Safety check
    if host != ALLOWED_HOST and not host.startswith("192.168") and not host.startswith("10."):
        raise ValueError(f"Safety guard triggered: {host} is not a local target. Aborting.")

    tool = attack_plan.get("tool", "nuclei")
    endpoint = attack_plan.get("target_endpoint", "/")
    full_url = f"{target_url}{endpoint}"

    if tool == "sqlmap":
        return await _run_sqlmap(full_url, attack_plan)
    elif tool == "nuclei":
        return await _run_nuclei(target_url, attack_plan)
    else:
        return await _run_custom(full_url, attack_plan)

async def _run_sqlmap(url: str, plan: dict) -> dict:
    cmd = [
        "sqlmap", "-u", url,
        "--batch",           # non-interactive
        "--level=2",
        "--risk=1",
        "--forms",
        "--crawl=2",
        "--output-dir=/tmp/sqlmap_out",
        "--cookie=security=low; PHPSESSID=placeholder"
    ]
    result = await _exec(cmd, timeout=120)
    vuln_found = "injection" in result["stdout"].lower() or "parameter" in result["stdout"].lower()
    return {**result, "vuln_found": vuln_found, "tool": "sqlmap", "url": url}

async def _run_nuclei(target: str, plan: dict) -> dict:
    cmd = [
        "nuclei", "-u", target,
        "-t", "cves/", "-t", "vulnerabilities/",
        "-severity", "medium,high,critical",
        "-json",
        "-silent"
    ]
    result = await _exec(cmd, timeout=120)
    vuln_found = len(result["stdout"].strip()) > 0
    return {**result, "vuln_found": vuln_found, "tool": "nuclei", "url": target}

async def _run_custom(url: str, plan: dict) -> dict:
    """Simple auth bypass attempt — tries default creds."""
    import aiohttp
    payloads = [
        {"username": "admin", "password": "password"},
        {"username": "admin", "password": "admin"},
        {"username": "' OR '1'='1", "password": "anything"},
    ]
    results = []
    async with aiohttp.ClientSession() as session:
        for creds in payloads:
            async with session.post(f"{url}/login.php", data=creds) as r:
                text = await r.text()
                success = "logout" in text.lower() or "welcome" in text.lower()
                results.append({"creds": creds, "success": success, "status": r.status})
    
    vuln_found = any(r["success"] for r in results)
    return {"stdout": str(results), "stderr": "", "vuln_found": vuln_found, "tool": "custom", "url": url}

async def _exec(cmd: list, timeout: int = 60) -> dict:
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return {"stdout": stdout.decode(), "stderr": stderr.decode(), "returncode": proc.returncode}
    except asyncio.TimeoutError:
        proc.kill()
        return {"stdout": "", "stderr": "TIMEOUT", "returncode": -1}
```

### 4.5 Create agent/evaluator.py

```python
"""
Braintrust Eval — scores each agent run.
Scores: vuln_found, false_positive_risk, severity_accuracy, tool_appropriateness
View results at: https://www.braintrust.dev
"""
import braintrust
from config import BRAINTRUST_API_KEY, BRAINTRUST_PROJECT
from observability.datadog_tracer import trace_step

braintrust.login(api_key=BRAINTRUST_API_KEY)

@trace_step("eval", "braintrust-score")
async def score_attempt(
    attack_plan: dict,
    exploit_result: dict,
    iteration: int
) -> dict:
    experiment = braintrust.init(
        project=BRAINTRUST_PROJECT,
        experiment=f"penagent-loop-{iteration}"
    )

    vuln_found = exploit_result.get("vuln_found", False)
    tool_used = exploit_result.get("tool", "unknown")
    stdout = exploit_result.get("stdout", "")

    # Heuristic scoring (0.0 - 1.0)
    scores = {
        "vuln_found": 1.0 if vuln_found else 0.0,
        "false_positive_risk": _score_false_positive(stdout, vuln_found),
        "tool_appropriateness": _score_tool_choice(attack_plan, tool_used),
        "output_quality": min(len(stdout) / 500, 1.0)  # penalises empty output
    }

    overall = sum(scores.values()) / len(scores)
    scores["overall"] = round(overall, 3)

    experiment.log(
        input=attack_plan,
        output=exploit_result,
        scores=scores,
        metadata={"iteration": iteration, "target": exploit_result.get("url")}
    )
    experiment.flush()

    return scores

def _score_false_positive(stdout: str, vuln_reported: bool) -> float:
    """Lower score if tool claims vuln but output is thin."""
    if not vuln_reported:
        return 1.0  # No claim = no false positive risk
    confidence_keywords = ["injection", "vulnerability", "found", "vulnerable", "confirmed"]
    hits = sum(1 for kw in confidence_keywords if kw in stdout.lower())
    return min(hits / 3, 1.0)

def _score_tool_choice(plan: dict, tool_used: str) -> float:
    vector = plan.get("attack_vector", "")
    ideal = {
        "sql_injection": "sqlmap",
        "xss": "nuclei",
        "lfi": "nuclei",
        "auth_bypass": "custom",
        "command_injection": "nuclei"
    }
    return 1.0 if ideal.get(vector) == tool_used else 0.5
```

### 4.6 Create agent/reporter.py

```python
"""
ElevenLabs Voice Reporter — speaks critical findings aloud.
Triggers when overall Braintrust score > 0.6 (real vulnerability found).
"""
import io
from elevenlabs.client import ElevenLabs
from elevenlabs import play
from config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID
from observability.datadog_tracer import trace_step

client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

@trace_step("reporter", "voice-report")
async def voice_report(attack_plan: dict, scores: dict, iteration: int):
    overall = scores.get("overall", 0)
    if overall < 0.4:
        print("[Reporter] Score too low — no voice report triggered.")
        return

    severity = attack_plan.get("severity_prediction", "unknown").upper()
    vector = attack_plan.get("attack_vector", "unknown").replace("_", " ")
    endpoint = attack_plan.get("target_endpoint", "/")

    script = f"""
    PenAgent alert. Iteration {iteration} complete.
    {'Critical finding detected.' if overall > 0.7 else 'Potential vulnerability found.'}
    Attack vector: {vector}.
    Target endpoint: {endpoint}.
    Severity: {severity}.
    Braintrust overall score: {overall:.0%}.
    Recommend immediate review.
    """

    audio = client.text_to_speech.convert(
        voice_id=ELEVENLABS_VOICE_ID,
        text=script.strip(),
        model_id="eleven_turbo_v2"
    )
    play(audio)
    print(f"[Reporter] Voice report delivered. Score: {overall:.0%}")
```

### 4.7 Create agent/orchestrator.py

```python
"""
Google ADK Agent Orchestrator — wires all modules into the agent loop.
Uses Google ADK's Agent class with custom tools for each pipeline stage.
"""
from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from agent.recon import run_recon
from agent.reasoning import decide_strategy, improve_strategy
from agent.exploit import run_exploit
from agent.evaluator import score_attempt
from agent.reporter import voice_report
from config import TARGET_URL, MAX_LOOP_ITERATIONS
from rich.console import Console

console = Console()

# Wrap modules as ADK FunctionTools
recon_tool = FunctionTool(run_recon)
exploit_tool = FunctionTool(run_exploit)

penagent = Agent(
    name="PenAgent",
    model="gemini-2.5-pro",  # ADK model binding
    description="Autonomous penetration testing agent with self-improvement loop.",
    tools=[recon_tool, exploit_tool],
)

async def run_agent_loop():
    console.rule("[bold red]PenAgent Starting[/bold red]")
    eval_history = []

    for i in range(MAX_LOOP_ITERATIONS):
        console.rule(f"[yellow]Iteration {i+1}/{MAX_LOOP_ITERATIONS}[/yellow]")

        # Step 1: Recon
        console.print("[cyan]→ Running recon...[/cyan]")
        recon_data = await run_recon(TARGET_URL)
        console.print(f"  Services found: {len(recon_data.get('services', []))}")

        # Step 2: Gemini decides strategy
        console.print("[cyan]→ Gemini deciding attack strategy...[/cyan]")
        attack_plan = await decide_strategy(recon_data, iteration=i)
        console.print(f"  Attack vector: {attack_plan.get('attack_vector')}")
        console.print(f"  Tool: {attack_plan.get('tool')}")

        # Step 3: Execute exploit
        console.print("[cyan]→ Executing exploit...[/cyan]")
        exploit_result = await run_exploit(attack_plan)
        console.print(f"  Vuln found: {exploit_result.get('vuln_found')}")

        # Step 4: Braintrust eval
        console.print("[cyan]→ Scoring with Braintrust...[/cyan]")
        scores = await score_attempt(attack_plan, exploit_result, iteration=i)
        eval_history.append({"iteration": i, "scores": scores, "plan": attack_plan})
        console.print(f"  Overall score: {scores.get('overall'):.0%}")

        # Step 5: Voice report (if significant finding)
        console.print("[cyan]→ ElevenLabs voice report...[/cyan]")
        await voice_report(attack_plan, scores, iteration=i)

        # Step 6: Self-improve (skip on last iteration)
        if i < MAX_LOOP_ITERATIONS - 1:
            console.print("[cyan]→ Gemini rewriting strategy prompt...[/cyan]")
            new_prompt = await improve_strategy(eval_history, current_iteration=i)
            console.print(f"  New strategy written ({len(new_prompt)} chars)")

    console.rule("[bold green]PenAgent Complete[/bold green]")
    return eval_history
```

---

## Phase 5 — Create Prompt Files

### 5.1 Create prompts/strategy.txt

```
You are an expert penetration tester analyzing a web application.
Your goal is to identify the most promising attack vector based on reconnaissance data.

Focus on OWASP Top 10 vulnerabilities:
- SQL Injection via login forms, search fields, URL parameters
- Cross-site scripting in input fields
- Local file inclusion via path parameters
- Authentication bypass via default credentials or logic flaws
- Command injection via user-supplied input passed to OS commands

Prioritize vectors that are:
1. Supported by concrete evidence in the recon findings
2. Testable with available tools (sqlmap, nuclei, custom scripts)
3. Likely to yield high-severity findings in a DVWA environment

Always respond with valid JSON matching the specified schema.
```

### 5.2 Create prompts/improvement.txt

```
You are a meta-learning system for a penetration testing agent.
Your job is to improve the agent's attack strategy prompt based on empirical results.

Analyze the eval scores from previous runs:
- High vuln_found scores mean the attack vector selection was correct — reinforce this
- Low false_positive_risk scores mean output was credible — keep this behavior  
- Low tool_appropriateness scores mean tool selection logic needs updating
- Low output_quality scores mean the tool ran but found nothing — try different vectors

When rewriting the strategy prompt:
- Be specific about which endpoints worked
- Update prioritization based on what actually yielded results
- Remove or deprioritize vectors that scored poorly
- Keep instructions concise and actionable
- Do NOT include this meta-prompt in your output — output only the new strategy prompt
```

---

## Phase 6 — Entry Point

### 6.1 Create main.py

```python
#!/usr/bin/env python3
"""
PenAgent — main entry point.
Run: python main.py
"""
import asyncio
from agent.orchestrator import run_agent_loop
from rich.console import Console
from rich.panel import Panel

console = Console()

async def main():
    console.print(Panel.fit(
        "[bold red]PenAgent[/bold red] — Self-Improving Penetration Testing Agent\n"
        "[dim]Target: DVWA (Damn Vulnerable Web App)[/dim]\n"
        "[dim]Stack: Gemini 2.5 Pro · Google ADK · Braintrust · Datadog · ElevenLabs[/dim]",
        border_style="red"
    ))

    results = await run_agent_loop()

    console.print("\n[bold]Final Eval Summary:[/bold]")
    for r in results:
        console.print(f"  Iteration {r['iteration']+1}: score={r['scores']['overall']:.0%} "
                      f"vector={r['plan'].get('attack_vector', '?')}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Phase 7 — Datadog Dashboard Setup

```bash
# Ensure Datadog agent is running locally for traces
DD_API_KEY=your_key_here bash -c "$(curl -L https://s3.amazonaws.com/dd-agent/scripts/install_mac_os.sh)"

# Or use Docker (simpler for hackathon)
docker run -d \
  -e DD_API_KEY=$DD_API_KEY \
  -e DD_SITE=datadoghq.com \
  -e DD_APM_ENABLED=true \
  -e DD_APM_NON_LOCAL_TRAFFIC=true \
  -p 8126:8126 \
  --name dd-agent \
  gcr.io/datadoghq/agent:latest

# Run agent with Datadog tracing auto-injected
DD_API_KEY=$DD_API_KEY DD_SITE=datadoghq.com ddtrace-run python main.py
```

**Live dashboard URL:** `https://app.datadoghq.com/apm/services/penagent`  
Create a dashboard in Datadog → New Dashboard → Add widgets for:
- APM Trace Latency by step (recon / reasoning / exploit / eval / reporter)
- Custom metric: `penagent.vuln_found` (count)
- Custom metric: `penagent.score.overall` (avg)

---

## Phase 8 — Run the Full Stack

```bash
# Terminal 1: DVWA
docker compose -f docker/dvwa-compose.yml up

# Terminal 2: Datadog agent
docker run -d -e DD_API_KEY=$DD_API_KEY -e DD_APM_ENABLED=true -p 8126:8126 gcr.io/datadoghq/agent:latest

# Terminal 3: PenAgent
source .venv/bin/activate
export $(cat .env | xargs)
ddtrace-run python main.py
```

---

## Troubleshooting

**nmap requires sudo on Mac:**  
`sudo python main.py` or grant nmap privileges: `sudo chmod u+s $(which nmap)`

**Gemini quota errors:**  
Add `time.sleep(5)` between iterations in orchestrator.py

**sqlmap PHPSESSID invalid:**  
Log into DVWA at `http://localhost:8080`, copy the real PHPSESSID cookie from browser DevTools → Network, paste into `_run_sqlmap()` in exploit.py

**ElevenLabs audio not playing on Mac:**  
`pip install playsound` and add `from playsound import playsound` as fallback in reporter.py

**Braintrust experiment not appearing:**  
Ensure `experiment.flush()` is called after `experiment.log()` — already included in evaluator.py

**Google ADK import errors:**  
`pip install google-adk --upgrade` — the SDK is early-stage and releases frequently

---

## Demo Script (Hackathon Judges)

1. Show DVWA running at `http://localhost:8080`
2. Start PenAgent: `ddtrace-run python main.py`
3. Show terminal output — Iteration 1 recon + Gemini deciding SQL injection
4. Show sqlmap finding the vuln → ElevenLabs speaks the finding aloud
5. Show Braintrust dashboard: `braintrust.dev` → penagent-evals experiment
6. Show Iteration 2 — Gemini has rewritten the strategy prompt (self-improvement)
7. Show Datadog APM trace waterfall — every step timed and logged
8. Close: "This is a fully autonomous security agent that gets smarter every run"
