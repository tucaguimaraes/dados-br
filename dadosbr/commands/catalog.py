"""
Comandos de catálogo: list, info, catalog validate, catalog stats.
"""

from __future__ import annotations

from typing import Optional

import typer
from rich.panel import Panel
from rich.table import Table

from ..context import emit_json, err, is_json, out
from ..models import Dataset
from ..services import get_registry
from ..utils import (
    category_icon,
    human_mb,
    human_size,
    source_badge,
)

# Sub-app montado em cli.py como "catalog"
catalog_app = typer.Typer(help="Comandos de catálogo (validate, stats).")


# ---------------------------------------------------------------------------
# Helpers de renderização
# ---------------------------------------------------------------------------

def _dataset_table(datasets: list[Dataset], title: str = "Datasets") -> Table:
    table = Table(
        title=title,
        show_lines=False,
        expand=True,
        title_style="bold cyan",
    )
    table.add_column("#", style="dim", width=4, no_wrap=True)
    table.add_column("ID", style="bold", no_wrap=True)
    table.add_column("Nome", min_width=30)
    table.add_column("Fonte", no_wrap=True)
    table.add_column("Categoria", no_wrap=True)
    table.add_column("Anos / Arquivos", justify="right")
    table.add_column("~Download", justify="right")

    for i, ds in enumerate(datasets, 1):
        icon = category_icon(ds.category)
        if ds.url_type in ("pattern", "ftp") and ds.years:
            anos = f"{ds.years.start}–{ds.years.end} ({ds.year_count()} anos)"
        elif ds.url_type == "static_list":
            anos = f"{len(ds.files)} arquivo(s)"
        else:
            anos = "dinâmico"

        est = ds.estimate_download_mb(ds.available_years() or None)
        tamanho = human_mb(est) if est else "—"

        table.add_row(
            str(i), ds.id, ds.name, ds.source,
            f"{icon} {ds.category}", anos, tamanho,
        )
    return table


# ---------------------------------------------------------------------------
# Comando: list
# ---------------------------------------------------------------------------

def cmd_list(
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filtra por categoria"),
    source: Optional[str] = typer.Option(None, "--source", "-s", help="Filtra por fonte/órgão"),
    search: Optional[str] = typer.Option(None, "--search", "-q", help="Busca por texto livre"),
    show_urls: bool = typer.Option(False, "--urls", help="Exibe URLs de exemplo"),
    show_commands: bool = typer.Option(False, "--commands", help="Exibe o comando de download de cada dataset"),
) -> None:
    """Lista todos os datasets disponíveis no catálogo."""
    reg = get_registry()
    datasets = reg.all()

    if category:
        datasets = [d for d in datasets if d.category.lower() == category.lower()]
    if source:
        datasets = [d for d in datasets if d.source.lower() == source.lower()]
    if search:
        datasets = reg.search(search)

    if not datasets:
        if is_json():
            emit_json([])
        else:
            out.print("[yellow]Nenhum dataset encontrado com os filtros informados.[/]")
        raise typer.Exit(0)

    # ---- JSON ---------------------------------------------------------------
    if is_json():
        def _download_cmd(ds: Dataset) -> str:
            if ds.url_type in ("pattern", "ftp") and ds.years:
                avail = ds.available_years()
                recent = avail[-3:] if len(avail) >= 3 else avail
                yr = f"--years {recent[0]}-{recent[-1]}" if len(recent) > 1 else f"--years {recent[0]}"
                return f"dados-br download {ds.id} {yr}"
            return f"dados-br download {ds.id}"

        rows = []
        for ds in datasets:
            row: dict = {
                "id": ds.id,
                "name": ds.name,
                "source": ds.source,
                "category": ds.category,
                "url_type": ds.url_type,
                "tags": ds.tags or [],
                "license": ds.license,
                "est_size_mb": ds.estimate_download_mb(ds.available_years() or None),
                "download_command": _download_cmd(ds),
            }
            if ds.url_type in ("pattern", "ftp") and ds.years:
                row["years_start"] = ds.years.start
                row["years_end"] = ds.years.end
                row["year_count"] = ds.year_count()
            elif ds.url_type == "static_list":
                row["file_count"] = len(ds.files)
            rows.append(row)
        emit_json(rows)
        return

    # ---- text ---------------------------------------------------------------
    title = f"Catálogo dados-br — {len(datasets)} dataset(s)"
    out.print(_dataset_table(datasets, title=title))

    if show_urls:
        out.print()
        for ds in datasets[:5]:
            if ds.url_pattern:
                out.print(f"  [dim]{ds.id}[/]: {ds.url_pattern}")

    if show_commands:
        out.print()
        out.print("[bold]Comandos de download:[/]")
        cmd_table = Table(show_header=False, box=None, padding=(0, 1))
        cmd_table.add_column("ID", style="bold cyan", no_wrap=True)
        cmd_table.add_column("Comando", style="green")
        for ds in datasets:
            if ds.url_type in ("pattern", "ftp") and ds.years:
                avail = ds.available_years()
                recent = avail[-3:] if len(avail) >= 3 else avail
                years_ex = f"--years {recent[0]}-{recent[-1]}" if len(recent) > 1 else f"--years {recent[0]}"
                cmd = f"dados-br download {ds.id} {years_ex}"
            else:
                cmd = f"dados-br download {ds.id}"
            cmd_table.add_row(ds.id, cmd)
        out.print(cmd_table)

    out.print(f"\n[dim]Use [bold]dados-br info <id>[/] para detalhes ou [bold]dados-br download <id>[/] para baixar.[/]")
    out.print(f"[dim]Dica: [bold]dados-br list --commands[/] mostra o comando de download de cada dataset.[/]")


