"""
Utilitários compartilhados: formatação, parsing de anos, espaço em disco.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Formatação humana
# ---------------------------------------------------------------------------

def human_size(n: int | float) -> str:
    """Converte bytes para string legível (ex: 1.23 GB)."""
    units = ["B", "KB", "MB", "GB", "TB"]
    x = float(n)
    for unit in units[:-1]:
        if x < 1024.0:
            return f"{x:.2f} {unit}"
        x /= 1024.0
    return f"{x:.2f} {units[-1]}"


def human_mb(mb: float) -> str:
    """Converte MB para string legível."""
    return human_size(int(mb * 1024 * 1024))


def human_duration(seconds: float) -> str:
    """Converte segundos em string legível."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        m, s = divmod(int(seconds), 60)
        return f"{m}m{s:02d}s"
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h}h{m:02d}m{s:02d}s"


# ---------------------------------------------------------------------------
# Parsing de anos
# ---------------------------------------------------------------------------

def parse_years_expr(expr: str, available: list[int]) -> list[int]:
    """
    Interpreta uma expressão de anos e retorna anos válidos da lista disponível.

    Formatos aceitos:
        all             → todos os anos disponíveis
        2020            → apenas 2020
        2020-2023       → intervalo fechado
        2020,2022,2023  → lista explícita
        2010-2014,2020  → combinação de intervalos e listas
    """
    expr = expr.strip().lower()
    if expr == "all":
        return sorted(available)

    requested: set[int] = set()
    for part in expr.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            raw_a, raw_b = part.split("-", 1)
            try:
                a, b = int(raw_a.strip()), int(raw_b.strip())
            except ValueError as e:
                raise ValueError(f"Intervalo inválido: {part!r}") from e
            requested.update(range(min(a, b), max(a, b) + 1))
        else:
            try:
                requested.add(int(part))
            except ValueError as e:
                raise ValueError(f"Ano inválido: {part!r}") from e

    available_set = set(available)
    result = sorted(y for y in requested if y in available_set)
    return result


def validate_years_expr(expr: str) -> bool:
    """Valida sintaxe de expressão de anos sem executar."""
    expr = expr.strip().lower()
    if expr == "all":
        return True
    pattern = r"^\d{4}(-\d{4})?(,\d{4}(-\d{4})?)*$"
    return bool(re.match(pattern, expr.strip()))


# ---------------------------------------------------------------------------
# Disco
# ---------------------------------------------------------------------------

def check_disk_space(dest_dir: Path, required_bytes: int, margin: float = 1.1) -> bool:
    """
    Verifica se há espaço livre suficiente.

    Args:
        dest_dir: Diretório de destino (deve existir ou sua raiz existir).
        required_bytes: Bytes necessários.
        margin: Multiplicador de segurança (padrão 10% extra).

    Returns:
        True se houver espaço suficiente (ou se required_bytes <= 0).
    """
    if required_bytes <= 0:
        return True
    try:
        check_path = dest_dir
        while not check_path.exists() and check_path != check_path.parent:
            check_path = check_path.parent
        _, _, free = shutil.disk_usage(check_path)
        return free >= int(required_bytes * margin)
    except Exception:
        return True  # não bloquear por erro de checagem


def free_space_bytes(path: Path) -> int:
    """Retorna bytes livres no disco que contém o path."""
    try:
        check_path = path
        while not check_path.exists():
            check_path = check_path.parent
        _, _, free = shutil.disk_usage(check_path)
        return free
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# URLs
# ---------------------------------------------------------------------------

def clean_url(url: str) -> str:
    """Sanitiza URLs que possam ter artefatos HTML ou duplicações de protocolo."""
    url = re.sub(r"</?br[^>]*>", "", url, flags=re.IGNORECASE).strip()
    url = url.replace("https://https://", "https://")
    url = url.replace("http://http://", "http://")
    url = url.replace("ftp://ftp.dabrtasus.gov.br", "ftp://ftp.datasus.gov.br")
    url = re.sub(r"</[^>]*>", "", url)  # remove tags HTML residuais
    return url.strip()


def filename_from_url(url: str, fallback: str = "arquivo") -> str:
    """Extrai o nome do arquivo de uma URL."""
    url = clean_url(url)
    parts = url.rstrip("/").split("/")
    name = parts[-1].split("?")[0] if parts else fallback
    return name if name else fallback


# ---------------------------------------------------------------------------
# Formatação de tabela
# ---------------------------------------------------------------------------

def category_icon(category: str) -> str:
    """Retorna emoji associado à categoria."""
    icons = {
        "educacao": "🎓",
        "saude": "🏥",
        "geografia": "🗺️",
        "trabalho": "💼",
        "saneamento": "💧",
        "ambiente": "🌿",
        "economia": "📈",
    }
    return icons.get(category.lower(), "📦")


def source_badge(source: str) -> str:
    """Retorna badge colorido para a fonte."""
    badges = {
        "INEP/MEC": "[bold blue]INEP[/]",
        "IBGE": "[bold green]IBGE[/]",
        "DATASUS": "[bold red]DATASUS[/]",
        "SNIS": "[bold yellow]SNIS[/]",
        "SEDUC-GO": "[bold magenta]SEDUC-GO[/]",
        "dadosabertos.go.gov.br": "[bold magenta]GO[/]",
    }
    return badges.get(source, f"[cyan]{source}[/]")
