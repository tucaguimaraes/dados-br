"""
Estado global de apresentação da CLI.

Centraliza o formato de saída (text | json), os consoles Rich compartilhados
e os helpers de emissão de JSON — evitando variáveis globais espalhadas.
"""

from __future__ import annotations

import json

from rich.console import Console

# Consoles compartilhados entre todos os módulos de comando
out = Console()
err = Console(stderr=True)

# ---------------------------------------------------------------------------
# Formato de saída — modificado pelo callback --output antes de cada comando
# ---------------------------------------------------------------------------

_output_format: str = "text"


def set_output_format(fmt: str) -> None:
    """Define o formato de saída. Chamado pelo @app.callback() em cli.py."""
    global _output_format
    _output_format = fmt


def is_json() -> bool:
    """Retorna True quando o usuário solicitou --output json."""
    return _output_format == "json"


def emit_json(data: object) -> None:
    """Escreve JSON puro em stdout — compatível com pipes (| jq)."""
    print(json.dumps(data, ensure_ascii=False, indent=2))
