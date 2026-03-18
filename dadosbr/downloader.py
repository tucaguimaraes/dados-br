"""
Engine de download: HTTP (httpx) + FTP (urllib) com Rich progress bars,
retry com backoff exponencial, resume de downloads parciais e checagem de espaço.
"""

from __future__ import annotations

import ftplib
import logging
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx
from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)

from .utils import check_disk_space, clean_url, filename_from_url, human_size

logger = logging.getLogger(__name__)
console = Console(stderr=True)

USER_AGENT = "dados-br/0.1 (+https://github.com/tucaguimaraes/dados-br)"

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

@dataclass
class DownloadConfig:
    output_dir: Path
    timeout: int = 60
    max_retries: int = 4
    chunk_mb: int = 16
    verify_ssl: bool = True
    skip_existing: bool = True
    dry_run: bool = False
    parallel: int = 1  # reservado para futuro suporte async


@dataclass
class DownloadResult:
    url: str
    dest: Path
    success: bool
    skipped: bool = False
    size_bytes: int = 0
    elapsed_seconds: float = 0.0
    error: Optional[str] = None


@dataclass
class DownloadSummary:
    results: list[DownloadResult] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def succeeded(self) -> int:
        return sum(1 for r in self.results if r.success)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if not r.success and not r.skipped)

    @property
    def skipped(self) -> int:
        return sum(1 for r in self.results if r.skipped)

    @property
    def total_bytes(self) -> int:
        return sum(r.size_bytes for r in self.results if r.success)


# ---------------------------------------------------------------------------
# Cliente HTTP
# ---------------------------------------------------------------------------

def build_http_client(config: DownloadConfig) -> httpx.Client:
    transport = httpx.HTTPTransport(retries=2)
    return httpx.Client(
        transport=transport,
        timeout=httpx.Timeout(config.timeout, connect=15),
        verify=config.verify_ssl,
        follow_redirects=True,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Connection": "keep-alive",
        },
    )


def probe_url(client: httpx.Client, url: str) -> tuple[bool, int]:
    """
    Faz HEAD (ou GET streaming) para verificar disponibilidade e tamanho.

    Returns:
        (available, content_length_bytes)
    """
    url = clean_url(url)
    try:
        r = client.head(url)
        if r.status_code >= 400:
            return False, 0
        size = int(r.headers.get("content-length", 0))
        if size == 0:
            # Alguns servidores não respondem ao HEAD com content-length
            with client.stream("GET", url) as rg:
                rg.raise_for_status()
                size = int(rg.headers.get("content-length", 0))
        return True, size
    except Exception as exc:
        logger.debug("probe_url falhou para %s: %s", url, exc)
        return False, 0


# ---------------------------------------------------------------------------
# Download HTTP
# ---------------------------------------------------------------------------

def _download_http(
    client: httpx.Client,
    url: str,
    dest: Path,
    *,
    total_hint: int,
    config: DownloadConfig,
    progress: Progress,
    task_id: TaskID,
) -> DownloadResult:
    url = clean_url(url)
    tmp = dest.with_suffix(dest.suffix + ".part")
    chunk_size = max(1, config.chunk_mb) * (1 << 20)
    start = time.monotonic()

    # Skip se já existe com tamanho correto
    if dest.exists() and config.skip_existing:
        if total_hint > 0 and dest.stat().st_size == total_hint:
            progress.update(task_id, completed=total_hint or 1, total=total_hint or 1)
            return DownloadResult(
                url=url, dest=dest, success=True, skipped=True,
                size_bytes=dest.stat().st_size,
            )
        if total_hint == 0:
            progress.update(task_id, completed=1, total=1)
            return DownloadResult(
                url=url, dest=dest, success=True, skipped=True,
                size_bytes=dest.stat().st_size,
            )

    if config.dry_run:
        progress.update(task_id, completed=1, total=1)
        return DownloadResult(url=url, dest=dest, success=True, skipped=True)

    resume_from = tmp.stat().st_size if tmp.exists() else 0

    for attempt in range(1, config.max_retries + 1):
        try:
            headers: dict[str, str] = {}
            if resume_from > 0:
                headers["Range"] = f"bytes={resume_from}-"

            with client.stream("GET", url, headers=headers) as r:
                if r.status_code not in (200, 206):
                    raise IOError(f"HTTP {r.status_code}: {url}")

                cl = r.headers.get("content-length")
                total = total_hint
                if cl:
                    inc = int(cl)
                    total = inc + (resume_from if r.status_code == 206 else 0)

                if total > 0 and not check_disk_space(dest.parent, total - resume_from):
                    return DownloadResult(
                        url=url, dest=dest, success=False,
                        error=f"Espaço insuficiente (~{human_size(total - resume_from)} necessários)",
                    )

                progress.update(task_id, total=total or None, completed=resume_from)

                mode = "ab" if (resume_from > 0 and r.status_code == 206) else "wb"
                downloaded = resume_from

                dest.parent.mkdir(parents=True, exist_ok=True)
                with open(tmp, mode) as f:
                    for chunk in r.iter_bytes(chunk_size=chunk_size):
                        if not chunk:
                            continue
                        f.write(chunk)
                        downloaded += len(chunk)
                        progress.update(task_id, completed=downloaded)

            tmp.rename(dest)
            elapsed = time.monotonic() - start
            return DownloadResult(
                url=url, dest=dest, success=True,
                size_bytes=dest.stat().st_size,
                elapsed_seconds=elapsed,
            )

        except Exception as exc:
            logger.warning("Tentativa %d/%d falhou para %s: %s", attempt, config.max_retries, url, exc)
            if attempt < config.max_retries:
                wait = min(30, 2 ** attempt)
                time.sleep(wait)

    return DownloadResult(
        url=url, dest=dest, success=False,
        error=f"Falhou após {config.max_retries} tentativas",
    )


