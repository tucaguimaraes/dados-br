"""
dados-br CLI — interface de linha de comando com Typer + Rich.

Comandos:
    dados-br list              Lista datasets do catálogo
    dados-br info <id>         Informações detalhadas sobre um dataset
    dados-br download          Baixa um ou mais datasets (interativo ou via flags)
    dados-br check             Verifica arquivos baixados (ZIP/CSV)
    dados-br verify            Verifica integridade via SHA256 (manifest)
    dados-br status            Resumo dos datasets baixados localmente
    dados-br catalog           Subcomandos de catálogo (validate, stats)
    dados-br indicators        Subcomandos de indicadores educacionais
    dados-br version           Exibe a versão instalada
"""

from __future__ import annotations

from typing import Optional

import typer

from .context import set_output_format

# ---------------------------------------------------------------------------
# App principal
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="dados-br",
    help="Acesso a dados públicos brasileiros via linha de comando.",
    no_args_is_help=True,
    rich_markup_mode="rich",
)


@app.callback()
def _global_options(
    output: str = typer.Option(
        "text",
        "--output",
        help="Formato de saída: [bold]text[/] (padrão) ou [bold]json[/] (para pipes)",
        show_default=True,
    ),
) -> None:
    """
    dados-br · dados públicos brasileiros

    Use [bold]--output json[/] para saída estruturada compatível com pipes (| jq).
    """
    if output not in ("text", "json"):
        typer.echo(f"Formato inválido: {output!r}. Use 'text' ou 'json'.", err=True)
        raise typer.Exit(1)
    set_output_format(output)


# ---------------------------------------------------------------------------
# Comandos raiz
# ---------------------------------------------------------------------------

from .commands.catalog import cmd_list, cmd_info, catalog_app          # noqa: E402
from .commands.download import cmd_download                             # noqa: E402
from .commands.integrity import cmd_check, cmd_verify                  # noqa: E402
from .commands.system import cmd_version, cmd_status                   # noqa: E402
from .commands.indicators import indicators_app                        # noqa: E402

app.command("list")(cmd_list)
app.command("info")(cmd_info)
app.command("download")(cmd_download)
app.command("check")(cmd_check)
app.command("verify")(cmd_verify)
app.command("status")(cmd_status)
app.command("version")(cmd_version)

# ---------------------------------------------------------------------------
# Sub-aplicativos montados como grupos de comandos
# ---------------------------------------------------------------------------

app.add_typer(catalog_app,    name="catalog",    help="Comandos de catálogo (validate, stats).")
app.add_typer(indicators_app, name="indicators", help="Indicadores educacionais brasileiros.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
