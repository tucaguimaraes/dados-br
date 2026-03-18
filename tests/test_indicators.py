"""
Testes para dadosbr.indicators — IndicatorRegistry, Indicator e YAML de indicadores.

Cobre:
  - Carregamento e contagem dos indicadores
  - Acesso por id, nível, categoria e dataset
  - Presença obrigatória de perguntas norteadoras e citações
  - Cobertura: todos os datasets do catálogo têm indicador
  - Validação estrutural de cada YAML de indicadores
  - Busca textual
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from dadosbr.indicators import (
    Indicator,
    IndicatorLevel,
    IndicatorRegistry,
    indicator_registry,
)
from dadosbr.registry import CATALOG_DIR, registry as dataset_registry

# Diretório dos YAMLs de indicadores
INDICATORS_DIR = CATALOG_DIR / "indicators"
_indicator_yamls = sorted(INDICATORS_DIR.glob("*.yaml"))


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def loaded_registry() -> IndicatorRegistry:
    """Registry carregado uma única vez por módulo."""
    reg = IndicatorRegistry()
    reg.load()
    return reg


@pytest.fixture(scope="module")
def all_indicators(loaded_registry: IndicatorRegistry) -> list[Indicator]:
    return loaded_registry.all()


# ─────────────────────────────────────────────────────────────────────────────
# 1. Carregamento
# ─────────────────────────────────────────────────────────────────────────────

class TestRegistryLoad:
    def test_loads_without_error(self, loaded_registry: IndicatorRegistry):
        assert loaded_registry is not None

    def test_minimum_indicator_count(self, loaded_registry: IndicatorRegistry):
        """Catálogo deve ter pelo menos 38 indicadores."""
        assert len(loaded_registry) >= 38, (
            f"Apenas {len(loaded_registry)} indicadores carregados (esperado ≥ 38)"
        )

    def test_global_singleton_loads(self):
        """A instância global indicator_registry deve carregar corretamente."""
        indicator_registry.load()
        assert len(indicator_registry) >= 38

    def test_reload_preserves_count(self, loaded_registry: IndicatorRegistry):
        """Recarregar não deve alterar a contagem."""
        count_before = len(loaded_registry)
        loaded_registry.reload()
        assert len(loaded_registry) == count_before

    def test_validates_without_errors(self, loaded_registry: IndicatorRegistry):
        errors = loaded_registry.validate()
        assert errors == [], f"Erros de validação: {errors}"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Acesso por ID
# ─────────────────────────────────────────────────────────────────────────────

class TestGetById:
    @pytest.mark.parametrize("ind_id", [
        "ideb",
        "distorcao_idade_serie",
        "taxa_analfabetismo",
        "mortalidade_infantil",
        "gasto_aluno_municipio",
        "transparencia_orcamentaria",
        "fluxo_educacao_superior",
    ])
    def test_known_indicators_exist(self, loaded_registry: IndicatorRegistry, ind_id: str):
        ind = loaded_registry.get(ind_id)
        assert ind is not None, f"Indicador '{ind_id}' não encontrado"
        assert ind.id == ind_id

    def test_get_unknown_returns_none(self, loaded_registry: IndicatorRegistry):
        assert loaded_registry.get("indicador_que_nao_existe_xyz") is None

    def test_require_unknown_raises(self, loaded_registry: IndicatorRegistry):
        with pytest.raises(KeyError):
            loaded_registry.require("indicador_que_nao_existe_xyz")

    def test_require_known_returns_indicator(self, loaded_registry: IndicatorRegistry):
        ind = loaded_registry.require("ideb")
        assert ind.id == "ideb"
        assert isinstance(ind, Indicator)


# ─────────────────────────────────────────────────────────────────────────────
# 3. Filtros por nível
# ─────────────────────────────────────────────────────────────────────────────

class TestByLevel:
    def test_basica_level_exists(self, loaded_registry: IndicatorRegistry):
        basica = loaded_registry.by_level(IndicatorLevel.BASICA)
        assert len(basica) >= 15, f"Educação básica: {len(basica)} indicadores (esperado ≥ 15)"

    def test_superior_level_exists(self, loaded_registry: IndicatorRegistry):
        superior = loaded_registry.by_level(IndicatorLevel.SUPERIOR)
        assert len(superior) >= 4

    def test_transversal_level_exists(self, loaded_registry: IndicatorRegistry):
        transversal = loaded_registry.by_level(IndicatorLevel.TRANSVERSAL)
        assert len(transversal) >= 10

    def test_all_levels_sum_to_total(self, loaded_registry: IndicatorRegistry):
        basica = loaded_registry.by_level(IndicatorLevel.BASICA)
        superior = loaded_registry.by_level(IndicatorLevel.SUPERIOR)
        transversal = loaded_registry.by_level(IndicatorLevel.TRANSVERSAL)
        total = len(basica) + len(superior) + len(transversal)
        assert total == len(loaded_registry), (
            f"Soma dos níveis ({total}) ≠ total ({len(loaded_registry)})"
        )

    def test_ideb_is_basica(self, loaded_registry: IndicatorRegistry):
        ind = loaded_registry.require("ideb")
        assert ind.level == IndicatorLevel.BASICA

    def test_fluxo_superior_is_superior(self, loaded_registry: IndicatorRegistry):
        ind = loaded_registry.require("fluxo_educacao_superior")
        assert ind.level == IndicatorLevel.SUPERIOR

    def test_mortalidade_infantil_is_transversal(self, loaded_registry: IndicatorRegistry):
        ind = loaded_registry.require("mortalidade_infantil")
        assert ind.level == IndicatorLevel.TRANSVERSAL


# ─────────────────────────────────────────────────────────────────────────────
# 4. Perguntas norteadoras
# ─────────────────────────────────────────────────────────────────────────────

class TestResearchQuestions:
    def test_total_questions_minimum(self, loaded_registry: IndicatorRegistry):
        questions = loaded_registry.all_research_questions()
        assert len(questions) >= 155, (
            f"Apenas {len(questions)} perguntas (esperado ≥ 155)"
        )

    def test_ideb_has_questions(self, loaded_registry: IndicatorRegistry):
        ind = loaded_registry.require("ideb")
        assert len(ind.research_questions) >= 3, (
            f"IDEB tem apenas {len(ind.research_questions)} perguntas"
        )

    def test_all_indicators_have_at_least_one_question(self, all_indicators: list[Indicator]):
        without = [ind.id for ind in all_indicators if not ind.research_questions]
        assert without == [], f"Indicadores sem perguntas norteadoras: {without}"

    def test_questions_for_dataset_censo_escolar(self, loaded_registry: IndicatorRegistry):
        questions = loaded_registry.questions_for_dataset("censo_escolar")
        assert len(questions) >= 5, (
            f"Censo Escolar tem apenas {len(questions)} perguntas"
        )

    def test_questions_for_unknown_dataset(self, loaded_registry: IndicatorRegistry):
        questions = loaded_registry.questions_for_dataset("dataset_xyz_inexistente")
        assert questions == []

    def test_questions_are_strings(self, all_indicators: list[Indicator]):
        for ind in all_indicators:
            for q in ind.research_questions:
                assert isinstance(q, str) and len(q.strip()) > 10, (
                    f"Pergunta inválida em '{ind.id}': {q!r}"
                )
            break  # basta checar o primeiro para não tornar lento


# ─────────────────────────────────────────────────────────────────────────────
# 5. Citações bibliográficas (ABNT)
# ─────────────────────────────────────────────────────────────────────────────

class TestCitations:
    def test_ideb_has_citations(self, loaded_registry: IndicatorRegistry):
        ind = loaded_registry.require("ideb")
        assert len(ind.citations) >= 1, "IDEB deve ter pelo menos 1 citação"

    def test_total_citations_across_all(self, all_indicators: list[Indicator]):
        total = sum(len(ind.citations) for ind in all_indicators)
        assert total >= 100, f"Apenas {total} citações no total (esperado ≥ 100)"

    def test_citations_are_strings(self, all_indicators: list[Indicator]):
        for ind in all_indicators[:5]:  # amostra
            for cit in ind.citations:
                assert isinstance(cit, str) and len(cit.strip()) > 10, (
                    f"Citação inválida em '{ind.id}': {cit!r}"
                )


# ─────────────────────────────────────────────────────────────────────────────
# 6. Cobertura datasets × indicadores
# ─────────────────────────────────────────────────────────────────────────────

class TestDatasetCoverage:
    def test_all_datasets_have_indicator(self, loaded_registry: IndicatorRegistry):
        """100% dos datasets do catálogo devem ter ao menos um indicador."""
        dataset_registry.load()
        todos = {d.id for d in dataset_registry.all()}
        referenciados = set()
        for ind in loaded_registry.all():
            referenciados.update(ind.source_datasets)
        sem_indicador = todos - referenciados
        assert sem_indicador == set(), (
            f"Datasets sem indicador associado: {sorted(sem_indicador)}"
        )

    def test_indicator_references_valid_datasets(self, loaded_registry: IndicatorRegistry):
        """Indicadores não devem referenciar datasets inexistentes no catálogo."""
        dataset_registry.load()
        ids_validos = {d.id for d in dataset_registry.all()}
        invalidos = []
        for ind in loaded_registry.all():
            for ds_id in ind.source_datasets:
                if ds_id not in ids_validos:
                    invalidos.append((ind.id, ds_id))
        assert invalidos == [], f"Referências a datasets inexistentes: {invalidos}"

    def test_for_dataset_enem(self, loaded_registry: IndicatorRegistry):
        resultado = loaded_registry.by_dataset("enem")
        assert len(resultado) >= 1

    def test_for_dataset_censo_escolar(self, loaded_registry: IndicatorRegistry):
        resultado = loaded_registry.by_dataset("censo_escolar")
        assert len(resultado) >= 3


# ─────────────────────────────────────────────────────────────────────────────
# 7. Busca textual
# ─────────────────────────────────────────────────────────────────────────────

class TestSearch:
    def test_search_ideb(self, loaded_registry: IndicatorRegistry):
        results = loaded_registry.search("ideb")
        assert any(ind.id == "ideb" for ind in results)

    def test_search_case_insensitive(self, loaded_registry: IndicatorRegistry):
        results = loaded_registry.search("MORTALIDADE")
        assert len(results) >= 1

    def test_search_no_match(self, loaded_registry: IndicatorRegistry):
        results = loaded_registry.search("xyztermoquenonexiste999")
        assert results == []

    def test_search_partial_term(self, loaded_registry: IndicatorRegistry):
        results = loaded_registry.search("analfab")
        assert len(results) >= 1

    def test_search_by_category(self, loaded_registry: IndicatorRegistry):
        results = loaded_registry.by_category("saude")
        assert len(results) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# 8. Validação estrutural dos YAMLs de indicadores
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("yaml_path", _indicator_yamls, ids=[f.stem for f in _indicator_yamls])
class TestIndicatorYamlStructure:
    def test_yaml_parseable(self, yaml_path: Path):
        with yaml_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict), f"{yaml_path.name} deve ser um mapeamento YAML"

    def test_has_level_field(self, yaml_path: Path):
        with yaml_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "level" in data, f"{yaml_path.name}: campo 'level' ausente"
        assert data["level"] in ("basica", "superior", "transversal"), (
            f"{yaml_path.name}: level inválido: {data['level']!r}"
        )

    def test_has_indicators_list(self, yaml_path: Path):
        with yaml_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "indicators" in data, f"{yaml_path.name}: campo 'indicators' ausente"
        assert isinstance(data["indicators"], list), f"{yaml_path.name}: 'indicators' deve ser lista"
        assert len(data["indicators"]) >= 1, f"{yaml_path.name}: lista de indicadores vazia"

    def test_each_indicator_has_required_fields(self, yaml_path: Path):
        with yaml_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        required = ("id", "name", "description", "source_datasets",
                    "research_questions", "citations")
        for ind in data.get("indicators", []):
            for field in required:
                assert field in ind, (
                    f"{yaml_path.name} → indicador '{ind.get('id', '?')}': "
                    f"campo '{field}' ausente"
                )

    def test_each_indicator_has_research_questions(self, yaml_path: Path):
        with yaml_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for ind in data.get("indicators", []):
            questions = ind.get("research_questions", [])
            assert len(questions) >= 1, (
                f"{yaml_path.name} → '{ind.get('id', '?')}': sem perguntas norteadoras"
            )

    def test_each_indicator_has_source_datasets(self, yaml_path: Path):
        with yaml_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for ind in data.get("indicators", []):
            ds = ind.get("source_datasets", [])
            assert len(ds) >= 1, (
                f"{yaml_path.name} → '{ind.get('id', '?')}': sem source_datasets"
            )

    def test_indicator_ids_are_snake_case(self, yaml_path: Path):
        import re
        with yaml_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for ind in data.get("indicators", []):
            ind_id = ind.get("id", "")
            assert re.match(r"^[a-z][a-z0-9_]*$", ind_id), (
                f"{yaml_path.name}: ID '{ind_id}' não é snake_case válido"
            )

    def test_no_duplicate_ids_within_file(self, yaml_path: Path):
        with yaml_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        ids = [ind.get("id") for ind in data.get("indicators", [])]
        assert len(ids) == len(set(ids)), (
            f"{yaml_path.name}: IDs duplicados: "
            f"{[x for x in ids if ids.count(x) > 1]}"
        )
