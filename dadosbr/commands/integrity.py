"""
Comandos de integridade: check, verify.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.table import Table

from ..checker import DatasetCheckReport, run_basic_checks, run_dataset_checks
from ..context import emit_json, err, is_json, out
from ..manifest import ManifestVerifyReport, verify_manifest
from ..services import get_registry


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------

_STATUS_ICON: dict[str, tuple[str, str]] = {
    "ok":       ("[green]✓[/]",                "ok — hash confere"),
    "mismatch": ("[bold red]✗ CORROMPIDO[/]",   "hash diverge — arquivo pode estar corrompido"),
    "missing":  ("[red]✗ AUSENTE[/]",           "arquivo não encontrado em disco"),
    "no_hash":  ("[yellow]? sem hash[/]",        "manifest não registrou hash (versão antiga ou dry-run)"),
    "skipped":  ("[dim]⏭ skip[/]",             "arquivo pulado — hash não coletado"),
}


def _check_report_to_dict(rpt: DatasetCheckReport) -> dict:
    return {
        "dataset_id": rpt.dataset_id,
        "all_passed": rpt.all_passed,
        "passed": rpt.passed,
        "failed": rpt.failed,
        "results": [
            {
                "check_type": cr.check_type,
                "file": str(cr.file),
                "passed": cr.passed,
                "message": cr.message,
            }
            for cr in rpt.results
        ],
    }


def _verify_report_to_dict(rpt: ManifestVerifyReport) -> dict:
    return {
        "dataset": rpt.dataset,
        "manifest": str(rpt.manifest_path),
        "timestamp": rpt.timestamp,
        "all_ok": rpt.all_ok,
        "ok": rpt.ok_count,
        "mismatch": rpt.mismatch_count,
        "missing": rpt.missing_count,
        "no_hash": rpt.no_hash_count,
        "skipped": rpt.skipped_count,
        "results": [
            {
                "filename": r.filename,
                "status": r.status,
                "expected_sha256": r.expected_sha256,
                "actual_sha256": r.actual_sha256,
            }
            for r in rpt.results
        ],
    }


def _print_verify_report(rpt: ManifestVerifyReport) -> None:
    color = "green" if rpt.all_ok else "red"
    status_label = "[green]OK[/]" if rpt.all_ok else "[bold red]FALHA[/]"
    out.print(
        f"\n[bold]Verificação [{color}]{rpt.dataset}[/][/] — {status_label}  "
        f"[dim](manifest: {rpt.manifest_path.name})[/]"
    )
    table = Table(show_header=True, header_style="bold dim", box=None, padding=(0, 1))
    table.add_column("Status", no_wrap=True, min_width=18)
    table.add_column("Arquivo", min_width=40)
    table.add_column("Detalhe", style="dim")

    for r in rpt.results:
        icon, detail = _STATUS_ICON.get(r.status, ("?", r.status))
        table.add_row(icon, r.filename, detail)
    out.print(table)

    parts = []
    if rpt.ok_count:       parts.append(f"[green]{rpt.ok_count} ok[/]")
    if rpt.skipped_count:  parts.append(f"[dim]{rpt.skipped_count} skip[/]")
    if rpt.mismatch_count: parts.append(f"[bold red]{rpt.mismatch_count} corrompido(s)[/]")
    if rpt.missing_count:  parts.append(f"[red]{rpt.missing_count} ausente(s)[/]")
    if rpt.no_hash_count:  parts.append(f"[yellow]{rpt.no_hash_count} sem hash[/]")
    out.print("  " + " | ".join(parts))


# ---------------------------------------------------------------------------
# Comando: check
# ---------------------------------------------------------------------------

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
    reg = get_registry()

    if dataset_id:
        from ..registry import RegistryError
        try:
            ds = reg.require(dataset_id)
        except RegistryError as exc:
            err.print(f"[red]{exc}[/]")
            raise typer.Exit(1) from exc

        report = run_dataset_checks(ds, data_dir)
        if is_json():
            emit_json(_check_report_to_dict(report))
        else:
            report.print_summary()
        if not report.all_passed:
            raise typer.Exit(1)

    else:
        if not data_dir.exists():
            err.print(f"[red]Diretório não encontrado: {data_dir}[/]")
            raise typer.Exit(1)

        files = sorted(data_dir.rglob("*.zip")) + sorted(data_dir.rglob("*.csv"))
        if not files:
            if is_json():
                emit_json({"dataset_id": None, "all_passed": True, "passed": 0, "failed": 0, "results": []})
            else:
                out.print(f"[yellow]Nenhum arquivo ZIP ou CSV encontrado em {data_dir}[/]")
            raise typer.Exit(0)

        if not is_json():
            out.print(f"[cyan]Checando {len(files)} arquivo(s) em {data_dir}...[/]")
        report = run_basic_checks(files)
        if is_json():
            emit_json(_check_report_to_dict(report))
        else:
            report.print_summary()
        if not report.all_passed:
            raise typer.Exit(1)


# ---------------------------------------------------------------------------
# Comando: verify
# ---------------------------------------------------------------------------

def cmd_verify(
    dataset_id: Optional[str] = typer.Argument(
        default=None,
        help="ID do dataset (omita para verificar todos os manifests em --dir)",
    ),
    data_dir: Path = typer.Option(
        Path("dados"), "--dir", "-d",
        help="Diretório raiz dos dados baixados",
    ),
) -> None:
    """
    Verifica integridade dos arquivos via SHA256 registrado no manifest.json.

    Detecta arquivos corrompidos, ausentes ou alterados desde o download.
    """
    # Localizar manifest(s)
    manifest_paths_found: list[Path] = []

    if dataset_id:
        from ..registry import RegistryError
        reg = get_registry()
        try:
            ds = reg.require(dataset_id)
        except RegistryError as exc:
            err.print(f"[red]{exc}[/]")
            raise typer.Exit(1) from exc
        candidate = data_dir / ds.dest_folder / "manifest.json"
        if not candidate.exists():
            err.print(f"[red]manifest.json não encontrado:[/] {candidate}")
            err.print(f"[dim]Rode primeiro: dados-br download {dataset_id}[/]")
            raise typer.Exit(1)
        manifest_paths_found.append(candidate)
    else:
        if not data_dir.exists():
            err.print(f"[red]Diretório não encontrado:[/] {data_dir}")
            raise typer.Exit(1)
        manifest_paths_found = sorted(data_dir.rglob("manifest.json"))
        if not manifest_paths_found:
            out.print(f"[yellow]Nenhum manifest.json encontrado em {data_dir}[/]")
            out.print("[dim]Execute downloads primeiro para gerar manifests.[/]")
            raise typer.Exit(0)

    # Verificar cada manifest
    all_reports: list[ManifestVerifyReport] = []
    any_failure = False

    for mpath in manifest_paths_found:
        try:
            rpt = verify_manifest(mpath)
        except Exception as exc:
            err.print(f"[red]Erro ao ler {mpath}:[/] {exc}")
            any_failure = True
            continue

        all_reports.append(rpt)
        if not rpt.all_ok:
            any_failure = True

    if is_json():
        emit_json([_verify_report_to_dict(r) for r in all_reports])
    else:
        for rpt in all_reports:
            _print_verify_report(rpt)

        total_ok = sum(r.ok_count for r in all_reports)
        total_bad = sum(r.mismatch_count + r.missing_count for r in all_reports)
        out.print(
            f"\n[bold]Total:[/] {len(all_reports)} dataset(s) verificado(s) — "
            f"[green]{total_ok} arquivo(s) íntegro(s)[/]"
            + (f" | [bold red]{total_bad} problema(s)[/]" if total_bad else "")
        )

    if any_failure:
        raise typer.Exit(1)
