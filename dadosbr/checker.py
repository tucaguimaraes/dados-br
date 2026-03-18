"""
Checagens automáticas pós-download.

Verifica integridade, formato e conteúdo mínimo dos arquivos baixados,
usando Rich spinners para feedback visual durante as verificações.
"""

from __future__ import annotations

import logging
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .extractor import validate_zip
from .models import CheckConfig, Dataset
from .utils import human_size

logger = logging.getLogger(__name__)
console = Console()


# ---------------------------------------------------------------------------
# Resultados
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    check_type: str
    file: Path
    passed: bool
    message: str
    detail: Optional[str] = None


@dataclass
class DatasetCheckReport:
    dataset_id: str
    results: list[CheckResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.passed)

    @property
    def all_passed(self) -> bool:
        return self.failed == 0

    def print_summary(self) -> None:
        table = Table(
            title=f"Checagens — {self.dataset_id}",
            show_lines=False,
            expand=False,
        )
        table.add_column("Tipo", style="cyan", no_wrap=True)
        table.add_column("Arquivo", style="white")
        table.add_column("Status", justify="center")
        table.add_column("Mensagem")

        for r in self.results:
            icon = "✓" if r.passed else "✗"
            color = "green" if r.passed else "red"
            table.add_row(
                r.check_type,
                r.file.name[:50],
                f"[{color}]{icon}[/]",
                r.message,
            )

        console.print(table)
        color = "green" if self.all_passed else "red"
        console.print(
            f"[{color}]Total: {self.passed} passou / {self.failed} falhou[/]"
        )


# ---------------------------------------------------------------------------
# Checagens individuais
# ---------------------------------------------------------------------------

def check_file_exists(file: Path) -> CheckResult:
    exists = file.exists() and file.is_file()
    return CheckResult(
        check_type="file_exists",
        file=file,
        passed=exists,
        message="Arquivo encontrado" if exists else "Arquivo não encontrado",
    )


def check_zip_valid(file: Path) -> CheckResult:
    if not file.exists():
        return CheckResult(
            check_type="zip_valid", file=file, passed=False,
            message="Arquivo não existe (não é possível validar ZIP)",
        )
    valid, err = validate_zip(file)
    return CheckResult(
        check_type="zip_valid",
        file=file,
        passed=valid,
        message="ZIP íntegro" if valid else f"ZIP inválido: {err}",
    )


def check_min_size(file: Path, min_mb: float) -> CheckResult:
    if not file.exists():
        return CheckResult(
            check_type="min_size_mb", file=file, passed=False,
            message=f"Arquivo não existe (mínimo: {min_mb} MB)",
        )
    size_mb = file.stat().st_size / (1024 * 1024)
    passed = size_mb >= min_mb
    return CheckResult(
        check_type="min_size_mb",
        file=file,
        passed=passed,
        message=(
            f"{size_mb:.1f} MB ≥ {min_mb} MB ✓"
            if passed
            else f"{size_mb:.1f} MB < {min_mb} MB (muito pequeno)"
        ),
    )


def check_csv_readable(file: Path) -> CheckResult:
    """Verifica se um CSV pode ser lido pelo pandas (amostra das primeiras 100 linhas)."""
    try:
        import pandas as pd  # noqa: PLC0415

        # Tentar detectar separador e encoding
        for sep in (",", ";", "\t"):
            for enc in ("utf-8", "latin-1", "cp1252"):
                try:
                    df = pd.read_csv(file, sep=sep, encoding=enc, nrows=100)
                    if len(df.columns) > 1:
                        return CheckResult(
                            check_type="csv_readable",
                            file=file,
                            passed=True,
                            message=f"CSV legível: {len(df.columns)} colunas, sep={sep!r}, enc={enc}",
                        )
                except Exception:
                    continue

        return CheckResult(
            check_type="csv_readable",
            file=file,
            passed=False,
            message="CSV não pôde ser lido com separadores e encodings comuns",
        )
    except ImportError:
        return CheckResult(
            check_type="csv_readable",
            file=file,
            passed=False,
            message="pandas não instalado — checagem CSV ignorada",
        )


