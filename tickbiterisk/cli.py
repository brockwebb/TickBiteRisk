from __future__ import annotations

from pathlib import Path

import typer

app = typer.Typer(help="TickBiteRisk ETL utilities")
etl_app = typer.Typer(help="ETL commands")
app.add_typer(etl_app, name="etl")


@etl_app.command("check")
def etl_check(
    output_dir: Path = typer.Option(
        Path("build/etl"), help="Output directory for ETL artifacts."
    )
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    typer.echo(f"ETL output directory ready: {output_dir}")


if __name__ == "__main__":
    app()
