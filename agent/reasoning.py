"""
Gemini Reasoning Core — two functions:
  1. decide_strategy(): takes recon data, returns attack plan
  2. improve_strategy(): takes eval scores, rewrites the strategy prompt
"""
import json
import re
import os
import vertexai
from vertexai.generative_models import GenerativeModel
from config import GCP_PROJECT_ID, GCP_LOCATION, MODEL_ID
from observability.datadog_tracer import trace_step

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
