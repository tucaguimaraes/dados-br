"""
Subcomandos de indicadores educacionais: list, info, questions, for-dataset, validate.
"""

from __future__ import annotations

from typing import Optional

import typer

from ..context import err, out
from ..indicators import IndicatorLevel
from ..services import get_indicators

indicators_app = typer.Typer(help="Indicadores educacionais brasileiros.")

# ---------------------------------------------------------------------------
# Mapeamentos de ícones
# ---------------------------------------------------------------------------

_LEVEL_LABELS = {
    IndicatorLevel.BASICA:      ("📚", "Educação Básica",   "cyan"),
    IndicatorLevel.SUPERIOR:    ("🎓", "Educação Superior", "magenta"),
    IndicatorLevel.TRANSVERSAL: ("🔗", "Transversal",       "yellow"),
}

_CATEGORY_ICONS: dict[str, str] = {
    "desempenho": "📊",
    "fluxo":      "🔄",
    "contexto":   "🏘",
    "docentes":   "👩‍🏫",
    "escola":     "🏫",
    "financeiro": "💰",
    "avaliacao":  "📝",
    "qualidade":  "⭐",
    "trajetoria": "🗺",
}


# ---------------------------------------------------------------------------
# Subcomandos
# ---------------------------------------------------------------------------

@indicators_app.command("list")
def indicators_list(
    level: Optional[str] = typer.Option(
        None, "--level", "-l",
        help="Filtrar por nível: 'basica' ou 'superior'",
    ),
    category: Optional[str] = typer.Option(
        None, "--category", "-c",
        help="Filtrar por categoria (ex: docentes, fluxo, desempenho)",
    ),
    show_questions: bool = typer.Option(
        False, "--questions", "-q",
        help="Exibir número de perguntas norteadoras por indicador",
    ),
) -> None:
    """Lista indicadores educacionais do catálogo."""
    from rich.table import Table

    reg = get_indicators()
    indicators = reg.all()

    if level:
        try:
            lv = IndicatorLevel(level.lower())
        except ValueError:
            err.print(f"[red]Nível inválido:[/] {level!r}. Use 'basica' ou 'superior'.")
            raise typer.Exit(1)
        indicators = [i for i in indicators if i.level == lv]

    if category:
        indicators = [i for i in indicators if i.category == category.lower()]

    if not indicators:
        out.print("[yellow]Nenhum indicador encontrado com os filtros aplicados.[/]")
        return

    table = Table(
        title=f"🇧🇷 Indicadores Educacionais dados-br ({len(indicators)} encontrados)",
        show_header=True,
        header_style="bold",
        expand=True,
    )
    table.add_column("ID", style="cyan", no_wrap=True, min_width=20)
    table.add_column("Nome", min_width=35)
    table.add_column("Nível", min_width=10)
    table.add_column("Categoria", min_width=10)
    table.add_column("Desde", justify="center", min_width=6)
    table.add_column("Datasets", justify="center", min_width=8)
    if show_questions:
        table.add_column("Perguntas", justify="center", min_width=9)

    for ind in indicators:
        icon, label, color = _LEVEL_LABELS.get(ind.level, ("", ind.level.value, "white"))
        cat_icon = _CATEGORY_ICONS.get(ind.category, "•")
        row = [
            f"[cyan]{ind.id}[/]",
            ind.name,
            f"[{color}]{icon} {ind.level.value}[/]",
            f"{cat_icon} {ind.category}",
            str(ind.available_since or "—"),
            str(len(ind.source_datasets)),
        ]
        if show_questions:
            row.append(str(len(ind.research_questions)))
        table.add_row(*row)

    out.print(table)
    out.print(f"\n[dim]Use [bold]dados-br indicators info <id>[/] para ver detalhes completos.[/]")


@indicators_app.command("info")
def indicators_info(
    indicator_id: str = typer.Argument(..., help="ID do indicador (ex: ideb, distorcao_idade_serie)"),
    no_questions: bool = typer.Option(False, "--no-questions", help="Ocultar perguntas norteadoras"),
    no_citations: bool = typer.Option(False, "--no-citations", help="Ocultar citações bibliográficas"),
) -> None:
    """Exibe informações completas de um indicador, incluindo citações e perguntas norteadoras."""
    from rich.panel import Panel

    reg = get_indicators()
    try:
        ind = reg.require(indicator_id)
    except Exception as exc:
        err.print(f"[red]{exc}[/]")
        raise typer.Exit(1)

    icon, level_label, color = _LEVEL_LABELS.get(ind.level, ("", ind.level.value, "white"))
    cat_icon = _CATEGORY_ICONS.get(ind.category, "•")

    out.print(Panel(
        f"[bold]{ind.name}[/]\n"
        f"[dim]{icon} {level_label}  {cat_icon} {ind.category}  "
        f"{'📅 ' + ind.periodicity if ind.periodicity else ''}  "
        f"{'📆 desde ' + str(ind.available_since) if ind.available_since else ''}[/]",
        title=f"[cyan bold]{ind.id}[/]",
        border_style=color,
        expand=False,
    ))

    out.print(f"\n[bold]Descrição[/]")
    out.print(f"  {ind.description.replace(chr(10), chr(10) + '  ')}")

    if ind.formula:
        out.print(f"\n[bold]Fórmula[/]")
        out.print(f"  [italic yellow]{ind.formula}[/]")

    if ind.disaggregations:
        out.print(f"\n[bold]Desagregações disponíveis[/]")
        out.print("  " + "  •  ".join(ind.disaggregations))

    if ind.source_datasets:
        out.print(f"\n[bold]Datasets no catálogo dados-br[/]")
        for ds_id in ind.source_datasets:
            out.print(f"  [cyan]→ dados-br info {ds_id}[/]")

    if ind.methodology_url:
        out.print(f"\n[bold]Nota técnica / metodologia[/]")
        out.print(f"  [link={ind.methodology_url}]{ind.methodology_url}[/link]")

    if not no_questions and ind.research_questions:
        out.print(
            f"\n[bold green]❓ Perguntas Norteadoras para Pesquisa[/] "
            f"[dim]({len(ind.research_questions)} perguntas)[/]"
        )
        for i, q in enumerate(ind.research_questions, 1):
            out.print(f"  [green]{i}.[/] {q}")

    if not no_citations and ind.citations:
        out.print(
            f"\n[bold blue]📚 Referências Bibliográficas[/] "
            f"[dim](ABNT)[/]"
        )
        for cite in ind.citations:
            out.print(f"  [blue]•[/] {cite}")

    out.print()


