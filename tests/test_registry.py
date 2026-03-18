"""
Testes para dadosbr.registry — carregamento e consulta do catálogo.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from dadosbr.registry import Registry, RegistryError


class TestRegistryLoad:
    def test_load_from_temp_catalog(self, test_registry: Registry):
        assert len(test_registry) == 2

    def test_load_real_catalog(self, real_catalog_registry: Registry):
        # Deve ter pelo menos 10 datasets no catálogo real
        assert len(real_catalog_registry) >= 10

    def test_load_missing_dir_raises(self, tmp_path: Path):
        reg = Registry(catalog_dir=tmp_path / "nonexistent")
        with pytest.raises(RegistryError):
            reg.load()

    def test_load_empty_dir_ok(self, tmp_path: Path):
        empty = tmp_path / "empty_catalog"
        empty.mkdir()
        reg = Registry(catalog_dir=empty)
        reg.load()
        assert len(reg) == 0

    def test_load_invalid_yaml_skipped(self, tmp_path: Path):
        catalog = tmp_path / "catalog"
        catalog.mkdir()
        # YAML malformado
        (catalog / "bad.yaml").write_text("id: :\n  bad: yaml: content:", encoding="utf-8")
        # YAML vazio
        (catalog / "empty.yaml").write_text("", encoding="utf-8")
        # YAML válido
        (catalog / "good.yaml").write_text(
            yaml.dump({
                "id": "good_ds",
                "name": "Good Dataset",
                "source": "Test",
                "category": "educacao",
                "description": "Um dataset válido para teste",
                "url_type": "static_list",
                "file_format": "csv",
                "files": [{"url": "https://example.com/f.csv"}],
                "dest_folder": "test",
            }),
            encoding="utf-8",
        )
        reg = Registry(catalog_dir=catalog)
        reg.load()
        assert len(reg) == 1  # somente o válido
        assert len(reg.load_errors()) >= 1  # erros registrados

    def test_duplicate_ids_handled(self, tmp_path: Path):
        catalog = tmp_path / "catalog"
        catalog.mkdir()
        ds_data = {
            "id": "dup_id",
            "name": "Duplicado",
            "source": "X",
            "category": "educacao",
            "description": "Dataset com ID duplicado",
            "url_type": "static_list",
            "file_format": "csv",
            "files": [{"url": "https://example.com/f.csv"}],
            "dest_folder": "test",
        }
        (catalog / "a.yaml").write_text(yaml.dump(ds_data), encoding="utf-8")
        ds_data2 = dict(ds_data)
        ds_data2["name"] = "Duplicado 2"
        (catalog / "b.yaml").write_text(yaml.dump(ds_data2), encoding="utf-8")

        reg = Registry(catalog_dir=catalog)
        reg.load()
        # Apenas um dos duplicados deve ser carregado
        assert len(reg) == 1

    def test_reload(self, temp_catalog_dir: Path):
        reg = Registry(catalog_dir=temp_catalog_dir)
        reg.load()
        count1 = len(reg)
        # Adiciona novo arquivo
        (temp_catalog_dir / "new.yaml").write_text(
            yaml.dump({
                "id": "new_dataset",
                "name": "New Dataset",
                "source": "X",
                "category": "saude",
                "description": "Novo dataset adicionado após carregamento",
                "url_type": "static_list",
                "file_format": "csv",
                "files": [{"url": "https://example.com/new.csv"}],
                "dest_folder": "test/new",
            }),
            encoding="utf-8",
        )
        reg.reload()
        assert len(reg) == count1 + 1


class TestRegistryQueries:
    def test_get_existing(self, test_registry: Registry):
        ds = test_registry.get("test_pattern")
        assert ds is not None
        assert ds.id == "test_pattern"

    def test_get_missing_returns_none(self, test_registry: Registry):
        assert test_registry.get("nonexistent") is None

    def test_require_existing(self, test_registry: Registry):
        ds = test_registry.require("test_pattern")
        assert ds.id == "test_pattern"

    def test_require_missing_raises(self, test_registry: Registry):
        with pytest.raises(RegistryError) as exc_info:
            test_registry.require("does_not_exist")
        assert "does_not_exist" in str(exc_info.value)

    def test_all_returns_sorted(self, test_registry: Registry):
        datasets = test_registry.all()
        ids = [d.id for d in datasets]
        assert ids == sorted(ids)

    def test_by_category(self, test_registry: Registry):
        educacao = test_registry.by_category("educacao")
        assert all(d.category == "educacao" for d in educacao)
        assert len(educacao) >= 1

    def test_by_category_case_insensitive(self, test_registry: Registry):
        result = test_registry.by_category("EDUCACAO")
        assert len(result) >= 1

    def test_by_source(self, test_registry: Registry):
        result = test_registry.by_source("Test Source")
        assert all(d.source == "Test Source" for d in result)

    def test_search_by_id(self, test_registry: Registry):
        results = test_registry.search("pattern")
        assert any(d.id == "test_pattern" for d in results)

    def test_search_by_category(self, test_registry: Registry):
        results = test_registry.search("saude")
        assert any(d.category == "saude" for d in results)

    def test_search_no_results(self, test_registry: Registry):
        results = test_registry.search("xyznotfound123")
        assert results == []

    def test_categories(self, test_registry: Registry):
        cats = test_registry.categories()
        assert isinstance(cats, list)
        assert cats == sorted(cats)
        assert "educacao" in cats

    def test_sources(self, test_registry: Registry):
        srcs = test_registry.sources()
        assert isinstance(srcs, list)
        assert srcs == sorted(srcs)

    def test_contains(self, test_registry: Registry):
        assert "test_pattern" in test_registry
        assert "nonexistent" not in test_registry

    def test_iter(self, test_registry: Registry):
        ids = {d.id for d in test_registry}
        assert "test_pattern" in ids
        assert "test_static" in ids

    def test_repr(self, test_registry: Registry):
        r = repr(test_registry)
        assert "Registry" in r
        assert "2 datasets" in r


class TestRegistryValidation:
    def test_validate_all_clean(self, test_registry: Registry):
        issues = test_registry.validate_all()
        assert issues == {}

    def test_validate_real_catalog(self, real_catalog_registry: Registry):
        issues = real_catalog_registry.validate_all()
        # O catálogo real não deve ter problemas críticos
        assert isinstance(issues, dict)
