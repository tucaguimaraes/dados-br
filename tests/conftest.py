"""
Fixtures compartilhadas entre os módulos de teste.
"""

from __future__ import annotations

import tempfile
import zipfile
from pathlib import Path

import pytest
import yaml

from dadosbr.models import CheckConfig, Dataset, DatasetFile, YearRange
from dadosbr.registry import Registry


# ---------------------------------------------------------------------------
# Fixtures de datasets de exemplo
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_pattern_dataset() -> Dataset:
    """Dataset padrão baseado em URL pattern."""
    return Dataset(
        id="test_enem",
        name="ENEM Teste",
        source="INEP/MEC",
        category="educacao",
        description="Dataset de teste baseado no ENEM",
        tags=["enem", "teste"],
        url_type="pattern",
        file_format="zip",
        years=YearRange(start=2020, end=2023),
        url_pattern="https://example.com/enem_{year}.zip",
        year_exceptions={"2022": None},  # ano desabilitado
        est_size_mb_per_year=100.0,
        est_extracted_mb_per_year=400.0,
        dest_folder="inep_mec/test_enem",
        checks=[
            CheckConfig(type="file_exists"),
            CheckConfig(type="zip_valid"),
            CheckConfig(type="min_size_mb", value=10),
        ],
    )


@pytest.fixture
def sample_static_dataset() -> Dataset:
    """Dataset com lista estática de arquivos."""
    return Dataset(
        id="test_goias",
        name="Goiás Teste",
        source="SEDUC-GO",
        category="educacao",
        description="Dataset de teste com arquivos estáticos CSV",
        url_type="static_list",
        file_format="csv",
        files=[
            DatasetFile(
                url="https://example.com/dados_2025.csv",
                filename="dados_2025.csv",
                description="Dados 2025",
                est_size_mb=2.0,
            ),
            DatasetFile(
                url="https://example.com/dados_2024.csv",
                filename="dados_2024.csv",
                est_size_mb=1.5,
            ),
        ],
        est_size_mb_total=3.5,
        est_extracted_mb_total=3.5,
        dest_folder="goias/test",
        checks=[
            CheckConfig(type="file_exists"),
            CheckConfig(type="csv_readable"),
        ],
    )


# ---------------------------------------------------------------------------
# Fixtures de registry
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_catalog_dir(tmp_path: Path) -> Path:
    """Cria um diretório de catálogo temporário com YAMLs de teste."""
    catalog_dir = tmp_path / "catalog"
    catalog_dir.mkdir()

    # Dataset pattern
    (catalog_dir / "test_pattern.yaml").write_text(
        yaml.dump({
            "id": "test_pattern",
            "name": "Test Pattern Dataset",
            "source": "Test Source",
            "category": "educacao",
            "description": "Um dataset de teste com URL pattern",
            "url_type": "pattern",
            "file_format": "zip",
            "years": {"start": 2020, "end": 2022},
            "url_pattern": "https://example.com/data_{year}.zip",
            "dest_folder": "test/pattern",
        }),
        encoding="utf-8",
    )

    # Dataset static_list
    (catalog_dir / "test_static.yaml").write_text(
        yaml.dump({
            "id": "test_static",
            "name": "Test Static Dataset",
            "source": "Test Source",
            "category": "saude",
            "description": "Um dataset de teste com lista estática",
            "url_type": "static_list",
            "file_format": "csv",
            "files": [
                {
                    "url": "https://example.com/file1.csv",
                    "filename": "file1.csv",
                    "est_size_mb": 1.0,
                }
            ],
            "dest_folder": "test/static",
        }),
        encoding="utf-8",
    )

    return catalog_dir


@pytest.fixture
def real_catalog_registry() -> Registry:
    """Registry apontando para o catálogo real do projeto."""
    from dadosbr.registry import CATALOG_DIR
    reg = Registry(catalog_dir=CATALOG_DIR)
    reg.load()
    return reg


@pytest.fixture
def test_registry(temp_catalog_dir: Path) -> Registry:
    """Registry apontando para o catálogo temporário de teste."""
    reg = Registry(catalog_dir=temp_catalog_dir)
    reg.load()
    return reg


# ---------------------------------------------------------------------------
# Fixtures de arquivos
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_zip_file(tmp_path: Path) -> Path:
    """Cria um arquivo ZIP válido para testes."""
    zip_path = tmp_path / "test_valid.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("dados.csv", "id,nome,valor\n1,teste,100\n2,outro,200\n")
        zf.writestr("README.txt", "Arquivo de teste dados-br")
    return zip_path


@pytest.fixture
def invalid_zip_file(tmp_path: Path) -> Path:
    """Cria um arquivo ZIP inválido/corrompido."""
    zip_path = tmp_path / "test_invalid.zip"
    zip_path.write_bytes(b"PK\x03\x04" + b"\x00" * 100)  # magic bytes mas dados inválidos
    return zip_path


@pytest.fixture
def valid_csv_file(tmp_path: Path) -> Path:
    """Cria um arquivo CSV válido."""
    csv_path = tmp_path / "test.csv"
    csv_path.write_text(
        "ano,municipio,valor\n2020,Goiania,100\n2020,Anapolis,200\n2021,Goiania,110\n",
        encoding="utf-8",
    )
    return csv_path


@pytest.fixture
def sample_data_dir(tmp_path: Path, valid_zip_file: Path, valid_csv_file: Path) -> Path:
    """Cria estrutura de diretório de dados para testes de checagem."""
    data_dir = tmp_path / "dados"
    (data_dir / "inep_mec" / "enem").mkdir(parents=True)
    (data_dir / "goias" / "educacao").mkdir(parents=True)

    # Copia fixtures
    import shutil
    shutil.copy(valid_zip_file, data_dir / "inep_mec" / "enem" / "enem_2020.zip")
    shutil.copy(valid_csv_file, data_dir / "goias" / "educacao" / "dados_2025.csv")

    return data_dir