# ---------------------------------------------------------------------------
# Download FTP
# ---------------------------------------------------------------------------

def _download_ftp(
    url: str,
    dest: Path,
    *,
    config: DownloadConfig,
    progress: Progress,
    task_id: TaskID,
) -> DownloadResult:
    """Download via FTP usando urllib (para DATASUS e IBGE FTP)."""
    url = clean_url(url)
    start = time.monotonic()

    if dest.exists() and config.skip_existing:
        progress.update(task_id, completed=1, total=1)
        return DownloadResult(
            url=url, dest=dest, success=True, skipped=True,
            size_bytes=dest.stat().st_size,
        )

    if config.dry_run:
        progress.update(task_id, completed=1, total=1)
        return DownloadResult(url=url, dest=dest, success=True, skipped=True)

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")

    for attempt in range(1, config.max_retries + 1):
        try:
            parsed = urlparse(url)
            ftp_host = parsed.hostname or ""
            ftp_path = parsed.path

            def _progress_hook(block_count: int, block_size: int, total_size: int) -> None:
                downloaded = block_count * block_size
                progress.update(task_id, completed=min(downloaded, total_size), total=total_size or None)

            urllib.request.urlretrieve(url, str(tmp), reporthook=_progress_hook)
            tmp.rename(dest)
            elapsed = time.monotonic() - start
            return DownloadResult(
                url=url, dest=dest, success=True,
                size_bytes=dest.stat().st_size,
                elapsed_seconds=elapsed,
            )
        except Exception as exc:
            logger.warning("FTP tentativa %d/%d falhou: %s — %s", attempt, config.max_retries, url, exc)
            if attempt < config.max_retries:
                time.sleep(min(30, 2 ** attempt))

    return DownloadResult(
        url=url, dest=dest, success=False,
        error=f"FTP falhou após {config.max_retries} tentativas",
    )


# ---------------------------------------------------------------------------
# Orquestrador principal
# ---------------------------------------------------------------------------

def download_urls(
    url_map: dict[str, str],
    config: DownloadConfig,
    *,
    title: str = "Baixando arquivos",
) -> DownloadSummary:
    """
    Baixa uma lista de URLs para seus destinos correspondentes.

    Args:
        url_map: {url: dest_path_str} mapeando URL → caminho de destino.
        config: Configurações de download.
        title: Título exibido na progress bar.

    Returns:
        DownloadSummary com resultados individuais.
    """
    summary = DownloadSummary()
    if not url_map:
        return summary

    http_client = build_http_client(config)

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=False,
    )

    with progress, http_client:
        for url, dest_str in url_map.items():
            dest = Path(dest_str)
            filename = dest.name
            task_id = progress.add_task(f"[cyan]{filename[:50]}", total=None)

            is_ftp = url.startswith("ftp://")

            # Sonda o tamanho (só HTTP)
            total_hint = 0
            if not is_ftp and not config.dry_run:
                ok, size = probe_url(http_client, url)
                if not ok:
                    progress.update(task_id, description=f"[red]✗ {filename[:45]} (indisponível)")
                    summary.results.append(
                        DownloadResult(url=url, dest=dest, success=False, error="URL indisponível")
                    )
                    continue
                total_hint = size

            if is_ftp:
                result = _download_ftp(url, dest, config=config, progress=progress, task_id=task_id)
            else:
                result = _download_http(
                    http_client, url, dest,
                    total_hint=total_hint,
                    config=config,
                    progress=progress,
                    task_id=task_id,
                )

            status = "⏭ skip" if result.skipped else ("✓" if result.success else "✗")
            color = "dim" if result.skipped else ("green" if result.success else "red")
            label = f"[{color}]{status} {filename[:50]}"
            progress.update(task_id, description=label)
            summary.results.append(result)

    return summary


def probe_all_sizes(
    url_list: list[str],
    config: DownloadConfig,
) -> dict[str, int]:
    """
    Sonda o tamanho de múltiplas URLs em sequência.

    Returns:
        {url: size_bytes} — size=0 se não foi possível determinar.
    """
    sizes: dict[str, int] = {}
    client = build_http_client(config)

    with client:
        with Progress(
            SpinnerColumn(),
            TextColumn("[dim]Verificando tamanhos... {task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("", total=len(url_list))
            for url in url_list:
                if url.startswith("ftp://"):
                    sizes[url] = 0
                else:
                    _, size = probe_url(client, url)
                    sizes[url] = size
                progress.advance(task)

    return sizes
