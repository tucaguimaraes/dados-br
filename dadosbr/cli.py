"""
dados-br CLI — interface de linha de comando com Typer + Rich.

Comandos:
    dados-br list              Lista datasets do catálogo
    dados-br info <id>         Informações detalhadas sobre um dataset
    dados-br download          Baixa um ou mais datasets (interativo ou via flags)
    dados-br check             Verifica arquivos baixados
    dados-br catalog           Subcomandos de catálogo (validate, stats)
    dados-br indicators        Subcomandos de indicadores educacionais
    dados-br version           Exibe a versão instalada
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

from . import __version__
from .checker import DatasetCheckReport, run_basic_checks, run_dataset_checks
from .downloader import DownloadConfig, DownloadSummary, download_urls, probe_all_sizes
from .indicators import IndicatorLevel, IndicatorRegistry, indicator_registry as _global_indicators
from .models import Dataset
from .registry import Registry, RegistryError, registry as _global_registry
from .utils import (
    category_icon,
    check_disk_space,
    free_space_bytes,
    human_mb,
    human_size,
    parse_years_expr,
    source_badge,
)

# ---------------------------------------------------------------------------
# App raiz
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="dados-br",
    help=(
        "🇧🇷 [bold]dados-br[/] — Ferramenta open source para catalogar, baixar "
        "e validar dados públicos brasileiros."
    ),
    rich_markup_mode="rich",
    no_args_is_help=True,
    add_completion=True,
)

catalog_app = typer.Typer(help="Comandos de catálogo (validate, stats).")
app.add_typer(catalog_app, name="catalog")

indicators_app = typer.Typer(help="Indicadores educacionais com citações e perguntas norteadoras.")
app.add_typer(indicators_app, name="indicators")

out = Console()
err = Console(stderr=True)

# ---------------------------------------------------------------------------
# Helpers de display
# ---------------------------------------------------------------------------

_LOGO = """
 ██████╗ ██████╗  █████╗ ███████╗ █████╗ ██████╗  █████╗ ██████╗  ██████╗ ███████╗
 ██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗██╔══██╗██╔══██╗██╔══██╗██╔═══██╗██╔════╝
 ██████╔╝██████╔╝███████║███████╗███████║██║  ██║███████║██║  ██║██║   ██║███████╗
 ██╔══██╗██╔══██╗██╔══██║╚════██║██╔══██║██║  ██║██╔══██║██║  ██║██║   ██║╚════██║
 ██████╔╝██║  ██║██║  ██║███████║██║  ██║██████╔╝██║  ██║██████╔╝╚██████╔╝███████║
 ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝╚═════╝ ╚═╝  ╚═╝╚═════╝  ╚═════╝ ╚══════╝
