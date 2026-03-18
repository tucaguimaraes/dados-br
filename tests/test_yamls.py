"""
Testes de validação estrutural dos YAMLs do catálogo real.

Verifica que todos os arquivos YAML são:
  - Parsáveis pelo PyYAML
  - Validáveis pelo modelo Dataset do Pydantic
  - Sem IDs duplicados
  - Com campos obrigatórios preenchidos
  - Com URLs bem formadas
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from dadosbr.models import Dataset
from dadosbr.registry import CATALOG_DIR, Registry

# Coletar apenas YAMLs de datasets (excluir subpasta indicators/)
_yaml_files = sorted(
    p for p in CATALOG_DIR.rglob("*.yaml")
    if "indicators" not in p.parts
)


@pytest.mark.parametrize("yaml_path", _yaml_files, ids=[f.stem for f in _yaml_files])
class TestEachYamlFile:
    def test_yaml_parseable(self, yaml_path: Path):
        """Arquivo deve ser YAML válido."""
        with yaml_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data is not None, f"{yaml_path.name} está vazio"
        assert isinstance(data, dict), f"{yaml_path.name} deve ser um mapeamento YAML"

    def test_yaml_has_required_fields(self, yaml_path: Path):
        """Campos obrigatórios devem estar presentes."""
        with yaml_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        for field in ("id", "name", "source", "category", "description", "dest_folder"):
            assert field in data, f"{yaml_path.name}: campo '{field}' ausente"

    def test_yaml_validates_as_dataset(self, yaml_path: Path):
        """YAML deve ser validável como Dataset Pydantic sem erros."""
        with yaml_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        try:
            ds = Dataset.model_validate(data)
        except Exception as exc:
            pytest.fail(f"{yaml_path.name} falhou na validação Pydantic: {exc}")

    def test_id_is_snake_case(self, yaml_path: Path):
        """ID deve seguir padrão snake_case."""
        import re
        with yaml_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        ds_id = data.get("id", "")
        assert re.match(r"^[a-z][a-z0-9_]*$", ds_id), (
            f"{yaml_path.name}: ID '{ds_id}' não é snake_case válido"
        )

    def test_dest_folder_not_empty(self, yaml_path: Path):
        """dest_folder deve ser não vazio."""
        with yaml_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data.get("dest_folder", "").strip(), (
            f"{yaml_path.name}: dest_folder está vazio"
        )

    def test_description_min_length(self, yaml_path: Path):
        """Descrição deve ter pelo menos 10 caracteres."""
        with yaml_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        desc = data.get("description", "")
        assert len(str(desc).strip()) >= 10, (
            f"{yaml_path.name}: description muito curta ({len(str(desc))} chars)"
        )

    def test_urls_are_valid(self, yaml_path: Path):
        """URLs declaradas devem ter protocolo válido."""
        with yaml_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)

        urls_to_check = []

        # url_pattern
        if data.get("url_pattern"):
            # Substitui placeholder por ano fictício para validar estrutura
            url = data["url_pattern"].replace("{year}", "2020").replace("{year_2d}", "20")
            urls_to_check.append(url)

        # files
        for f_entry in data.get("files", []):
            if isinstance(f_entry, dict) and "url" in f_entry:
                urls_to_check.append(f_entry["url"])

        # year_exceptions
        for val in data.get("year_exceptions", {}).values():
            if isinstance(val, str):
                urls_to_check.append(val)
            elif isinstance(val, list):
                urls_to_check.extend(u for u in val if isinstance(u, str))

        for url in urls_to_check:
            assert url.startswith(("http://", "https://", "ftp://")), (
                f"{yaml_path.name}: URL inválida: {url!r}"
            )

    def test_category_is_string(self, yaml_path: Path):
        """Category deve ser string não vazia."""
        with yaml_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        cat = data.get("category", "")
        assert isinstance(cat, str) and len(cat) > 0, (
            f"{yaml_path.name}: category inválida"
        )

    def test_url_type_is_valid(self, yaml_path: Path):
        """url_type deve ser um dos valores permitidos."""
        valid = {"pattern", "static_list", "dynamic", "ftp"}
        with yaml_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f)
        url_type = data.get("url_type", "pattern")
        assert url_type in valid, (
            f"{yaml_path.name}: url_type inválido: {url_type!r}. Valores aceitos: {valid}"
        )


class TestCatalogGlobal:
    def test_no_duplicate_ids_in_catalog(self):
        """IDs devem ser únicos em todo o catálogo."""
        ids: list[str] = []
        for yaml_path in _yaml_files:
            with yaml_path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            if ds_id := data.get("id"):
                ids.append(ds_id)
        assert len(ids) == len(set(ids)), (
            f"IDs duplicados encontrados: {[x for x in ids if ids.count(x) > 1]}"
        )

    def test_catalog_has_multiple_categories(self):
        """Catálogo deve cobrir pelo menos 3 categorias diferentes."""
        categories = set()
        for yaml_path in _yaml_files:
            with yaml_path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            if cat := data.get("category"):
                categories.add(cat)
        assert len(categories) >= 3, f"Apenas {len(categories)} categoria(s): {categories}"

    def test_catalog_has_multiple_sources(self):
        """Catálogo deve cobrir pelo menos 3 fontes diferentes."""
        sources = set()
        for yaml_path in _yaml_files:
            with yaml_path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            if src := data.get("source"):
                sources.add(src)
        assert len(sources) >= 3

    def test_registry_loads_all_yamls(self):
        """O Registry deve carregar todos os YAMLs sem erros críticos."""
        reg = Registry(catalog_dir=CATALOG_DIR)
        reg.load()
        errors = reg.load_errors()
        assert errors == [], f"Erros de carregamento: {errors}"

    def test_registry_validate_no_issues(self):
        """validate_all() não deve retornar problemas para o catálogo real."""
        reg = Registry(catalog_dir=CATALOG_DIR)
        reg.load()
        issues = reg.validate_all()
        assert issues == {}, f"Problemas de validação: {issues}"
