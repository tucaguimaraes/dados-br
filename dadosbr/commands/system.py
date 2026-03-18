"""
Comandos de sistema: version, status.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer

from ..context import emit_json, err, is_json, out
from ..utils import human_size


# ---------------------------------------------------------------------------
# Comando: version
# ---------------------------------------------------------------------------

def cmd_version() -> None:
    """Exibe a versão do dados-br."""
    from .. import __version__
    if is_json():
        emit_json({"version": __version__, "python": sys.version})
        return
    out.print(f"[bold]dados-br[/] versão [cyan]{__version__}[/]")
    out.print(f"[dim]Python {sys.version}[/]")


# ---------------------------------------------------------------------------
# Comando: status
# ---------------------------------------------------------------------------

def cmd_status(
    data_dir: Path = typer.Option(
        Path("dados"), "--dir", "-d",
        help="Diretório raiz dos dados baixados",
    ),
) -> None:
    """
    Exibe um resumo dos datasets baixados e seu estado de integridade.

    Lê os manifests gerados pelos downloads e apresenta uma visão consolidada
    de quais dados estão disponíveis localmente.
    """
    from rich.table import Table

    if not data_dir.exists():
        if is_json():
            emit_json({"data_dir": str(data_dir), "datasets": [], "total_bytes": 0})
        else:
            out.print(f"[yellow]Diretório de dados não encontrado: {data_dir.resolve()}[/]")
            out.print("[dim]Execute [bold]dados-br download <dataset>[/] para começar.[/]")
        raise typer.Exit(0)

    manifest_paths = sorted(data_dir.rglob("manifest.json"))

    if not manifest_paths:
        if is_json():
            emit_json({"data_dir": str(data_dir.resolve()), "datasets": [], "total_bytes": 0})
        else:
            out.print(f"[yellow]Nenhum manifest.json encontrado em {data_dir.resolve()}[/]")
            out.print("[dim]Execute [bold]dados-br download <dataset>[/] para começar.[/]")
        raise typer.Exit(0)

    # Carregar registry opcionalmente (para obter nomes amigáveis)
    registry = None
    try:
        from ..services import get_registry
        registry = get_registry()
    except Exception:
        pass  # Funciona sem registry — só mostra IDs

    rows = []
    total_bytes_all = 0

    for mpath in manifest_paths:
        try:
            data = json.loads(mpath.read_text(encoding="utf-8"))
        except Exception as exc:
            err.print(f"[yellow]⚠ Não foi possível ler {mpath}: {exc}[/]")
            continue

        dataset_id = data.get("dataset_id", "?")
        timestamp = data.get("timestamp", "")[:19].replace("T", " ")
        files = data.get("files", [])
        dry_run = data.get("dry_run", False)
        schema = data.get("schema_version", "1")

        total_bytes = sum(f.get("size_bytes", 0) for f in files if isinstance(f, dict))
        file_count = len(files)
        total_bytes_all += total_bytes

        # Status de integridade: baseado nos arquivos com sha256
        files_with_hash = [f for f in files if isinstance(f, dict) and f.get("sha256")]
        integrity = "—"
        if files_with_hash:
            integrity = f"[green]✓[/] {len(files_with_hash)} hashes"
        elif schema == "1":
            integrity = "[dim]sem hash (v1)[/]"
        elif dry_run:
            integrity = "[dim]dry-run[/]"

        # Nome amigável via registry
        friendly_name = dataset_id
        if registry:
            try:
                ds = registry.get(dataset_id)
                if ds:
                    friendly_name = ds.name
            except Exception:
                pass

        rows.append({
            "dataset_id": dataset_id,
            "name": friendly_name,
            "timestamp": timestamp,
            "file_count": file_count,
            "total_bytes": total_bytes,
            "integrity": integrity,
            "dry_run": dry_run,
            "manifest": str(mpath),
        })

    if is_json():
        emit_json({
            "data_dir": str(data_dir.resolve()),
            "datasets": [
                {k: v for k, v in row.items() if k != "integrity"}
                for row in rows
            ],
            "total_bytes": total_bytes_all,
        })
        return

    # Render tabela
    table = Table(
        title=f"📂 dados-br — Datasets baixados em {data_dir.resolve()}",
        title_style="bold cyan",
        show_lines=False,
        expand=True,
    )
    table.add_column("#",          style="dim",    width=4,  no_wrap=True)
    table.add_column("Dataset",    style="bold",            no_wrap=True)
    table.add_column("Nome",                       min_width=28)
    table.add_column("Baixado em",                 no_wrap=True)
    table.add_column("Arquivos",   justify="right", no_wrap=True)
    table.add_column("Tamanho",    justify="right", no_wrap=True)
    table.add_column("Integridade",                no_wrap=True)

    for i, row in enumerate(rows, 1):
        flags = []
        if row["dry_run"]:
            flags.append("[dim]dry-run[/]")
        name_display = row["name"] if row["name"] != row["dataset_id"] else "[dim]—[/]"
        table.add_row(
            str(i),
            row["dataset_id"],
            name_display,
            f"[dim]{row['timestamp']}[/]",
            str(row["file_count"]),
            human_size(row["total_bytes"]) if row["total_bytes"] else "[dim]—[/]",
            row["integrity"] + ("  " + "  ".join(flags) if flags else ""),
        )

    out.print()
    out.print(table)
    out.print(
        f"\n[bold]Total:[/] {len(rows)} dataset(s) · "
        f"[bold]{human_size(total_bytes_all)}[/] em disco\n"
    )
    out.print(
        "[dim]Use [bold]dados-br verify[/] para verificar integridade via SHA256 · "
        "[bold]dados-br check[/] para validar arquivos ZIP/CSV.[/]"
    )
