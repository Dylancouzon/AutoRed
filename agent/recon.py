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

    try:
        r = subprocess.run(
            ["whatweb", "--log-json=-", target_url],
            capture_output=True, text=True, timeout=30
        )
        findings["tech_stack"] = json.loads(r.stdout) if r.stdout else []
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        findings["tech_stack"] = [{"note": "whatweb not available"}]

    try:
        r = subprocess.run(
            ["subfinder", "-d", host, "-silent"],
            capture_output=True, text=True, timeout=30
        )
        findings["subdomains"] = r.stdout.strip().split("\n") if r.stdout.strip() else []
    except (subprocess.TimeoutExpired, FileNotFoundError):
        findings["subdomains"] = []

    return findings