def check_row_count(file: Path, min_rows: int) -> CheckResult:
    """Verifica se um CSV/Parquet tem pelo menos min_rows linhas."""
    try:
        import pandas as pd  # noqa: PLC0415

        suffix = file.suffix.lower()
        if suffix == ".parquet":
            df = pd.read_parquet(file)
        elif suffix in (".csv", ".txt"):
            df = pd.read_csv(file, low_memory=False)
        else:
            return CheckResult(
                check_type="row_count",
                file=file,
                passed=False,
                message=f"Formato não suportado para row_count: {suffix}",
            )

        rows = len(df)
        passed = rows >= min_rows
        return CheckResult(
            check_type="row_count",
            file=file,
            passed=passed,
            message=(
                f"{rows:,} linhas ≥ {min_rows:,} ✓"
                if passed
                else f"{rows:,} linhas < {min_rows:,} (muito poucas)"
            ),
        )
    except ImportError:
        return CheckResult(
            check_type="row_count",
            file=file,
            passed=False,
            message="pandas não instalado — checagem row_count ignorada",
        )
    except Exception as exc:
        return CheckResult(
            check_type="row_count",
            file=file,
            passed=False,
            message=f"Erro ao contar linhas: {exc}",
        )


def check_dbc_exists(file: Path) -> CheckResult:
    """Verifica se arquivo DBC (DATASUS) existe e tem tamanho não-nulo."""
    exists = file.exists() and file.is_file() and file.stat().st_size > 0
    return CheckResult(
        check_type="dbc_exists",
        file=file,
        passed=exists,
        message=(
            f"DBC encontrado ({human_size(file.stat().st_size)})"
            if exists
            else "DBC não encontrado ou vazio",
        ),
    )


# ---------------------------------------------------------------------------
# Mapeamento tipo → função
# ---------------------------------------------------------------------------

def _run_check(cfg: CheckConfig, file: Path) -> CheckResult:
    """Executa uma checagem individual com base na configuração."""
    t = cfg.type
    if t == "file_exists":
        return check_file_exists(file)
    if t == "zip_valid":
        return check_zip_valid(file)
    if t == "min_size_mb":
        min_mb = float(cfg.value or 1)
        return check_min_size(file, min_mb)
    if t == "csv_readable":
        return check_csv_readable(file)
    if t == "row_count":
        min_rows = int(cfg.value or 1)
        return check_row_count(file, min_rows)
    if t == "dbc_exists":
        return check_dbc_exists(file)
    return CheckResult(
        check_type=t,
        file=file,
        passed=False,
        message=f"Tipo de checagem desconhecido: {t!r}",
    )


# ---------------------------------------------------------------------------
# Checagem de um dataset
# ---------------------------------------------------------------------------

def run_dataset_checks(
    dataset: Dataset,
    data_dir: Path,
) -> DatasetCheckReport:
    """
    Executa todas as checagens configuradas para um dataset.

    Descobre automaticamente os arquivos no diretório de destino
    e aplica as verificações configuradas em dataset.checks.

    Args:
        dataset: Dataset com configuração de checagens.
        data_dir: Raiz do diretório de dados (ex: ./dados).

    Returns:
        DatasetCheckReport com todos os resultados.
    """
    report = DatasetCheckReport(dataset_id=dataset.id)
    dest = data_dir / dataset.dest_folder

    if not dest.exists():
        report.results.append(
            CheckResult(
                check_type="directory_exists",
                file=dest,
                passed=False,
                message=f"Diretório de destino não encontrado: {dest}",
            )
        )
        return report

    # Coletar arquivos baixados
    all_files = sorted(dest.rglob("*"))
    downloaded_files = [f for f in all_files if f.is_file() and not f.name.endswith(".part")]

    if not downloaded_files:
        report.results.append(
            CheckResult(
                check_type="directory_exists",
                file=dest,
                passed=False,
                message=f"Nenhum arquivo encontrado em {dest}",
            )
        )
        return report

    with Progress(
        SpinnerColumn(),
        TextColumn("[dim]Checando {task.description}..."),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task(dataset.id, total=len(downloaded_files) * len(dataset.checks))

        for file in downloaded_files:
            for cfg in dataset.checks:
                progress.update(task, description=f"{file.name} [{cfg.type}]")
                result = _run_check(cfg, file)
                report.results.append(result)
                progress.advance(task)

    return report


def run_basic_checks(files: list[Path]) -> DatasetCheckReport:
    """
    Checagem básica (exists + zip_valid + min_size) para uma lista de arquivos
    sem configuração de dataset.
    """
    report = DatasetCheckReport(dataset_id="ad-hoc")
    for f in files:
        report.results.append(check_file_exists(f))
        if f.suffix.lower() == ".zip" and f.exists():
            report.results.append(check_zip_valid(f))
            report.results.append(check_min_size(f, min_mb=0.1))
        elif f.suffix.lower() == ".csv" and f.exists():
            report.results.append(check_csv_readable(f))
    return report
