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

recon_tool = FunctionTool(run_recon)
exploit_tool = FunctionTool(run_exploit)

penagent = Agent(
    name="PenAgent",
    model="gemini-2.5-pro",
    description="Autonomous penetration testing agent with self-improvement loop.",
    tools=[recon_tool, exploit_tool],
)


async def run_agent_loop():
    console.rule("[bold red]PenAgent Starting[/bold red]")
    eval_history = []

    for i in range(MAX_LOOP_ITERATIONS):
        console.rule(f"[yellow]Iteration {i+1}/{MAX_LOOP_ITERATIONS}[/yellow]")

        console.print("[cyan]→ Running recon...[/cyan]")
        recon_data = await run_recon(TARGET_URL)
        console.print(f"  Services found: {len(recon_data.get('services', []))}")

        console.print("[cyan]→ Gemini deciding attack strategy...[/cyan]")
        attack_plan = await decide_strategy(recon_data, iteration=i)
        console.print(f"  Attack vector: {attack_plan.get('attack_vector')}")
        console.print(f"  Tool: {attack_plan.get('tool')}")

        console.print("[cyan]→ Executing exploit...[/cyan]")
        exploit_result = await run_exploit(attack_plan)
        console.print(f"  Vuln found: {exploit_result.get('vuln_found')}")

        console.print("[cyan]→ Scoring with Braintrust...[/cyan]")
        scores = await score_attempt(attack_plan, exploit_result, iteration=i)
        eval_history.append({"iteration": i, "scores": scores, "plan": attack_plan})
        console.print(f"  Overall score: {scores.get('overall'):.0%}")

        console.print("[cyan]→ ElevenLabs voice report...[/cyan]")
        await voice_report(attack_plan, scores, iteration=i)

        if i < MAX_LOOP_ITERATIONS - 1:
            console.print("[cyan]→ Gemini rewriting strategy prompt...[/cyan]")
            new_prompt = await improve_strategy(eval_history, current_iteration=i)
            console.print(f"  New strategy written ({len(new_prompt)} chars)")

    console.rule("[bold green]PenAgent Complete[/bold green]")
    return eval_history
