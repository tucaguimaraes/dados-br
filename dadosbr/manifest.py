"""
Geração de manifest.json por dataset após cada execução de download.

O manifest registra: dataset, timestamp, arquivos, URLs, tamanhos, status
e um resumo da execução — criando um histórico rastreável de cada download.

Localização: <output_dir>/<dest_folder>/manifest.json
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .downloader import DownloadResult, DownloadSummary
    from .models import Dataset

logger = logging.getLogger(__name__)

# Versão do schema do manifest — incrementar se a estrutura mudar
MANIFEST_SCHEMA_VERSION = "1"


# ---------------------------------------------------------------------------
# Estrutura do manifest
# ---------------------------------------------------------------------------

def _build_manifest(
    ds: "Dataset",
    dest_dir: Path,
    ds_results: "list[DownloadResult]",
    dry_run: bool,
    check_report: dict | None = None,
) -> dict:
    """Constrói o dicionário do manifest para um dataset."""
    succeeded = sum(1 for r in ds_results if r.success)
    failed = sum(1 for r in ds_results if not r.success and not r.skipped)
    skipped = sum(1 for r in ds_results if r.skipped)
    total_bytes = sum(r.size_bytes for r in ds_results if r.success)

    manifest: dict = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "dataset": ds.id,
        "dataset_name": ds.name,
        "source": ds.source,
        "category": ds.category,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dry_run": dry_run,
        "output_dir": str(dest_dir.resolve()),
        "summary": {
            "total_files": len(ds_results),
            "succeeded": succeeded,
            "failed": failed,
            "skipped": skipped,
            "total_bytes": total_bytes,
            "all_succeeded": failed == 0,
        },
        "files": [
            {
                "filename": r.dest.name,
                "url": r.url,
                "dest": str(r.dest),
                "size_bytes": r.size_bytes,
                "success": r.success,
                "skipped": r.skipped,
                "elapsed_seconds": round(r.elapsed_seconds, 2),
                "error": r.error,
            }
            for r in ds_results
        ],
    }

    if check_report is not None:
        manifest["checks"] = check_report

    return manifest


# ---------------------------------------------------------------------------
# Escrita do manifest
# ---------------------------------------------------------------------------

def write_manifest(
    ds: "Dataset",
    output_dir: Path,
    summary: "DownloadSummary",
    dataset_file_paths: list[str],
    dry_run: bool,
    check_report: dict | None = None,
) -> Path:
    """
    Gera e salva o manifest.json do dataset no diretório de destino.

    Args:
        ds: Dataset cujo manifest será gerado.
        output_dir: Diretório raiz de saída (ex: Path("dados")).
        summary: Resultado completo do download (todos os datasets).
        dataset_file_paths: Caminhos dos arquivos deste dataset.
        dry_run: Indica se foi uma simulação sem download real.
        check_report: Relatório de checagens pós-download, se disponível.

    Returns:
        Path do manifest.json gravado.
    """
    dest_dir = output_dir / ds.dest_folder
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Filtrar resultados que pertencem a este dataset
    dest_set = set(dataset_file_paths)
    ds_results = [r for r in summary.results if str(r.dest) in dest_set]

    manifest = _build_manifest(ds, dest_dir, ds_results, dry_run, check_report)

    manifest_path = dest_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.debug("Manifest gravado: %s", manifest_path)
    return manifest_path


def read_manifest(manifest_path: Path) -> dict:
    """Lê um manifest.json existente."""
    return json.loads(manifest_path.read_text(encoding="utf-8"))
