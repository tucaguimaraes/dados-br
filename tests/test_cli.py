"""
Testes para a CLI (dadosbr.cli) via Typer TestClient.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from dadosbr.cli import app

runner = CliRunner()


class TestCliVersion:
    def test_version_command(self):
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        assert "dados-br" in result.output

    def test_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "download" in result.output.lower()
        assert "list" in result.output.lower()


class TestCliList:
    def test_list_all(self):
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        # Deve listar pelo menos os datasets do catálogo real
        assert "enem" in result.output.lower() or "censo" in result.output.lower()

    def test_list_by_category(self):
        result = runner.invoke(app, ["list", "--category", "educacao"])
        assert result.exit_code == 0

    def test_list_by_nonexistent_category(self):
        result = runner.invoke(app, ["list", "--category", "categoria_inexistente_xyz"])
        assert result.exit_code == 0
        assert "nenhum" in result.output.lower()

    def test_list_search(self):
        result = runner.invoke(app, ["list", "--search", "enem"])
        assert result.exit_code == 0
        assert "enem" in result.output.lower()

    def test_list_search_no_results(self):
        result = runner.invoke(app, ["list", "--search", "xyznotfound999"])
        assert result.exit_code == 0
        assert "nenhum" in result.output.lower()


class TestCliInfo:
    def test_info_existing_dataset(self):
        result = runner.invoke(app, ["info", "enem"])
        assert result.exit_code == 0
        assert "ENEM" in result.output or "enem" in result.output.lower()

    def test_info_nonexistent_dataset(self):
        result = runner.invoke(app, ["info", "dataset_que_nao_existe_xyz"])
        assert result.exit_code != 0

    def test_info_censo_escolar(self):
        result = runner.invoke(app, ["info", "censo_escolar"])
        assert result.exit_code == 0
        assert "censo" in result.output.lower()

    def test_info_static_dataset(self):
        result = runner.invoke(app, ["info", "goias_educacao"])
        assert result.exit_code == 0


class TestCliCatalog:
    def test_catalog_validate_ok(self):
        result = runner.invoke(app, ["catalog", "validate"])
        assert result.exit_code == 0
        assert "válido" in result.output.lower() or "válido" in result.output

    def test_catalog_stats(self):
        result = runner.invoke(app, ["catalog", "stats"])
        assert result.exit_code == 0
        assert "dataset" in result.output.lower()
        assert "categoria" in result.output.lower()

    def test_catalog_help(self):
        result = runner.invoke(app, ["catalog", "--help"])
        assert result.exit_code == 0
        assert "validate" in result.output
        assert "stats" in result.output


class TestCliDownload:
    def test_download_dry_run(self, tmp_path: Path):
        result = runner.invoke(
            app,
            ["download", "enem", "--years", "2023", "--dry-run", "--output-dir", str(tmp_path)],
            input="y\n",  # Confirma o download
        )
        # dry-run deve retornar 0 (sucesso)
        assert result.exit_code == 0
        assert "dry-run" in result.output.lower() or "simula" in result.output.lower()

    def test_download_nonexistent_dataset(self, tmp_path: Path):
        result = runner.invoke(
            app,
            ["download", "dataset_nao_existe_xyz", "--output-dir", str(tmp_path)],
        )
        assert result.exit_code != 0

    def test_download_no_confirm(self, tmp_path: Path):
        # Responde "n" à confirmação — deve sair sem baixar
        result = runner.invoke(
            app,
            ["download", "ibge_malha_go", "--output-dir", str(tmp_path)],
            input="n\n",
        )
        assert result.exit_code == 0

    def test_download_static_dry_run(self, tmp_path: Path):
        result = runner.invoke(
            app,
            ["download", "goias_educacao", "--dry-run", "--output-dir", str(tmp_path)],
            input="y\n",
        )
        assert result.exit_code == 0


class TestCliCheck:
    def test_check_missing_dir(self, tmp_path: Path):
        result = runner.invoke(
            app,
            ["check", "--dir", str(tmp_path / "nao_existe")],
        )
        assert result.exit_code != 0

    def test_check_empty_dir(self, tmp_path: Path):
        empty = tmp_path / "dados"
        empty.mkdir()
        result = runner.invoke(app, ["check", "--dir", str(empty)])
        # Deve sair com 0 (nenhum arquivo, nenhuma checagem)
        assert result.exit_code == 0

    def test_check_nonexistent_dataset(self, tmp_path: Path):
        result = runner.invoke(
            app,
            ["check", "dataset_nao_existe", "--dir", str(tmp_path)],
        )
        assert result.exit_code != 0


class TestCliUtils:
    def test_utils_parse_years(self):
        from dadosbr.utils import parse_years_expr
        available = list(range(2015, 2025))
        assert parse_years_expr("all", available) == available
        assert parse_years_expr("2020", available) == [2020]
        assert parse_years_expr("2018-2021", available) == [2018, 2019, 2020, 2021]
        assert parse_years_expr("2015,2020,2023", available) == [2015, 2020, 2023]
        assert parse_years_expr("2010", available) == []  # fora do disponível

    def test_utils_human_size(self):
        from dadosbr.utils import human_size
        assert "B" in human_size(500)
        assert "KB" in human_size(2048)
        assert "MB" in human_size(2 * 1024 * 1024)
        assert "GB" in human_size(2 * 1024 ** 3)

    def test_utils_human_mb(self):
        from dadosbr.utils import human_mb
        result = human_mb(1024.0)
        assert "GB" in result

    def test_utils_filename_from_url(self):
        from dadosbr.utils import filename_from_url
        assert filename_from_url("https://example.com/path/file.zip") == "file.zip"
        assert filename_from_url("https://example.com/path/") == "path"

    def test_utils_clean_url(self):
        from dadosbr.utils import clean_url
        assert clean_url("https://https://example.com") == "https://example.com"
        assert clean_url("  https://example.com  ") == "https://example.com"

    def test_utils_validate_years_expr(self):
        from dadosbr.utils import validate_years_expr
        assert validate_years_expr("all") is True
        assert validate_years_expr("2020") is True
        assert validate_years_expr("2020-2023") is True
        assert validate_years_expr("2020,2022") is True
        assert validate_years_expr("abc") is False
