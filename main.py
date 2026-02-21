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
