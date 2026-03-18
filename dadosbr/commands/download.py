"""
Comando: dados-br download
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.prompt import Confirm, Prompt

from ..checker import run_dataset_checks
from ..config import get_config
from ..context import emit_json, err, is_json, out
from ..downloader import DownloadConfig, download_urls
from ..manifest import write_manifest
from ..models import Dataset
from ..services import get_registry
from ..utils import (
    category_icon,
    check_disk_space,
    filename_from_url,
    free_space_bytes,
    human_mb,
    human_size,
    parse_years_expr,
)

_LOGO = "dados-br  ·  dados públicos brasileiros"


def _print_logo() -> None:
    from rich.panel import Panel
    from .. import __version__
    out.print(Panel.fit(
        f"[bold cyan]{_LOGO}[/]\n[dim]v{__version__}  ·  Apache 2.0  ·  github.com/tucaguimaraes/dados-br[/]",
        style="cyan", padding=(0, 2),
    ))


def _select_from_list(items: list[str], prompt: str, allow_all: bool = False) -> list[int]:
    for i, item in enumerate(items, 1):
        out.print(f"  [dim]{i:3}[/] {item}")
    if allow_all:
        out.print(f"  [dim]  0[/] [bold]TODOS[/]")

    raw = Prompt.ask(prompt, console=out)

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


def cmd_download(
    dataset_id: Optional[str] = typer.Argument(
        default=None,
        help="ID do dataset (omita para modo interativo)",
    ),
    all_datasets: bool = typer.Option(False, "--all", "-a", help="Baixa TODOS os datasets do catálogo"),
    years: Optional[str] = typer.Option(None, "--years", "-y", help="Anos: all, 2020-2023, 2020,2021"),
    output_dir: Optional[Path] = typer.Option(None, "--output-dir", "-o", help="Diretório raiz para salvar os dados"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simula o download sem baixar nada"),
    skip_existing: bool = typer.Option(True, "--skip-existing/--no-skip", help="Pula arquivos já existentes"),
    verify_ssl: bool = typer.Option(True, "--verify-ssl/--no-verify-ssl", help="Verifica certificados SSL"),
    retries: Optional[int] = typer.Option(None, "--retries", "-r", help="Tentativas por arquivo"),
    timeout: int = typer.Option(60, "--timeout", "-t", help="Timeout por requisição (segundos)"),
    chunk_mb: int = typer.Option(16, "--chunk-mb", help="Tamanho dos blocos de download (MB)"),
    auto_check: bool = typer.Option(True, "--check/--no-check", help="Executa checagens automáticas após o download"),
) -> None:
    """
    Baixa um ou mais datasets de dados públicos brasileiros.

    Sem argumentos: modo interativo com seleção guiada.
    Use [bold]--output json[/] para saída estruturada (compatível com pipes).
    """
    # Aplicar defaults do config file
    cfg = get_config()
    effective_output_dir = output_dir or cfg.output_dir
    effective_retries = retries if retries is not None else cfg.retries

    if not is_json():
        _print_logo()
    reg = get_registry()

    # ------------------------------------------------------------------
    # Resolver quais datasets baixar
    # ------------------------------------------------------------------
    datasets_to_download: list[Dataset] = []

    if all_datasets:
        datasets_to_download = reg.all()
        out.print(f"[yellow]⚠ Modo --all: {len(datasets_to_download)} datasets selecionados[/]")
        if not Confirm.ask(
            f"Confirmar download de TODOS os {len(datasets_to_download)} datasets?",
            console=out, default=False,
        ):
            raise typer.Exit(0)

    elif dataset_id:
        from ..registry import RegistryError
        try:
            datasets_to_download = [reg.require(dataset_id)]
        except RegistryError as exc:
            err.print(f"[red]{exc}[/]")
            raise typer.Exit(1) from exc

    else:
        if is_json():
            err.print("[red]--output json requer um DATASET_ID explícito[/]")
            raise typer.Exit(1)
        out.print("\n[bold cyan]Modo interativo — selecione os dados para baixar[/]\n")

        categories = reg.categories()
        out.print("[bold]Categorias disponíveis:[/]")
        cat_indices = _select_from_list(
            [f"{category_icon(c)} {c}" for c in categories],
            prompt="Número(s) da(s) categoria(s) [ex: 1 ou 1,2 ou 0 para todas]",
            allow_all=True,
        )
        selected_categories = [categories[i] for i in cat_indices] if cat_indices else categories

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
    # Construir mapa de downloads
    # ------------------------------------------------------------------
    config = DownloadConfig(
        output_dir=effective_output_dir,
        timeout=timeout,
        max_retries=effective_retries,
        chunk_mb=chunk_mb,
        verify_ssl=verify_ssl,
        skip_existing=skip_existing,
        dry_run=dry_run,
    )

    url_dest_map: dict[str, str] = {}
    dataset_files: dict[str, list[str]] = {}
    dataset_years: dict[str, list[int]] = {}

    for ds in datasets_to_download:
        dest_root = effective_output_dir / ds.dest_folder
        ds_files: list[str] = []

        if ds.url_type in ("pattern", "ftp"):
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
                if len(datasets_to_download) == 1 and not is_json():
                    out.print(
                        f"\n[bold]Anos disponíveis para [cyan]{ds.id}[/]: "
                        f"{available[0]}–{available[-1]}[/]"
                    )
                    years_input = Prompt.ask(
                        "Quais anos? (ex: all, 2020-2023, 2020,2022)",
                        default="all", console=out,
                    )
                    try:
                        selected_years = parse_years_expr(years_input, available)
                    except ValueError as exc:
                        err.print(f"[red]{exc}[/]")
                        raise typer.Exit(1) from exc
                else:
                    selected_years = available

            year_urls = ds.urls_for_years(selected_years)
            dataset_years[ds.id] = list(year_urls.keys())
            for _y, url_list in year_urls.items():
                for url in url_list:
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
            out.print(f"[yellow]⚠ {ds.id}: url_type=dynamic não suportado ainda[/]")
            continue

        dataset_files[ds.id] = ds_files

    if not url_dest_map:
        out.print("[yellow]Nenhuma URL para baixar. Verifique os filtros de anos e datasets.[/]")
        raise typer.Exit(0)

    # ------------------------------------------------------------------
    # Estimativas
    # ------------------------------------------------------------------
    if not is_json():
        out.print(f"\n[bold cyan]📦 Resumo do download[/]")
        out.print(f"  Datasets selecionados : [bold]{len(datasets_to_download)}[/]")
        out.print(f"  Arquivos a baixar     : [bold]{len(url_dest_map)}[/]")
        out.print(f"  Diretório de saída    : [bold]{effective_output_dir.resolve()}[/]")

        total_est_mb: float = sum(
            est for ds in datasets_to_download
            if (est := ds.estimate_download_mb(dataset_years.get(ds.id) or None))
        )
        total_ext_mb: float = sum(
            ext for ds in datasets_to_download
            if (ext := ds.estimate_extracted_mb(dataset_years.get(ds.id) or None))
        )
        if total_est_mb > 0:
            out.print(f"  ~Tamanho download     : [bold yellow]{human_mb(total_est_mb)}[/]")
        if total_ext_mb > 0:
            out.print(f"  ~Tamanho após extração: [bold yellow]{human_mb(total_ext_mb)}[/]")

        effective_output_dir.mkdir(parents=True, exist_ok=True)
        free = free_space_bytes(effective_output_dir)
        out.print(f"  Espaço livre em disco : [bold]{human_size(free)}[/]")

        if total_est_mb > 0 and not check_disk_space(effective_output_dir, int(total_est_mb * 1024 * 1024)):
            out.print(f"\n[bold red]⚠ Espaço em disco potencialmente insuficiente![/]")
            if not Confirm.ask("Continuar mesmo assim?", console=out, default=False):
                raise typer.Exit(1)

    if dry_run and not is_json():
        out.print("\n[bold yellow]🔍 Modo dry-run: nenhum arquivo será baixado[/]")

    if not dry_run and not is_json() and not Confirm.ask(
        f"\nIniciar download de {len(url_dest_map)} arquivo(s)?",
        console=out, default=True,
    ):
        raise typer.Exit(0)

    # ------------------------------------------------------------------
    # Criar diretórios e baixar
    # ------------------------------------------------------------------
    for dest_str in url_dest_map.values():
        Path(dest_str).parent.mkdir(parents=True, exist_ok=True)

    out.print()
    summary = download_urls(url_dest_map, config, title="dados-br Download")

    # ------------------------------------------------------------------
    # Checagens + Manifests
    # ------------------------------------------------------------------
    check_reports_by_ds: dict[str, dict] = {}
    manifest_paths: dict[str, str] = {}

    if auto_check and not dry_run and summary.succeeded > 0:
        if not is_json():
            out.print("\n[bold cyan]🔍 Checagens automáticas pós-download[/]")
        for ds in datasets_to_download:
            if ds.checks and dataset_files.get(ds.id):
                rpt = run_dataset_checks(ds, effective_output_dir)
                check_dict = {
                    "dataset_id": rpt.dataset_id,
                    "all_passed": rpt.all_passed,
                    "passed": rpt.passed,
                    "failed": rpt.failed,
                    "results": [
                        {"check_type": cr.check_type, "file": str(cr.file),
                         "passed": cr.passed, "message": cr.message}
                        for cr in rpt.results
                    ],
                }
                check_reports_by_ds[ds.id] = check_dict
                if not is_json():
                    rpt.print_summary()
                    if not rpt.all_passed:
                        out.print(f"[yellow]⚠ {rpt.failed} checagem(ns) falhou para {ds.id}[/]")

    for ds in datasets_to_download:
        if dataset_files.get(ds.id) is not None:
            try:
                mpath = write_manifest(
                    ds=ds,
                    output_dir=effective_output_dir,
                    summary=summary,
                    dataset_file_paths=dataset_files[ds.id],
                    dry_run=dry_run,
                    check_report=check_reports_by_ds.get(ds.id),
                )
                manifest_paths[ds.id] = str(mpath)
                if not is_json():
                    out.print(f"  [dim]📄 manifest: {mpath}[/]")
            except Exception as exc:
                err.print(f"[yellow]⚠ Não foi possível gravar manifest para {ds.id}: {exc}[/]")

    # ------------------------------------------------------------------
    # Relatório final
    # ------------------------------------------------------------------
    if is_json():
        emit_json({
            "dry_run": dry_run,
            "datasets": [ds.id for ds in datasets_to_download],
            "files_total": summary.total,
            "succeeded": summary.succeeded,
            "failed": summary.failed,
            "skipped": summary.skipped,
            "total_bytes": summary.total_bytes,
            "manifests": manifest_paths,
            "checks": list(check_reports_by_ds.values()),
            "results": [
                {
                    "url": r.url,
                    "dest": str(r.dest),
                    "success": r.success,
                    "skipped": r.skipped,
                    "size_bytes": r.size_bytes,
                    "elapsed_seconds": round(r.elapsed_seconds, 2),
                    "error": r.error,
                }
                for r in summary.results
            ],
        })
        if summary.failed > 0:
            raise typer.Exit(1)
        return

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

    if summary.failed > 0:
        raise typer.Exit(1)
