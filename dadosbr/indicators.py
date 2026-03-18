"""
dados-br — Módulo de indicadores educacionais e sociais.

Fornece modelos, registry e helpers para os indicadores:
    - Educação Básica  (15 indicadores INEP: IDEB, TDI, Inse, AFD, ...)
    - Educação Superior (4 indicadores INEP: Fluxo, Trajetória, CPC/IGC, ...)
    - IBGE Social       (5 indicadores: analfabetismo, frequência, NEET, instrução, PeNSE)
    - DATASUS Saúde     (4 indicadores: mortalidade infantil, causas externas, SINASC, atenção básica)
    - Financeiro        (4 indicadores: gasto/aluno, vinculação constitucional, FUNDEB, execução federal)
    - Outros            (6 indicadores: transparência, MP, C&T, saneamento, prefeituras, Goiás)

Uso rápido:
    from dadosbr.indicators import indicator_registry, IndicatorLevel

    todos = indicator_registry.all()
    basicos = indicator_registry.by_level(IndicatorLevel.BASICA)
    transversais = indicator_registry.by_level(IndicatorLevel.TRANSVERSAL)
    ideb = indicator_registry.get("ideb")

    print(ideb.research_questions)
    print(ideb.citations)
    print(indicator_registry.questions_for_dataset("censo_escolar"))
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

import yaml

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_PACKAGE_ROOT = Path(__file__).parent
_INDICATORS_DIR = _PACKAGE_ROOT.parent / "catalog" / "indicators"

def _discover_level_files() -> list[tuple[str, Path]]:
    """
    Descobre automaticamente todos os YAMLs em catalog/indicators/.
    Retorna lista de (level, path) para que múltiplos arquivos do mesmo
    nível (ex: vários 'transversal') sejam todos carregados.
    """
    if not _INDICATORS_DIR.exists():
        return []
    result = []
    for yf in sorted(_INDICATORS_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(yf.read_text(encoding="utf-8"))
            level = data.get("level", yf.stem)
        except Exception:
            level = yf.stem
        result.append((level, yf))
    return result


# ---------------------------------------------------------------------------
# Enums e modelos leves (sem Pydantic — compatível sem instalação)
# ---------------------------------------------------------------------------

class IndicatorLevel(str, Enum):
    BASICA = "basica"
    SUPERIOR = "superior"
    TRANSVERSAL = "transversal"


class IndicatorCategory(str, Enum):
    DESEMPENHO = "desempenho"
    FLUXO = "fluxo"
    CONTEXTO = "contexto"
    DOCENTES = "docentes"
    ESCOLA = "escola"
    FINANCEIRO = "financeiro"
    AVALIACAO = "avaliacao"
    QUALIDADE = "qualidade"
    TRAJETORIA = "trajetoria"


class Indicator:
    """
    Representa um indicador educacional com metadados, citações e perguntas norteadoras.

    Attributes:
        id: Identificador único snake_case (ex: 'ideb', 'distorcao_idade_serie')
        name: Nome completo do indicador
        level: Nível de ensino (basica ou superior)
        category: Categoria temática
        description: Descrição metodológica completa
        periodicity: Periodicidade de cálculo (anual, bienal, trienal)
        available_since: Ano de início da série histórica
        methodology_url: URL da nota técnica/metodologia no INEP
        disaggregations: Desagregações disponíveis (escola, município, estado, ...)
        source_datasets: IDs de datasets do catálogo dados-br relacionados
        citations: Lista de referências bibliográficas formais (ABNT)
        research_questions: Perguntas norteadoras para pesquisas
        formula: Fórmula de cálculo (opcional)
    """

    def __init__(self, data: dict, level: str) -> None:
        self.id: str = data["id"]
        self.name: str = data["name"]
        # normaliza: aceita qualquer string, cai em TRANSVERSAL se desconhecido
        try:
            self.level: IndicatorLevel = IndicatorLevel(level)
        except ValueError:
            self.level = IndicatorLevel.TRANSVERSAL
        self.category: str = data.get("category", "")
        self.description: str = data.get("description", "").strip()
        self.periodicity: str = data.get("periodicity", "")
        self.available_since: Optional[int] = data.get("available_since")
        self.methodology_url: Optional[str] = data.get("methodology_url")
        self.disaggregations: list[str] = data.get("disaggregations", [])
        self.source_datasets: list[str] = data.get("source_datasets", [])
        self.citations: list[str] = data.get("citations", [])
        self.research_questions: list[str] = data.get("research_questions", [])
        self.formula: Optional[str] = data.get("formula")

    def __repr__(self) -> str:
        return f"Indicator(id={self.id!r}, level={self.level.value!r})"

    def __str__(self) -> str:
        return f"{self.name} [{self.level.value}]"

    def summary(self) -> str:
        """Retorna um resumo de uma linha."""
        since = f" (desde {self.available_since})" if self.available_since else ""
        return f"[{self.id}] {self.name}{since}"

    def has_dataset(self, dataset_id: str) -> bool:
        """Verifica se o indicador usa um dataset específico."""
        return dataset_id in self.source_datasets

    def to_dict(self) -> dict:
        """Serializa para dicionário."""
        return {
            "id": self.id,
            "name": self.name,
            "level": self.level.value,
            "category": self.category,
            "description": self.description,
            "periodicity": self.periodicity,
            "available_since": self.available_since,
            "methodology_url": self.methodology_url,
            "disaggregations": self.disaggregations,
            "source_datasets": self.source_datasets,
            "citations": self.citations,
            "research_questions": self.research_questions,
            "formula": self.formula,
        }


# ---------------------------------------------------------------------------
# Registry de indicadores
# ---------------------------------------------------------------------------

class IndicatorRegistryError(Exception):
    pass


class IndicatorRegistry:
    """
    Registry lazy de indicadores educacionais.

    Carrega os YAMLs de catalog/indicators/ sob demanda.
    Thread-safe para leitura (carregamento é idempotente).

    Exemplo:
        reg = IndicatorRegistry()
        ideb = reg.get("ideb")
        for ind in reg.by_level(IndicatorLevel.BASICA):
            print(ind.name, len(ind.research_questions), "perguntas")
    """

    def __init__(self, indicators_dir: Optional[Path] = None) -> None:
        self._dir = indicators_dir or _INDICATORS_DIR
        self._store: dict[str, Indicator] = {}
        self._loaded = False
        self._load_errors: list[tuple[Path, str]] = []

    # ------------------------------------------------------------------
    # Carregamento
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Carrega automaticamente todos os YAMLs de catalog/indicators/."""
        if self._loaded:
            return

        level_files = _discover_level_files()

        for level_key, yaml_path in level_files:
            if not yaml_path.exists():
                self._load_errors.append((yaml_path, "arquivo não encontrado"))
                continue
            try:
                data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            except yaml.YAMLError as exc:
                self._load_errors.append((yaml_path, str(exc)))
                continue

            # Usa o nível declarado no YAML, não o nome do arquivo
            declared_level = data.get("level", level_key)

            for ind_data in data.get("indicators", []):
                try:
                    ind = Indicator(ind_data, level=declared_level)
                    if ind.id in self._store:
                        self._load_errors.append(
                            (yaml_path, f"ID duplicado: {ind.id!r}")
                        )
                    else:
                        self._store[ind.id] = ind
                except (KeyError, ValueError) as exc:
                    self._load_errors.append(
                        (yaml_path, f"Erro ao carregar indicador: {exc}")
                    )

        self._loaded = True

    def reload(self) -> None:
        """Força recarregamento dos YAMLs."""
        self._store.clear()
        self._load_errors.clear()
        self._loaded = False
        self.load()

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()

    def load_errors(self) -> list[tuple[Path, str]]:
        self._ensure_loaded()
        return list(self._load_errors)

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def get(self, indicator_id: str) -> Optional[Indicator]:
        """Retorna um indicador por ID, ou None se não encontrado."""
        self._ensure_loaded()
        return self._store.get(indicator_id)

    def require(self, indicator_id: str) -> Indicator:
        """Retorna um indicador por ID; lança IndicatorRegistryError se não encontrar."""
        ind = self.get(indicator_id)
        if ind is None:
            available = sorted(self._store.keys())
            raise IndicatorRegistryError(
                f"Indicador {indicator_id!r} não encontrado. "
                f"Disponíveis: {available}"
            )
        return ind

    def all(self) -> list[Indicator]:
        """Retorna todos os indicadores ordenados por nível e nome."""
        self._ensure_loaded()
        return sorted(self._store.values(), key=lambda i: (i.level.value, i.name))

    def by_level(self, level: IndicatorLevel) -> list[Indicator]:
        """Filtra indicadores por nível de ensino."""
        self._ensure_loaded()
        return [i for i in self.all() if i.level == level]

    def by_category(self, category: str) -> list[Indicator]:
        """Filtra indicadores por categoria temática."""
        self._ensure_loaded()
        return [i for i in self.all() if i.category == category]

    def by_dataset(self, dataset_id: str) -> list[Indicator]:
        """Retorna indicadores que usam um dataset específico do catálogo."""
        self._ensure_loaded()
        return [i for i in self.all() if i.has_dataset(dataset_id)]

    def search(self, query: str) -> list[Indicator]:
        """
        Busca case-insensitive em id, name, description e tags de categorias.
        """
        self._ensure_loaded()
        q = query.lower()
        return [
            i for i in self.all()
            if q in i.id.lower()
            or q in i.name.lower()
            or q in i.description.lower()
            or q in i.category.lower()
        ]

    def categories(self) -> list[str]:
        """Retorna lista de categorias únicas presentes."""
        self._ensure_loaded()
        return sorted({i.category for i in self._store.values()})

    def questions_for_dataset(self, dataset_id: str) -> dict[str, list[str]]:
        """
        Retorna {indicator_id: [perguntas]} para todos os indicadores
        relacionados a um dataset específico.
        """
        result: dict[str, list[str]] = {}
        for ind in self.by_dataset(dataset_id):
            if ind.research_questions:
                result[ind.id] = ind.research_questions
        return result

    def all_research_questions(
        self,
        level: Optional[IndicatorLevel] = None,
        category: Optional[str] = None,
    ) -> list[dict]:
        """
        Retorna todas as perguntas norteadoras como lista de dicts:
        [{"indicator_id": ..., "indicator_name": ..., "question": ...}]

        Parâmetros opcionais para filtrar por nível e categoria.
        """
        self._ensure_loaded()
        indicators = self.all()
        if level:
            indicators = [i for i in indicators if i.level == level]
        if category:
            indicators = [i for i in indicators if i.category == category]

        questions = []
        for ind in indicators:
            for q in ind.research_questions:
                questions.append({
                    "indicator_id": ind.id,
                    "indicator_name": ind.name,
                    "level": ind.level.value,
                    "category": ind.category,
                    "question": q,
                })
        return questions

    def validate(self) -> list[str]:
        """Valida integridade do registry; retorna lista de erros."""
        self._ensure_loaded()
        errors = list(self._load_errors)

        for ind in self._store.values():
            if not ind.id:
                errors.append(f"Indicador sem ID em {ind.name!r}")
            if not ind.citations:
                errors.append(f"[{ind.id}] sem citações bibliográficas")
            if not ind.research_questions:
                errors.append(f"[{ind.id}] sem perguntas norteadoras")
            if not ind.source_datasets:
                errors.append(f"[{ind.id}] sem datasets associados")

        return errors

    def __len__(self) -> int:
        self._ensure_loaded()
        return len(self._store)

    def __contains__(self, indicator_id: str) -> bool:
        self._ensure_loaded()
        return indicator_id in self._store

    def __iter__(self):
        self._ensure_loaded()
        return iter(self._store.values())


# ---------------------------------------------------------------------------
# Singleton global
# ---------------------------------------------------------------------------

indicator_registry = IndicatorRegistry()
