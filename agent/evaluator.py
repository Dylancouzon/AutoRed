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

    scores = {
        "vuln_found": 1.0 if vuln_found else 0.0,
        "false_positive_risk": _score_false_positive(stdout, vuln_found),
        "tool_appropriateness": _score_tool_choice(attack_plan, tool_used),
        "output_quality": min(len(stdout) / 500, 1.0)
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
        return 1.0
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