# ---------------------------------------------------------------------------
# Comando: info
# ---------------------------------------------------------------------------

def cmd_info(
    dataset_id: str = typer.Argument(help="ID do dataset (ex: enem, censo_escolar)"),
) -> None:
    """Exibe informações detalhadas sobre um dataset."""
    from ..registry import RegistryError
    reg = get_registry()
    try:
        ds = reg.require(dataset_id)
    except RegistryError as exc:
        err.print(f"[red]{exc}[/]")
        raise typer.Exit(1) from exc

    icon = category_icon(ds.category)
    out.print(Panel.fit(
        f"[bold]{icon} {ds.name}[/]\n[dim]{ds.source}[/]",
        title=f"[cyan]{ds.id}[/]",
        style="blue",
    ))

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Campo", style="bold dim", no_wrap=True)
    table.add_column("Valor")

    table.add_row("ID", ds.id)
    table.add_row("Nome", ds.name)
    table.add_row("Fonte", ds.source)
    table.add_row("Categoria", f"{icon} {ds.category}")
    table.add_row("Licença", ds.license)
    table.add_row("Formato", ds.file_format.upper())
    table.add_row("Destino", ds.dest_folder)

    if ds.homepage:
        table.add_row("Homepage", ds.homepage)

    if ds.url_type in ("pattern", "ftp") and ds.years:
        table.add_row("Anos", f"{ds.years.start} – {ds.years.end} ({ds.year_count()} anos disponíveis)")
        if ds.url_pattern:
            table.add_row("URL padrão", ds.url_pattern)
        if ds.est_size_mb_per_year:
            table.add_row("~Tamanho/ano", human_mb(ds.est_size_mb_per_year))
        if ds.est_extracted_mb_per_year:
            table.add_row("~Extraído/ano", human_mb(ds.est_extracted_mb_per_year))
        total = ds.estimate_download_mb(ds.available_years())
        if total:
            table.add_row("~Total download", human_mb(total))
    elif ds.url_type == "static_list":
        table.add_row("Arquivos", str(len(ds.files)))
        if ds.est_size_mb_total:
            table.add_row("~Tamanho total", human_mb(ds.est_size_mb_total))
        if ds.est_extracted_mb_total:
            table.add_row("~Extraído total", human_mb(ds.est_extracted_mb_total))

    out.print(table)
    out.print(f"\n[bold]Descrição:[/]\n{ds.description.strip()}")

    if ds.notes:
        out.print(f"\n[bold dim]Notas:[/]\n[dim]{ds.notes.strip()}[/]")
    if ds.tags:
        tags_str = "  ".join(f"[cyan]#{t}[/]" for t in ds.tags)
        out.print(f"\n{tags_str}")
    if ds.year_exceptions:
        out.print(f"\n[bold]Exceções por ano:[/]")
        for y, exc_val in list(ds.year_exceptions.items())[:5]:
            if exc_val is None:
                out.print(f"  [red]✗ {y}: desabilitado[/]")
            else:
                out.print(f"  [yellow]≠ {y}: URL alternativa[/]")
    if ds.checks:
        checks_str = ", ".join(c.type for c in ds.checks)
        out.print(f"\n[dim]Checagens configuradas: {checks_str}[/]")

    out.print(f"\n[dim]Baixar: [bold]dados-br download {ds.id}[/][/]")


# ---------------------------------------------------------------------------
# Subcomandos: catalog validate / stats
# ---------------------------------------------------------------------------

@catalog_app.command("validate")
def catalog_validate() -> None:
    """Valida todos os YAMLs do catálogo e reporta erros."""
    reg = get_registry()
    issues = reg.validate_all()

    if not issues:
        out.print(f"[green]✓ Catálogo válido! {len(reg)} datasets sem erros.[/]")
        return

    out.print(f"[red]✗ {len(issues)} problema(s) encontrado(s):[/]")
    for target, msgs in issues.items():
        for msg in msgs:
            out.print(f"  [red]•[/] [bold]{target}[/]: {msg}")
    raise typer.Exit(1)


@catalog_app.command("stats")
def catalog_stats() -> None:
    """Exibe estatísticas do catálogo."""
    reg = get_registry()
    datasets = reg.all()

    out.print(f"\n[bold cyan]📊 Estatísticas do Catálogo dados-br[/]\n")
    out.print(f"  Total de datasets  : [bold]{len(datasets)}[/]")
    out.print(f"  Categorias únicas  : [bold]{len(reg.categories())}[/]")
    out.print(f"  Fontes únicas      : [bold]{len(reg.sources())}[/]")

    out.print("\n[bold]Por categoria:[/]")
    for cat in reg.categories():
        cat_ds = reg.by_category(cat)
        icon = category_icon(cat)
        out.print(f"  {icon} {cat}: [bold]{len(cat_ds)}[/] dataset(s)")

    out.print("\n[bold]Por fonte:[/]")
    for src in reg.sources():
        src_ds = reg.by_source(src)
        badge = source_badge(src)
        out.print(f"  {badge}: [bold]{len(src_ds)}[/] dataset(s)")

    total_mb = sum(
        est for ds in datasets
        if (est := ds.estimate_download_mb(ds.available_years() or None))
    )
    if total_mb > 0:
        out.print(f"\n  ~Volume total estimado (todos os anos): [bold yellow]{human_mb(total_mb)}[/]")

    errors = reg.load_errors()
    if errors:
        out.print(f"\n[yellow]⚠ {len(errors)} YAML(s) com erro de carregamento[/]")
        for path, exc in errors:
            out.print(f"  [red]•[/] {path.name}: {exc}")
