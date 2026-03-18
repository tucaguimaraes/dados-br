"""
Extrator de arquivos comprimidos (ZIP principal, com placeholder para DBC).

Usa zipfile da stdlib + Rich para progresso de extração.
DBC (formato DATASUS) requer dbfread ou blast-dbf opcionais.
"""

from __future__ import annotations

import logging
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
)

from .utils import human_size

logger = logging.getLogger(__name__)
console = Console(stderr=True)


@dataclass
class ExtractResult:
    source: Path
    dest_dir: Path
    success: bool
    files_extracted: int = 0
    total_bytes: int = 0
    error: Optional[str] = None


@dataclass
class ExtractSummary:
    results: list[ExtractResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def succeeded(self) -> int:
        return sum(1 for r in self.results if r.success)

    @property
    def total_bytes(self) -> int:
        return sum(r.total_bytes for r in self.results if r.success)


def estimate_zip_size(zip_path: Path) -> int:
    """Estima tamanho descomprimido sem extrair (soma dos tamanhos não comprimidos)."""
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            return sum(info.file_size for info in zf.infolist())
    except Exception:
        return 0


def validate_zip(zip_path: Path) -> tuple[bool, Optional[str]]:
    """
    Valida integridade de um arquivo ZIP.

    Returns:
        (valid, error_message)
    """
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            bad = zf.testzip()
            if bad:
                return False, f"Arquivo corrompido dentro do ZIP: {bad}"
        return True, None
    except zipfile.BadZipFile as exc:
        return False, f"ZIP inválido: {exc}"
    except Exception as exc:
        return False, f"Erro ao verificar ZIP: {exc}"


def extract_zip(
    zip_path: Path,
    dest_dir: Path,
    *,
    overwrite: bool = False,
    progress: Optional[Progress] = None,
    task_id: Optional[TaskID] = None,
) -> ExtractResult:
    """
    Extrai um arquivo ZIP para dest_dir.

    Args:
        zip_path: Caminho do arquivo ZIP.
        dest_dir: Diretório de destino.
        overwrite: Se True, sobrescreve arquivos existentes.
        progress: Instância de Rich Progress para atualização visual.
        task_id: ID da tarefa no progress.
    """
    dest_dir.mkdir(parents=True, exist_ok=True)

    try:
        valid, err = validate_zip(zip_path)
        if not valid:
            return ExtractResult(
                source=zip_path, dest_dir=dest_dir, success=False,
                error=err or "ZIP inválido",
            )

        with zipfile.ZipFile(zip_path, "r") as zf:
            members = zf.infolist()
            total_size = sum(m.file_size for m in members)

            if progress and task_id is not None:
                progress.update(task_id, total=len(members), completed=0)

            extracted_count = 0
            extracted_bytes = 0

            for i, member in enumerate(members):
                target = dest_dir / member.filename
                if not overwrite and target.exists():
                    pass  # pula mas conta
                else:
                    zf.extract(member, dest_dir)
                    extracted_count += 1
                    extracted_bytes += member.file_size

                if progress and task_id is not None:
                    progress.update(task_id, completed=i + 1)

        return ExtractResult(
            source=zip_path,
            dest_dir=dest_dir,
            success=True,
            files_extracted=extracted_count,
            total_bytes=extracted_bytes,
        )

    except Exception as exc:
        logger.error("Erro ao extrair %s: %s", zip_path, exc)
        return ExtractResult(
            source=zip_path, dest_dir=dest_dir, success=False,
            error=str(exc),
        )


def extract_many(
    zip_paths: list[Path],
    dest_dir: Path,
    *,
    overwrite: bool = False,
) -> ExtractSummary:
    """
    Extrai múltiplos ZIPs para dest_dir (ou subpastas por nome do arquivo).

    Cada ZIP é extraído em dest_dir/<nome_sem_extensão>/.
    """
    summary = ExtractSummary()

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total} arquivos"),
        TimeRemainingColumn(),
        console=console,
    )

    with progress:
        for zip_path in zip_paths:
            sub_dir = dest_dir / zip_path.stem
            task_id = progress.add_task(
                f"[green]Extraindo {zip_path.name[:45]}",
                total=None,
            )
            result = extract_zip(
                zip_path, sub_dir,
                overwrite=overwrite,
                progress=progress,
                task_id=task_id,
            )
            status_icon = "✓" if result.success else "✗"
            color = "green" if result.success else "red"
            progress.update(
                task_id,
                description=f"[{color}]{status_icon} {zip_path.name[:50]}",
            )
            summary.results.append(result)

    return summary
