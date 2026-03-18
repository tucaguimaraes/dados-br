"""
Testes para dadosbr.models — validação dos modelos Pydantic.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from dadosbr.models import CheckConfig, Dataset, DatasetFile, YearRange


class TestYearRange:
    def test_valid_range(self):
        yr = YearRange(start=2000, end=2024)
        assert yr.start == 2000
        assert yr.end == 2024

    def test_to_list(self):
        yr = YearRange(start=2020, end=2023)
        assert yr.to_list() == [2020, 2021, 2022, 2023]

    def test_single_year(self):
        yr = YearRange(start=2023, end=2023)
        assert yr.to_list() == [2023]

    def test_invalid_order(self):
        with pytest.raises(ValidationError):
            YearRange(start=2024, end=2020)

    def test_out_of_range(self):
        with pytest.raises(ValidationError):
            YearRange(start=1800, end=2000)


class TestDatasetFile:
    def test_valid_file(self):
        f = DatasetFile(url="https://example.com/data.csv", filename="data.csv")
        assert f.filename == "data.csv"

    def test_inferred_filename_from_url(self):
        f = DatasetFile(url="https://example.com/path/arquivo.zip")
        assert f.inferred_filename() == "arquivo.zip"

    def test_inferred_filename_uses_explicit(self):
        f = DatasetFile(url="https://example.com/path/arquivo.zip", filename="custom.zip")
        assert f.inferred_filename() == "custom.zip"

    def test_invalid_url(self):
        with pytest.raises(ValidationError):
            DatasetFile(url="not-a-url")

    def test_ftp_url_valid(self):
        f = DatasetFile(url="ftp://ftp.datasus.gov.br/file.dbc")
        assert f.url.startswith("ftp://")


class TestDataset:
    def test_pattern_dataset_valid(self, sample_pattern_dataset):
        ds = sample_pattern_dataset
        assert ds.id == "test_enem"
        assert ds.url_type == "pattern"

    def test_pattern_dataset_available_years(self, sample_pattern_dataset):
        years = sample_pattern_dataset.available_years()
        assert 2020 in years
        assert 2021 in years
        assert 2022 not in years  # exceção explícita com None
        assert 2023 in years

    def test_pattern_urls_for_year(self, sample_pattern_dataset):
        urls = sample_pattern_dataset.urls_for_year(2020)
        assert len(urls) == 1
        assert "2020" in urls[0]

    def test_pattern_urls_disabled_year(self, sample_pattern_dataset):
        urls = sample_pattern_dataset.urls_for_year(2022)
        assert urls == []

    def test_pattern_urls_for_years(self, sample_pattern_dataset):
        result = sample_pattern_dataset.urls_for_years([2020, 2021, 2022])
        assert 2020 in result
        assert 2021 in result
        assert 2022 not in result  # desabilitado

    def test_static_dataset_valid(self, sample_static_dataset):
        ds = sample_static_dataset
        assert ds.url_type == "static_list"
        assert len(ds.files) == 2

    def test_estimate_download_mb_pattern(self, sample_pattern_dataset):
        # 3 anos disponíveis (2020, 2021, 2023) × 100 MB/ano = 300 MB
        est = sample_pattern_dataset.estimate_download_mb([2020, 2021, 2023])
        assert est == pytest.approx(300.0)

    def test_estimate_download_mb_static(self, sample_static_dataset):
        est = sample_static_dataset.estimate_download_mb()
        assert est == pytest.approx(3.5)

    def test_estimate_extracted_mb(self, sample_pattern_dataset):
        est = sample_pattern_dataset.estimate_extracted_mb([2020, 2021])
        assert est == pytest.approx(800.0)

    def test_invalid_id_not_snake_case(self):
        with pytest.raises(ValidationError):
            Dataset(
                id="Test Dataset",  # espaço e maiúscula
                name="X",
                source="Y",
                category="z",
                description="desc",
                url_type="pattern",
                years={"start": 2020, "end": 2020},
                url_pattern="https://ex.com/{year}.zip",
                dest_folder="x/y",
            )

    def test_pattern_requires_url_pattern(self):
        with pytest.raises(ValidationError):
            Dataset(
                id="test",
                name="Test",
                source="Source",
                category="cat",
                description="description here",
                url_type="pattern",
                years={"start": 2020, "end": 2022},
                # url_pattern missing
                dest_folder="test",
            )

    def test_static_list_requires_files(self):
        with pytest.raises(ValidationError):
            Dataset(
                id="test",
                name="Test",
                source="Source",
                category="cat",
                description="description here",
                url_type="static_list",
                file_format="csv",
                files=[],  # vazio
                dest_folder="test",
            )

    def test_year_count(self, sample_pattern_dataset):
        # 2020, 2021, 2023 (2022 desabilitado)
        assert sample_pattern_dataset.year_count() == 3

    def test_str_representation(self, sample_pattern_dataset):
        s = str(sample_pattern_dataset)
        assert "test_enem" in s

    def test_alternative_url_exception(self):
        ds = Dataset(
            id="test_saeb",
            name="SAEB Teste",
            source="INEP",
            category="educacao",
            description="Dataset com URL alternativa",
            url_type="pattern",
            file_format="zip",
            years=YearRange(start=2019, end=2021),
            url_pattern="https://example.com/saeb_{year}.zip",
            year_exceptions={
                "2021": [
                    "https://example.com/saeb_2021_part1.zip",
                    "https://example.com/saeb_2021_part2.zip",
                ]
            },
            dest_folder="test/saeb",
        )
        urls_2021 = ds.urls_for_year(2021)
        assert len(urls_2021) == 2
        assert "part1" in urls_2021[0]
        assert "part2" in urls_2021[1]
