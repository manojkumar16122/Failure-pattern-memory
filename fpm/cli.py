import typer
from rich.console import Console
from rich.table import Table

from fpm.engine import FailurePatternMemory

app = typer.Typer(help="Failure Pattern Memory - learn from agent failures")
console = Console()


@app.command()
def record(
    log: str = typer.Argument(..., help="Raw failure log text"),
    task: str = typer.Option("unknown", "--task", "-t", help="Task type"),
    agent: str = typer.Option("default", "--agent", "-a", help="Agent ID"),
):
    """Record a failure from a raw log."""
    fpm = FailurePatternMemory()
    failure_id = fpm.record_failure(log, task_type=task, agent_id=agent)
    console.print(f"[green]OK[/green] Recorded failure: [bold]{failure_id}[/bold]")


@app.command()
def check(
    task: str = typer.Argument(..., help="Task description to check"),
    top_k: int = typer.Option(5, "--top", "-k", help="Number of warnings"),
):
    """Check for warnings before executing a task."""
    fpm = FailurePatternMemory()
    warnings = fpm.check_before_task(task, top_k=top_k)

    if not warnings:
        console.print("[dim]No warnings found for this task.[/dim]")
        return

    table = Table(title=f"Warnings for: {task}")
    table.add_column("Similarity", style="cyan")
    table.add_column("Pattern", style="yellow")
    table.add_column("Prevention", style="green")
    table.add_column("Severity", style="red")

    for w in warnings:
        prevention = w.prevention[:60] + "..." if len(w.prevention) > 60 else w.prevention
        table.add_row(f"{w.similarity:.2f}", w.context_pattern, prevention, w.severity)

    console.print(table)


@app.command()
def history():
    """Show all recorded failures."""
    fpm = FailurePatternMemory()
    failures = fpm.get_failure_history()

    if not failures:
        console.print("[dim]No failures recorded yet.[/dim]")
        return

    table = Table(title=f"Failure History ({len(failures)} records)")
    table.add_column("ID", style="dim")
    table.add_column("Category", style="cyan")
    table.add_column("Pattern", style="yellow")
    table.add_column("Severity", style="red")

    for f in failures:
        table.add_row(f["id"], f["error_category"], f["context_pattern"], f["severity"])

    console.print(table)


if __name__ == "__main__":
    app()