@indicators_app.command("questions")
def indicators_questions(
    level: Optional[str] = typer.Option(
        None, "--level", "-l",
        help="Filtrar por nível: 'basica' ou 'superior'",
    ),
    category: Optional[str] = typer.Option(
        None, "--category", "-c",
        help="Filtrar por categoria temática",
    ),
    dataset: Optional[str] = typer.Option(
        None, "--dataset", "-d",
        help="Filtrar por dataset do catálogo (ex: saeb, censo_escolar)",
    ),
) -> None:
    """Lista todas as perguntas norteadoras para propor pesquisas."""
    reg = get_indicators()

    if dataset:
        questions = reg.questions_for_dataset(dataset)
        if not questions:
            out.print(f"[yellow]Nenhum indicador associado ao dataset '{dataset}'.[/]")
            return
        total = sum(len(qs) for qs in questions.values())
        out.print(
            f"\n[bold]❓ Perguntas norteadoras relacionadas ao dataset [cyan]{dataset}[/] "
            f"({total} perguntas em {len(questions)} indicadores)[/]\n"
        )
        for ind_id, qs in questions.items():
            ind = reg.get(ind_id)
            ind_name = ind.name if ind else ind_id
            out.print(f"[bold cyan]{ind_id}[/] — [italic]{ind_name}[/]")
            for i, q in enumerate(qs, 1):
                out.print(f"  [green]{i}.[/] {q}")
            out.print()
        return

    lv = None
    if level:
        try:
            lv = IndicatorLevel(level.lower())
        except ValueError:
            err.print(f"[red]Nível inválido:[/] {level!r}.")
            raise typer.Exit(1)

    all_questions = reg.all_research_questions(level=lv, category=category)
    if not all_questions:
        out.print("[yellow]Nenhuma pergunta encontrada com os filtros aplicados.[/]")
        return

    by_indicator: dict[str, list[dict]] = {}
    for q in all_questions:
        key = q["indicator_id"]
        by_indicator.setdefault(key, []).append(q)

    level_label = f" [{level}]" if level else ""
    cat_label = f" [{category}]" if category else ""
    out.print(
        f"\n[bold]❓ Perguntas Norteadoras{level_label}{cat_label}[/] "
        f"[dim]— {len(all_questions)} perguntas em {len(by_indicator)} indicadores[/]\n"
    )

    for ind_id, qs in by_indicator.items():
        ind = reg.get(ind_id)
        if ind:
            icon, _, color = _LEVEL_LABELS.get(ind.level, ("", "", "white"))
            cat_icon = _CATEGORY_ICONS.get(ind.category, "•")
            out.print(
                f"[bold {color}]{icon} {ind.name}[/] "
                f"[dim]{cat_icon} {ind.category}[/]"
            )
        else:
            out.print(f"[bold]{ind_id}[/]")

        for i, q in enumerate(qs, 1):
            out.print(f"  [green]{i}.[/] {q['question']}")
        out.print()


@indicators_app.command("for-dataset")
def indicators_for_dataset(
    dataset_id: str = typer.Argument(..., help="ID do dataset (ex: saeb, censo_escolar, enem)"),
) -> None:
    """Lista indicadores e perguntas norteadoras relacionados a um dataset específico."""
    reg = get_indicators()
    indicators = reg.by_dataset(dataset_id)

    if not indicators:
        out.print(f"[yellow]Nenhum indicador mapeado para o dataset '{dataset_id}'.[/]")
        return

    out.print(
        f"\n[bold]Indicadores relacionados ao dataset [cyan]{dataset_id}[/][/] "
        f"({len(indicators)} encontrados)\n"
    )
    for ind in indicators:
        icon, _, color = _LEVEL_LABELS.get(ind.level, ("", "", "white"))
        out.print(f"  [{color}]{icon} [bold]{ind.id}[/][/] — {ind.name}")
        out.print(f"      [dim]{len(ind.research_questions)} perguntas • {len(ind.citations)} citações[/]")

    out.print(
        f"\n[dim]Use [bold]dados-br indicators questions --dataset {dataset_id}[/] "
        f"para ver todas as perguntas.[/]"
    )


@indicators_app.command("validate")
def indicators_validate() -> None:
    """Valida a integridade do registry de indicadores."""
    reg = get_indicators()
    errors = reg.validate()

    if not errors:
        out.print(f"[green]✓ Registry de indicadores válido! {len(reg)} indicadores carregados.[/]")
        return

    out.print(f"[red]✗ {len(errors)} problema(s) encontrado(s):[/]")
    for e in errors:
        out.print(f"  [red]•[/] {e}")
    raise typer.Exit(1)
