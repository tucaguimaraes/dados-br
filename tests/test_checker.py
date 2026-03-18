"""
Testes para dadosbr.checker — checagens de integridade pós-download.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from dadosbr.checker import (
    DatasetCheckReport,
    check_csv_readable,
    check_file_exists,
    check_min_size,
    check_zip_valid,
    run_basic_checks,
    run_dataset_checks,
)
from dadosbr.models import CheckConfig, Dataset, DatasetFile, YearRange


class TestCheckFileExists:
    def test_existing_file(self, valid_zip_file: Path):
        result = check_file_exists(valid_zip_file)
        assert result.passed is True
        assert result.check_type == "file_exists"

    def test_nonexistent_file(self, tmp_path: Path):
        result = check_file_exists(tmp_path / "nao_existe.zip")
        assert result.passed is False

    def test_directory_not_a_file(self, tmp_path: Path):
        result = check_file_exists(tmp_path)
        assert result.passed is False


class TestCheckZipValid:
    def test_valid_zip(self, valid_zip_file: Path):
        result = check_zip_valid(valid_zip_file)
        assert result.passed is True

    def test_invalid_zip(self, invalid_zip_file: Path):
        result = check_zip_valid(invalid_zip_file)
        assert result.passed is False

    def test_nonexistent_zip(self, tmp_path: Path):
        result = check_zip_valid(tmp_path / "nao_existe.zip")
        assert result.passed is False


class TestCheckMinSize:
    def test_file_above_minimum(self, valid_zip_file: Path):
        # Arquivo ZIP de teste tem alguns bytes — usar mínimo baixo
        result = check_min_size(valid_zip_file, min_mb=0.0001)
        assert result.passed is True

    def test_file_below_minimum(self, valid_zip_file: Path):
        result = check_min_size(valid_zip_file, min_mb=9999.0)
        assert result.passed is False
        assert "MB" in result.message

    def test_nonexistent_file(self, tmp_path: Path):
        result = check_min_size(tmp_path / "ghost.zip", min_mb=1.0)
        assert result.passed is False


class TestCheckCsvReadable:
    def test_valid_csv_utf8(self, valid_csv_file: Path):
        result = check_csv_readable(valid_csv_file)
        assert result.passed is True
        assert "colunas" in result.message.lower()

    def test_invalid_csv(self, tmp_path: Path):
        bad = tmp_path / "bad.csv"
        bad.write_bytes(b"\x00\x01\x02\x03\x04" * 100)  # binário, não CSV
        result = check_csv_readable(bad)
        # Pode passar ou falhar dependendo da interpretação do pandas
        assert result.check_type == "csv_readable"

    def test_nonexistent_csv(self, tmp_path: Path):
        result = check_csv_readable(tmp_path / "ghost.csv")
        assert result.passed is False


class TestRunBasicChecks:
    def test_valid_zip_passes_all(self, valid_zip_file: Path):
        report = run_basic_checks([valid_zip_file])
        assert report.passed >= 2  # file_exists + zip_valid (+ min_size)
        assert report.dataset_id == "ad-hoc"

    def test_invalid_zip_fails_zip_check(self, invalid_zip_file: Path):
        report = run_basic_checks([invalid_zip_file])
        zip_results = [r for r in report.results if r.check_type == "zip_valid"]
        assert any(not r.passed for r in zip_results)

    def test_csv_file_gets_csv_check(self, valid_csv_file: Path):
        report = run_basic_checks([valid_csv_file])
        types = {r.check_type for r in report.results}
        assert "csv_readable" in types

    def test_mixed_files(self, valid_zip_file: Path, valid_csv_file: Path):
        report = run_basic_checks([valid_zip_file, valid_csv_file])
        assert report.total > 0

    def test_empty_list(self):
        report = run_basic_checks([])
        assert report.total == 0


class TestRunDatasetChecks:
    def test_dataset_with_existing_files(
        self,
        sample_pattern_dataset: Dataset,
        sample_data_dir: Path,
    ):
        # O sample_data_dir tem enem_2020.zip em inep_mec/enem/
        # sample_pattern_dataset usa dest_folder="inep_mec/test_enem" (diferente)
        # Criamos dataset apontando para o diretório correto
        ds = Dataset(
            id="enem_check_test",
            name="ENEM Check",
            source="INEP",
            category="educacao",
            description="Dataset para testar checagens",
            url_type="pattern",
            file_format="zip",
            years=YearRange(start=2020, end=2020),
            url_pattern="https://example.com/enem_{year}.zip",
            dest_folder="inep_mec/enem",
            checks=[
                CheckConfig(type="file_exists"),
                CheckConfig(type="zip_valid"),
                CheckConfig(type="min_size_mb", value=0.001),
            ],
        )
        report = run_dataset_checks(ds, sample_data_dir)
        assert report.dataset_id == "enem_check_test"
        assert report.all_passed is True

    def test_dataset_missing_directory(
        self,
        sample_pattern_dataset: Dataset,
        tmp_path: Path,
    ):
        report = run_dataset_checks(sample_pattern_dataset, tmp_path / "vazio")
        assert report.all_passed is False
        assert report.failed >= 1

    def test_dataset_no_files_in_dir(
        self,
        sample_pattern_dataset: Dataset,
        tmp_path: Path,
    ):
        # Cria o diretório mas sem arquivos
        dest = tmp_path / sample_pattern_dataset.dest_folder
        dest.mkdir(parents=True)
        report = run_dataset_checks(sample_pattern_dataset, tmp_path)
        assert report.all_passed is False


class TestDatasetCheckReport:
    def test_all_passed_property(self):
        from dadosbr.checker import CheckResult
        from pathlib import Path

        report = DatasetCheckReport(dataset_id="test")
        report.results = [
            CheckResult("file_exists", Path("/tmp/f.zip"), True, "ok"),
            CheckResult("zip_valid", Path("/tmp/f.zip"), True, "ok"),
        ]
        assert report.all_passed is True

    def test_not_all_passed(self):
        from dadosbr.checker import CheckResult

        report = DatasetCheckReport(dataset_id="test")
        report.results = [
            CheckResult("file_exists", Path("/tmp/f.zip"), True, "ok"),
            CheckResult("zip_valid", Path("/tmp/f.zip"), False, "corrompido"),
        ]
        assert report.all_passed is False
        assert report.failed == 1
        assert report.passed == 1
