"""
dados-br — Ferramenta open source para catalogar, baixar, validar
e organizar dados públicos brasileiros.

Uso rápido:
    from dadosbr import registry, indicator_registry

    # Datasets do catálogo
    datasets = registry.all()

    # Indicadores educacionais
    ideb = indicator_registry.get("ideb")
    print(ideb.research_questions)
    print(ideb.citations)
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("dados-br")
except PackageNotFoundError:
    __version__ = "0.1.0-dev"

__all__ = ["__version__"]