"""


def _print_logo() -> None:
    out.print(Panel.fit(_LOGO.strip(), style="bold green", padding=(0, 2)))


def _get_registry() -> Registry:
    try:
        _global_registry.load()
    except Exception as exc:
        err.print(f"[red]Erro ao carregar catálogo: {exc}[/]")
        raise typer.Exit(1) from exc
    return _global_registry


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
            str(i),
            ds.id,
            ds.name,
            ds.source,
            f"{icon} {ds.category}",
            anos,
            tamanho,
        )
    return table


def _select_from_list(
    items: list[str],
    prompt: str,
    allow_all: bool = False,
) -> list[int]:
    """
    Exibe lista numerada e pede seleção interativa.

    Returns:
        Lista de índices 0-based selecionados.
    """
    for i, item in enumerate(items, 1):
        out.print(f"  [dim]{i:3}[/] {item}")

    if allow_all:
        out.print(f"  [dim]  0[/] [bold]TODOS[/]")

    raw = Prompt.ask(
        prompt,
        console=out,
    )

    if allow_all and raw.strip() == "0":
        return list(range(len(items)))

    selected: list[int] = []
    for part in raw.replace(" ", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            idx = int(part) - 1
            if 0 <= idx < len(items):
                selected.append(idx)
            else:
                out.print(f"[yellow]Número inválido: {part}[/]")
        except ValueError:
            out.print(f"[yellow]Entrada inválida: {part!r}[/]")

    return selected


# ---------------------------------------------------------------------------
# Comando: list
# ---------------------------------------------------------------------------

@app.command("list")
def cmd_list(
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filtra por categoria"),
    source: Optional[str] = typer.Option(None, "--source", "-s", help="Filtra por fonte/órgão"),
    search: Optional[str] = typer.Option(None, "--search", "-q", help="Busca por texto livre"),
    show_urls: bool = typer.Option(False, "--urls", help="Exibe URLs de exemplo"),
) -> None:
    """Lista todos os datasets disponíveis no catálogo."""
    reg = _get_registry()
    datasets = reg.all()

    if category:
        datasets = [d for d in datasets if d.category.lower() == category.lower()]
    if source:
        datasets = [d for d in datasets if d.source.lower() == source.lower()]
    if search:
        datasets = reg.search(search)

    if not datasets:
        out.print("[yellow]Nenhum dataset encontrado com os filtros informados.[/]")
        raise typer.Exit(0)

    title = f"Catálogo dados-br — {len(datasets)} dataset(s)"
    out.print(_dataset_table(datasets, title=title))

    if show_urls:
        out.print()
        for ds in datasets[:5]:  # limita exibição para não poluir
            if ds.url_pattern:
                out.print(f"  [dim]{ds.id}[/]: {ds.url_pattern}")

    out.print(f"\n[dim]Use [bold]dados-br info <id>[/] para detalhes ou [bold]dados-br download <id>[/] para baixar.[/]")


# ---------------------------------------------------------------------------
# Comando: info
# ---------------------------------------------------------------------------

@app.command("info")
def cmd_info(
    dataset_id: str = typer.Argument(help="ID do dataset (ex: enem, censo_escolar)"),
) -> None:
    """Exibe informações detalhadas sobre um dataset."""
    reg = _get_registry()
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
# Comando: download
# ---------------------------------------------------------------------------

@app.command("download")
def cmd_download(
    dataset_id: Optional[str] = typer.Argument(
        default=None,
        help="ID do dataset (omita para modo interativo)",
    ),
    all_datasets: bool = typer.Option(
        False, "--all", "-a",
        help="Baixa TODOS os datasets do catálogo",
    ),
    years: Optional[str] = typer.Option(
        None, "--years", "-y",
        help="Anos: all, 2020-2023, 2020,2021 (padrão: interativo)",
    ),
    output_dir: Path = typer.Option(
        Path("dados"), "--output-dir", "-o",
        help="Diretório raiz para salvar os dados",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run",
        help="Simula o download sem baixar nada",
    ),
    skip_existing: bool = typer.Option(
        True, "--skip-existing/--no-skip",
        help="Pula arquivos já existentes com o mesmo tamanho",
    ),
    verify_ssl: bool = typer.Option(
        True, "--verify-ssl/--no-verify-ssl",
        help="Verifica certificados SSL",
    ),
    retries: int = typer.Option(4, "--retries", "-r", help="Tentativas por arquivo"),
    timeout: int = typer.Option(60, "--timeout", "-t", help="Timeout por requisição (segundos)"),
    chunk_mb: int = typer.Option(16, "--chunk-mb", help="Tamanho dos blocos de download (MB)"),
    auto_check: bool = typer.Option(
        True, "--check/--no-check",
        help="Executa checagens automáticas após o download",
    ),
) -> None:
    """
    Baixa um ou mais datasets de dados públicos brasileiros.

    Sem argumentos: modo interativo com seleção guiada.
    """
    _print_logo()
    reg = _get_registry()

    # ------------------------------------------------------------------
    # Resolver quais datasets baixar
    # ------------------------------------------------------------------
    datasets_to_download: list[Dataset] = []

    if all_datasets:
        datasets_to_download = reg.all()
        out.print(f"[yellow]⚠ Modo --all: {len(datasets_to_download)} datasets selecionados[/]")
        if not Confirm.ask(
            f"Confirmar download de TODOS os {len(datasets_to_download)} datasets?",
            console=out,
            default=False,
        ):
            raise typer.Exit(0)

    elif dataset_id:
        try:
            datasets_to_download = [reg.require(dataset_id)]
        except RegistryError as exc:
            err.print(f"[red]{exc}[/]")
            raise typer.Exit(1) from exc

    else:
        # Modo interativo
        out.print("\n[bold cyan]Modo interativo — selecione os dados para baixar[/]\n")

        # Passo 1: Categoria
        categories = reg.categories()
        out.print("[bold]Categorias disponíveis:[/]")
        cat_indices = _select_from_list(
            [f"{category_icon(c)} {c}" for c in categories],
            prompt="Número(s) da(s) categoria(s) [ex: 1 ou 1,2 ou 0 para todas]",
            allow_all=True,
        )
        selected_categories = [categories[i] for i in cat_indices] if cat_indices else categories

        # Passo 2: Datasets da categoria
        candidates = [d for d in reg.all() if d.category in selected_categories]
        out.print(f"\n[bold]Datasets disponíveis ({len(candidates)}):[/]")
        ds_indices = _select_from_list(
            [f"[cyan]{d.id}[/] — {d.name} [dim]({d.source})[/]" for d in candidates],
            prompt="Número(s) do(s) dataset(s) [ex: 1 ou 1,3,5 ou 0 para todos]",
            allow_all=True,
        )
        datasets_to_download = [candidates[i] for i in ds_indices] if ds_indices else candidates

    if not datasets_to_download:
        out.print("[yellow]Nenhum dataset selecionado. Saindo.[/]")
        raise typer.Exit(0)

    # ------------------------------------------------------------------
    # Construir mapa de downloads: {url: dest_path}
    # ------------------------------------------------------------------
    config = DownloadConfig(
        output_dir=output_dir,
        timeout=timeout,
        max_retries=retries,
        chunk_mb=chunk_mb,
        verify_ssl=verify_ssl,
        skip_existing=skip_existing,
        dry_run=dry_run,
    )

    url_dest_map: dict[str, str] = {}  # url → dest absoluto
    dataset_files: dict[str, list[str]] = {}  # dataset_id → [dest paths]

    for ds in datasets_to_download:
        dest_root = output_dir / ds.dest_folder
        ds_files: list[str] = []

        if ds.url_type in ("pattern", "ftp"):
            # Resolver anos
            available = ds.available_years()
            if not available:
                out.print(f"[yellow]⚠ {ds.id}: sem anos disponíveis[/]")
                continue

            if years:
                try:
                    selected_years = parse_years_expr(years, available)
                except ValueError as exc:
                    err.print(f"[red]Anos inválidos para {ds.id}: {exc}[/]")
                    continue
            else:
                # Interativo: perguntar anos (só para datasets pattern)
                if len(datasets_to_download) == 1:
                    out.print(
                        f"\n[bold]Anos disponíveis para [cyan]{ds.id}[/]: "
                        f"{available[0]}–{available[-1]}[/]"
                    )
                    years_input = Prompt.ask(
                        "Quais anos? (ex: all, 2020-2023, 2020,2022)",
                        default="all",
                        console=out,
                    )
                    try:
                        selected_years = parse_years_expr(years_input, available)
                    except ValueError as exc:
                        err.print(f"[red]{exc}[/]")
                        raise typer.Exit(1) from exc
                else:
                    selected_years = available  # batch: baixa tudo

            year_urls = ds.urls_for_years(selected_years)
            for y, url_list in year_urls.items():
                for url in url_list:
                    from .utils import filename_from_url  # noqa
                    fname = filename_from_url(url)
                    dest = str(dest_root / fname)
                    url_dest_map[url] = dest
                    ds_files.append(dest)

        elif ds.url_type == "static_list":
            for f in ds.files:
                fname = f.inferred_filename()
                dest = str(dest_root / fname)
                url_dest_map[f.url] = dest
                ds_files.append(dest)

        elif ds.url_type == "dynamic":
            out.print(f"[yellow]⚠ {ds.id}: url_type=dynamic não suportado ainda (use módulo dedicado)[/]")
            continue

        dataset_files[ds.id] = ds_files

    if not url_dest_map:
        out.print("[yellow]Nenhuma URL para baixar. Verifique os filtros de anos e datasets.[/]")
        raise typer.Exit(0)

    # ------------------------------------------------------------------
    # Estimativas de tamanho
    # ------------------------------------------------------------------
    out.print(f"\n[bold cyan]📦 Resumo do download[/]")
    out.print(f"  Datasets selecionados : [bold]{len(datasets_to_download)}[/]")
    out.print(f"  Arquivos a baixar     : [bold]{len(url_dest_map)}[/]")
    out.print(f"  Diretório de saída    : [bold]{output_dir.resolve()}[/]")

    # Estimar tamanho total
    total_est_mb: float = 0.0
    total_ext_mb: float = 0.0
    for ds in datasets_to_download:
        selected_years_for_ds = [
            int(Path(p).stem.split("_")[-1]) if "_" in Path(p).stem else 0
            for p in dataset_files.get(ds.id, [])
        ]
        est = ds.estimate_download_mb(selected_years_for_ds or None)
        ext = ds.estimate_extracted_mb(selected_years_for_ds or None)
        if est:
            total_est_mb += est
        if ext:
            total_ext_mb += ext

    if total_est_mb > 0:
        out.print(f"  ~Tamanho download     : [bold yellow]{human_mb(total_est_mb)}[/]")
    if total_ext_mb > 0:
        out.print(f"  ~Tamanho após extração: [bold yellow]{human_mb(total_ext_mb)}[/]")

    # Checar espaço em disco
    output_dir.mkdir(parents=True, exist_ok=True)
    free = free_space_bytes(output_dir)
    out.print(f"  Espaço livre em disco : [bold]{human_size(free)}[/]")

    if total_est_mb > 0:
        required = int(total_est_mb * 1024 * 1024)
        if not check_disk_space(output_dir, required):
            out.print(f"\n[bold red]⚠ Espaço em disco potencialmente insuficiente![/]")
            if not Confirm.ask("Continuar mesmo assim?", console=out, default=False):
                raise typer.Exit(1)

    if dry_run:
        out.print("\n[bold yellow]🔍 Modo dry-run: nenhum arquivo será baixado[/]")

    if not dry_run and not Confirm.ask(
        f"\nIniciar download de {len(url_dest_map)} arquivo(s)?",
        console=out,
        default=True,
    ):
        raise typer.Exit(0)

    # ------------------------------------------------------------------
    # Criar diretórios de destino
    # ------------------------------------------------------------------
    for dest_str in url_dest_map.values():
        Path(dest_str).parent.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------
    out.print()
    summary = download_urls(url_dest_map, config, title="dados-br Download")

    # ------------------------------------------------------------------
    # Relatório final
    # ------------------------------------------------------------------
    out.print()
    color = "green" if summary.failed == 0 else "red"
    out.print(
        f"[{color}]Download concluído:[/] "
        f"[green]{summary.succeeded} ok[/] | "
        f"[red]{summary.failed} falha(s)[/] | "
        f"[dim]{summary.skipped} pulado(s)[/] | "
        f"Total: {human_size(summary.total_bytes)}"
    )

    for r in summary.results:
        if not r.success and not r.skipped:
            out.print(f"  [red]✗ {r.url}[/] — {r.error}")

    # ------------------------------------------------------------------
    # Checagens automáticas pós-download
    # ------------------------------------------------------------------
    if auto_check and not dry_run and summary.succeeded > 0:
        out.print("\n[bold cyan]🔍 Checagens automáticas pós-download[/]")
        for ds in datasets_to_download:
            if ds.checks and dataset_files.get(ds.id):
                report = run_dataset_checks(ds, output_dir)
                report.print_summary()
                if not report.all_passed:
                    out.print(f"[yellow]⚠ {report.failed} checagem(ns) falhou para {ds.id}[/]")

    if summary.failed > 0:
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# Comando: check
# ---------------------------------------------------------------------------

@app.command("check")
def cmd_check(
    dataset_id: Optional[str] = typer.Argument(
        default=None,
        help="ID do dataset (omita para checar todos os arquivos em --dir)",
    ),
    data_dir: Path = typer.Option(
        Path("dados"), "--dir", "-d",
        help="Diretório raiz dos dados baixados",
    ),
) -> None:
    """Verifica integridade dos arquivos baixados."""
    reg = _get_registry()

    if dataset_id:
        try:
            ds = reg.require(dataset_id)
        except RegistryError as exc:
            err.print(f"[red]{exc}[/]")
            raise typer.Exit(1) from exc

        report = run_dataset_checks(ds, data_dir)
        report.print_summary()
        if not report.all_passed:
            raise typer.Exit(1)

    else:
        # Checar todos os ZIPs e CSVs presentes
        if not data_dir.exists():
            err.print(f"[red]Diretório não encontrado: {data_dir}[/]")
            raise typer.Exit(1)

        files = sorted(data_dir.rglob("*.zip")) + sorted(data_dir.rglob("*.csv"))
        if not files:
            out.print(f"[yellow]Nenhum arquivo ZIP ou CSV encontrado em {data_dir}[/]")
            raise typer.Exit(0)

        out.print(f"[cyan]Checando {len(files)} arquivo(s) em {data_dir}...[/]")
        report = run_basic_checks(files)
        report.print_summary()
        if not report.all_passed:
            raise typer.Exit(1)


# ---------------------------------------------------------------------------
# Subcomandos: catalog
# ---------------------------------------------------------------------------

@catalog_app.command("validate")
def catalog_validate() -> None:
    """Valida todos os YAMLs do catálogo e reporta erros."""
    reg = _get_registry()
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
    reg = _get_registry()
    datasets = reg.all()

    out.print(f"\n[bold cyan]📊 Estatísticas do Catálogo dados-br[/]\n")
    out.print(f"  Total de datasets  : [bold]{len(datasets)}[/]")
    out.print(f"  Categorias únicas  : [bold]{len(reg.categories())}[/]")
    out.print(f"  Fontes únicas      : [bold]{len(reg.sources())}[/]")

    # Por categoria
    out.print("\n[bold]Por categoria:[/]")
    for cat in reg.categories():
        cat_ds = reg.by_category(cat)
        icon = category_icon(cat)
        out.print(f"  {icon} {cat}: [bold]{len(cat_ds)}[/] dataset(s)")

    # Por fonte
    out.print("\n[bold]Por fonte:[/]")
    for src in reg.sources():
        src_ds = reg.by_source(src)
        badge = source_badge(src)
        out.print(f"  {badge}: [bold]{len(src_ds)}[/] dataset(s)")

    # Estimativa total
    total_mb = 0.0
    for ds in datasets:
        est = ds.estimate_download_mb(ds.available_years() or None)
        if est:
            total_mb += est

    if total_mb > 0:
        out.print(f"\n  ~Volume total estimado (todos os anos): [bold yellow]{human_mb(total_mb)}[/]")

    errors = reg.load_errors()
    if errors:
        out.print(f"\n[yellow]⚠ {len(errors)} YAML(s) com erro de carregamento[/]")
        for path, exc in errors:
            out.print(f"  [red]•[/] {path.name}: {exc}")


# ---------------------------------------------------------------------------
# Subcomandos: indicators
# ---------------------------------------------------------------------------

_LEVEL_LABELS = {
    IndicatorLevel.BASICA: ("📚", "Educação Básica", "cyan"),
    IndicatorLevel.SUPERIOR: ("🎓", "Educação Superior", "magenta"),
    IndicatorLevel.TRANSVERSAL: ("🔗", "Transversal", "yellow"),
}

_CATEGORY_ICONS = {
    "desempenho":  "📊",
    "fluxo":       "🔄",
    "contexto":    "🏘",
    "docentes":    "👩‍🏫",
    "escola":      "🏫",
    "financeiro":  "💰",
    "avaliacao":   "📝",
    "qualidade":   "⭐",
    "trajetoria":  "🗺",
}


def _get_indicators() -> IndicatorRegistry:
    try:
        _global_indicators.load()
    except Exception as exc:
        err.print(f"[red]Erro ao carregar indicadores:[/] {exc}")
        raise typer.Exit(1) from exc
    return _global_indicators


@indicators_app.command("list")
def indicators_list(
    level: Optional[str] = typer.Option(
        None, "--level", "-l",
        help="Filtrar por nível: 'basica' ou 'superior'",
    ),
    category: Optional[str] = typer.Option(
        None, "--category", "-c",
        help="Filtrar por categoria (ex: docentes, fluxo, desempenho)",
    ),
    show_questions: bool = typer.Option(
        False, "--questions", "-q",
        help="Exibir número de perguntas norteadoras por indicador",
    ),
) -> None:
    """Lista indicadores educacionais do catálogo."""
    reg = _get_indicators()
    indicators = reg.all()

    if level:
        try:
            lv = IndicatorLevel(level.lower())
        except ValueError:
            err.print(f"[red]Nível inválido:[/] {level!r}. Use 'basica' ou 'superior'.")
            raise typer.Exit(1)
        indicators = [i for i in indicators if i.level == lv]

    if category:
        indicators = [i for i in indicators if i.category == category.lower()]

    if not indicators:
        out.print("[yellow]Nenhum indicador encontrado com os filtros aplicados.[/]")
        return

    table = Table(
        title=f"🇧🇷 Indicadores Educacionais dados-br ({len(indicators)} encontrados)",
        show_header=True,
        header_style="bold",
        expand=True,
    )
    table.add_column("ID", style="cyan", no_wrap=True, min_width=20)
    table.add_column("Nome", min_width=35)
    table.add_column("Nível", min_width=10)
    table.add_column("Categoria", min_width=10)
    table.add_column("Desde", justify="center", min_width=6)
    table.add_column("Datasets", justify="center", min_width=8)
    if show_questions:
        table.add_column("Perguntas", justify="center", min_width=9)

    for ind in indicators:
        icon, label, color = _LEVEL_LABELS.get(ind.level, ("", ind.level.value, "white"))
        cat_icon = _CATEGORY_ICONS.get(ind.category, "•")
        row = [
            f"[cyan]{ind.id}[/]",
            ind.name,
            f"[{color}]{icon} {ind.level.value}[/]",
            f"{cat_icon} {ind.category}",
            str(ind.available_since or "—"),
            str(len(ind.source_datasets)),
        ]
        if show_questions:
            row.append(str(len(ind.research_questions)))
        table.add_row(*row)

    out.print(table)
    out.print(f"\n[dim]Use [bold]dados-br indicators info <id>[/] para ver detalhes completos.[/]")


@indicators_app.command("info")
def indicators_info(
    indicator_id: str = typer.Argument(..., help="ID do indicador (ex: ideb, distorcao_idade_serie)"),
    no_questions: bool = typer.Option(False, "--no-questions", help="Ocultar perguntas norteadoras"),
    no_citations: bool = typer.Option(False, "--no-citations", help="Ocultar citações bibliográficas"),
) -> None:
    """Exibe informações completas de um indicador, incluindo citações e perguntas norteadoras."""
    reg = _get_indicators()
    try:
        ind = reg.require(indicator_id)
    except Exception as exc:
        err.print(f"[red]{exc}[/]")
        raise typer.Exit(1)

    icon, level_label, color = _LEVEL_LABELS.get(ind.level, ("", ind.level.value, "white"))
    cat_icon = _CATEGORY_ICONS.get(ind.category, "•")

    # Cabeçalho
    out.print(Panel(
        f"[bold]{ind.name}[/]\n"
        f"[dim]{icon} {level_label}  {cat_icon} {ind.category}  "
        f"{'📅 ' + ind.periodicity if ind.periodicity else ''}  "
        f"{'📆 desde ' + str(ind.available_since) if ind.available_since else ''}[/]",
        title=f"[cyan bold]{ind.id}[/]",
        border_style=color,
        expand=False,
    ))

    # Descrição
    out.print(f"\n[bold]Descrição[/]")
    out.print(f"  {ind.description.replace(chr(10), chr(10) + '  ')}")

    # Fórmula
    if ind.formula:
        out.print(f"\n[bold]Fórmula[/]")
        out.print(f"  [italic yellow]{ind.formula}[/]")

    # Desagregações
    if ind.disaggregations:
        out.print(f"\n[bold]Desagregações disponíveis[/]")
        out.print("  " + "  •  ".join(ind.disaggregations))

    # Datasets relacionados
    if ind.source_datasets:
        out.print(f"\n[bold]Datasets no catálogo dados-br[/]")
        for ds_id in ind.source_datasets:
            out.print(f"  [cyan]→ dados-br info {ds_id}[/]")

    # Metodologia
    if ind.methodology_url:
        out.print(f"\n[bold]Nota técnica / metodologia[/]")
        out.print(f"  [link={ind.methodology_url}]{ind.methodology_url}[/link]")

    # Perguntas norteadoras
    if not no_questions and ind.research_questions:
        out.print(f"\n[bold green]❓ Perguntas Norteadoras para Pesquisa[/] "
                  f"[dim]({len(ind.research_questions)} perguntas)[/]")
        for i, q in enumerate(ind.research_questions, 1):
            out.print(f"  [green]{i}.[/] {q}")

    # Citações bibliográficas
    if not no_citations and ind.citations:
        out.print(f"\n[bold blue]📚 Referências Bibliográficas[/] "
                  f"[dim](ABNT)[/]")
        for cite in ind.citations:
            out.print(f"  [blue]•[/] {cite}")

    out.print()


@indicators_app.command("questions")
def indicators_questions(
    level: Optional[str] = typer.Option(
        None, "--level", "-l",
        help="Filtrar por nível: 'basica' ou 'superior'",
    ),
    category: Optional[str] = typer.Option(
        None, "--category", "-c",
        help="Filtrar por categoria temática",
    ),
    dataset: Optional[str] = typer.Option(
        None, "--dataset", "-d",
        help="Filtrar por dataset do catálogo (ex: saeb, censo_escolar)",
    ),
) -> None:
    """Lista todas as perguntas norteadoras para propor pesquisas."""
    reg = _get_indicators()

    if dataset:
        questions = reg.questions_for_dataset(dataset)
        if not questions:
            out.print(f"[yellow]Nenhum indicador associado ao dataset '{dataset}'.[/]")
            return
        total = sum(len(qs) for qs in questions.values())
        out.print(f"\n[bold]❓ Perguntas norteadoras relacionadas ao dataset [cyan]{dataset}[/] "
                  f"({total} perguntas em {len(questions)} indicadores)[/]\n")
        for ind_id, qs in questions.items():
            ind = reg.get(ind_id)
            ind_name = ind.name if ind else ind_id
            out.print(f"[bold cyan]{ind_id}[/] — [italic]{ind_name}[/]")
            for i, q in enumerate(qs, 1):
                out.print(f"  [green]{i}.[/] {q}")
            out.print()
        return

    lv = None
    if level:
        try:
            lv = IndicatorLevel(level.lower())
        except ValueError:
            err.print(f"[red]Nível inválido:[/] {level!r}.")
            raise typer.Exit(1)

    all_questions = reg.all_research_questions(level=lv, category=category)
    if not all_questions:
        out.print("[yellow]Nenhuma pergunta encontrada com os filtros aplicados.[/]")
        return

    # Agrupar por indicador
    by_indicator: dict[str, list[dict]] = {}
    for q in all_questions:
        key = q["indicator_id"]
        by_indicator.setdefault(key, []).append(q)

    level_label = f" [{level}]" if level else ""
    cat_label = f" [{category}]" if category else ""
    out.print(f"\n[bold]❓ Perguntas Norteadoras{level_label}{cat_label}[/] "
              f"[dim]— {len(all_questions)} perguntas em {len(by_indicator)} indicadores[/]\n")

    for ind_id, qs in by_indicator.items():
        ind = reg.get(ind_id)
        if ind:
            icon, _, color = _LEVEL_LABELS.get(ind.level, ("", "", "white"))
            cat_icon = _CATEGORY_ICONS.get(ind.category, "•")
            out.print(
                f"[bold {color}]{icon} {ind.name}[/] "
                f"[dim]{cat_icon} {ind.category}[/]"
            )
        else:
            out.print(f"[bold]{ind_id}[/]")

        for i, q in enumerate(qs, 1):
            out.print(f"  [green]{i}.[/] {q['question']}")
        out.print()


@indicators_app.command("for-dataset")
def indicators_for_dataset(
    dataset_id: str = typer.Argument(..., help="ID do dataset (ex: saeb, censo_escolar, enem)"),
) -> None:
    """Lista indicadores e perguntas norteadoras relacionados a um dataset específico."""
    reg = _get_indicators()
    indicators = reg.by_dataset(dataset_id)

    if not indicators:
        out.print(f"[yellow]Nenhum indicador mapeado para o dataset '{dataset_id}'.[/]")
        return

    out.print(f"\n[bold]Indicadores relacionados ao dataset [cyan]{dataset_id}[/][/] "
              f"({len(indicators)} encontrados)\n")
    for ind in indicators:
        icon, _, color = _LEVEL_LABELS.get(ind.level, ("", "", "white"))
        out.print(f"  [{color}]{icon} [bold]{ind.id}[/][/] — {ind.name}")
        out.print(f"      [dim]{len(ind.research_questions)} perguntas • {len(ind.citations)} citações[/]")

    out.print(f"\n[dim]Use [bold]dados-br indicators questions --dataset {dataset_id}[/] "
              f"para ver todas as perguntas.[/]")


@indicators_app.command("validate")
def indicators_validate() -> None:
    """Valida a integridade do registry de indicadores."""
    reg = _get_indicators()
    errors = reg.validate()

    if not errors:
        out.print(f"[green]✓ Registry de indicadores válido! {len(reg)} indicadores carregados.[/]")
        return

    out.print(f"[red]✗ {len(errors)} problema(s) encontrado(s):[/]")
    for e in errors:
        out.print(f"  [red]•[/] {e}")
    raise typer.Exit(1)


# ---------------------------------------------------------------------------
# Comando: version
# ---------------------------------------------------------------------------

@app.command("version")
def cmd_version() -> None:
    """Exibe a versão do dados-br."""
    out.print(f"[bold]dados-br[/] versão [cyan]{__version__}[/]")
    out.print(f"[dim]Python {sys.version}[/]")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
