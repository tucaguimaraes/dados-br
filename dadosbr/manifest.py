"""
Geração e verificação de manifest.json por dataset.

O manifest registra: dataset, timestamp, arquivos, URLs, tamanhos,
hashes SHA256 e status — criando um histórico rastreável e verificável
de cada execução de download.

Localização: <output_dir>/<dest_folder>/manifest.json
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .downloader import DownloadResult, DownloadSummary
    from .models import Dataset

logger = logging.getLogger(__name__)

# Versão do schema — incrementar quando a estrutura mudar de forma incompatível
MANIFEST_SCHEMA_VERSION = "2"


# ---------------------------------------------------------------------------
# SHA256 auxiliar (também exportado para uso externo)
# ---------------------------------------------------------------------------

def sha256_file(path: Path, chunk_mb: int = 4) -> str:
    """Calcula SHA256 de um arquivo em chunks (seguro para arquivos grandes)."""
    import hashlib
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_mb << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Resultado de verificação
# ---------------------------------------------------------------------------

@dataclass
class FileVerifyResult:
    filename: str
    path: Path
    expected_sha256: str | None
    actual_sha256: str | None
    status: str  # "ok" | "mismatch" | "missing" | "no_hash" | "skipped"

    @property
    def ok(self) -> bool:
        return self.status in ("ok", "skipped")

    @property
    def corrupted(self) -> bool:
        return self.status == "mismatch"


@dataclass
class ManifestVerifyReport:
    manifest_path: Path
    dataset: str
    timestamp: str
    results: list[FileVerifyResult] = field(default_factory=list)

    @property
    def ok_count(self) -> int:
        return sum(1 for r in self.results if r.status == "ok")

    @property
    def skipped_count(self) -> int:
        return sum(1 for r in self.results if r.status == "skipped")

    @property
    def mismatch_count(self) -> int:
        return sum(1 for r in self.results if r.status == "mismatch")

    @property
    def missing_count(self) -> int:
        return sum(1 for r in self.results if r.status == "missing")

    @property
    def no_hash_count(self) -> int:
        return sum(1 for r in self.results if r.status == "no_hash")

    @property
    def all_ok(self) -> bool:
        return self.mismatch_count == 0 and self.missing_count == 0


# ---------------------------------------------------------------------------
# Construção do manifest
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
    failed    = sum(1 for r in ds_results if not r.success and not r.skipped)
    skipped   = sum(1 for r in ds_results if r.skipped)
    total_bytes = sum(r.size_bytes for r in ds_results if r.success)

    files = []
    for r in ds_results:
        # Para arquivos pulados (skip_existing), calcula o hash agora se o arquivo existe
        sha = r.sha256
        if sha is None and r.skipped and r.dest.exists():
            try:
                sha = sha256_file(r.dest)
            except Exception as exc:
                logger.warning("Não foi possível calcular SHA256 de %s: %s", r.dest, exc)

        files.append({
            "filename": r.dest.name,
            "url": r.url,
            "dest": str(r.dest),
            "size_bytes": r.size_bytes,
            "sha256": sha,
            "success": r.success,
            "skipped": r.skipped,
            "elapsed_seconds": round(r.elapsed_seconds, 2),
            "error": r.error,
        })

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
        "files": files,
    }

    if check_report is not None:
        manifest["checks"] = check_report

    return manifest


# ---------------------------------------------------------------------------
# Escrita
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

    Returns:
        Path do manifest.json gravado.
    """
    dest_dir = output_dir / ds.dest_folder
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest_set = set(dataset_file_paths)
    ds_results = [r for r in summary.results if str(r.dest) in dest_set]

    manifest = _build_manifest(ds, dest_dir, ds_results, dry_run, check_report)

    manifest_path = dest_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.debug("Manifest gravado: %s", manifest_path)
    return manifest_path


# ---------------------------------------------------------------------------
# Leitura
# ---------------------------------------------------------------------------

def read_manifest(manifest_path: Path) -> dict:
    """Lê um manifest.json existente."""
    return json.loads(manifest_path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Verificação de integridade
# ---------------------------------------------------------------------------

def verify_manifest(manifest_path: Path) -> ManifestVerifyReport:
    """
    Verifica a integridade dos arquivos listados em um manifest.json.

    Para cada arquivo com sha256 registrado:
    - Recomputa o hash do arquivo em disco
    - Compara com o valor armazenado

    Possíveis status por arquivo:
      "ok"       — arquivo presente e hash confere
      "mismatch" — arquivo presente mas hash difere (corrompido ou alterado)
      "missing"  — arquivo não encontrado em disco
      "no_hash"  — manifest não registrou hash (dry_run ou versão antiga)
      "skipped"  — arquivo foi pulado no download e não tem hash registrado

    Returns:
        ManifestVerifyReport com resultado por arquivo.
    """
    raw = read_manifest(manifest_path)
    report = ManifestVerifyReport(
        manifest_path=manifest_path,
        dataset=raw.get("dataset", "unknown"),
        timestamp=raw.get("timestamp", ""),
    )

    for entry in raw.get("files", []):
        path = Path(entry["dest"])
        expected = entry.get("sha256")
        was_skipped = entry.get("skipped", False)

        if expected is None:
            status = "skipped" if was_skipped else "no_hash"
            report.results.append(FileVerifyResult(
                filename=entry["filename"],
                path=path,
                expected_sha256=None,
                actual_sha256=None,
                status=status,
            ))
            continue

        if not path.exists():
            report.results.append(FileVerifyResult(
                filename=entry["filename"],
                path=path,
                expected_sha256=expected,
                actual_sha256=None,
                status="missing",
            ))
            continue

        try:
            actual = sha256_file(path)
        except Exception as exc:
            logger.warning("Erro ao ler %s para verificação: %s", path, exc)
            report.results.append(FileVerifyResult(
                filename=entry["filename"],
                path=path,
                expected_sha256=expected,
                actual_sha256=None,
                status="missing",
            ))
            continue

        status = "ok" if actual == expected else "mismatch"
        report.results.append(FileVerifyResult(
            filename=entry["filename"],
            path=path,
            expected_sha256=expected,
            actual_sha256=actual,
            status=status,
        ))

    return report
