"""
Serviços compartilhados entre os comandos da CLI.

Centraliza o carregamento do registry e dos indicadores, evitando
duplicação e garantindo que os erros de inicialização sejam tratados
de forma consistente.
"""

from __future__ import annotations

import typer

from .context import err
from .indicators import IndicatorRegistry, indicator_registry as _global_indicators
from .registry import Registry, RegistryError, registry as _global_registry


def get_registry() -> Registry:
    """Carrega e retorna o registry de datasets. Encerra com Exit(1) em falha."""
    try:
        _global_registry.load()
    except Exception as exc:
        err.print(f"[red]Erro ao carregar catálogo: {exc}[/]")
        raise typer.Exit(1) from exc
    return _global_registry


def get_indicators() -> IndicatorRegistry:
    """Carrega e retorna o registry de indicadores. Encerra com Exit(1) em falha."""
    try:
        _global_indicators.load()
    except Exception as exc:
        err.print(f"[red]Erro ao carregar indicadores: {exc}[/]")
        raise typer.Exit(1) from exc
    return _global_indicators
