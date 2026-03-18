"""
Modelos Pydantic para o catálogo declarativo de datasets.

Hierarquia:
    Dataset
      ├── YearRange       – intervalo de anos para datasets com padrão de URL
      ├── DatasetFile     – arquivo avulso (URL estática ou lista)
      └── CheckConfig     – configuração de checagem pós-download
"""

from __future__ import annotations

import re
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Modelos auxiliares
# ---------------------------------------------------------------------------

class YearRange(BaseModel):
    """Intervalo fechado de anos [start, end]."""

    start: int = Field(ge=1900, le=2100)
    end: int = Field(ge=1900, le=2100)

    @model_validator(mode="after")
    def _check_order(self) -> "YearRange":
        if self.start > self.end:
            raise ValueError(f"start ({self.start}) deve ser <= end ({self.end})")
        return self

    def to_list(self) -> list[int]:
        return list(range(self.start, self.end + 1))


class DatasetFile(BaseModel):
    """Representa um arquivo avulso dentro de um dataset static_list."""

    url: str = Field(min_length=10)
    filename: Optional[str] = None
    description: Optional[str] = None
    est_size_mb: Optional[float] = Field(default=None, ge=0)
    year: Optional[int] = Field(default=None, ge=1900, le=2100)

    @field_validator("url")
    @classmethod
    def _validate_url(cls, v: str) -> str:
        v = v.strip()
        if not (v.startswith("http://") or v.startswith("https://") or v.startswith("ftp://")):
            raise ValueError(f"URL inválida (deve começar com http/https/ftp): {v!r}")
        return v

    def inferred_filename(self) -> str:
        """Retorna filename explícito ou infere da URL."""
        if self.filename:
            return self.filename
        parts = self.url.rstrip("/").split("/")
        name = parts[-1] if parts else "arquivo"
        return name or "arquivo"


class CheckConfig(BaseModel):
    """Configuração de uma checagem pós-download."""

    type: Literal[
        "file_exists",
        "zip_valid",
        "min_size_mb",
        "csv_readable",
        "row_count",
        "dbc_exists",
    ]
    value: Optional[Union[int, float, str]] = None
    description: Optional[str] = None


# ---------------------------------------------------------------------------
# Modelo principal
# ---------------------------------------------------------------------------

class Dataset(BaseModel):
    """
    Descrição completa de um dataset de dados públicos brasileiros.

    Suporta três modos de URL:
      - pattern     : URL com variável {year}, combinada com YearRange
      - static_list : lista explícita de DatasetFile
      - dynamic     : URLs descobertas via scraping HTTP (ex: PNADc IBGE)
      - ftp         : URLs FTP diretas (via urllib)
    """

    # -- Identificação
    id: str = Field(description="Identificador único snake_case")
    name: str = Field(min_length=3)
    source: str = Field(description="Órgão/sistema de origem (ex: INEP/MEC)")
    category: str = Field(description="Categoria temática (ex: educacao, saude)")
    description: str = Field(min_length=10)
    tags: list[str] = Field(default_factory=list)
    license: str = Field(default="Dados Abertos")
    homepage: Optional[str] = None

    # -- Tipo de URL e formato
    url_type: Literal["pattern", "static_list", "dynamic", "ftp"] = "pattern"
    file_format: str = Field(default="zip", description="Extensão do arquivo (zip, csv, dbc, ...)")

    # -- Modo pattern (url_pattern + years)
    url_pattern: Optional[str] = None
    years: Optional[YearRange] = None
    year_exceptions: dict[str, Optional[Union[str, list[str]]]] = Field(
        default_factory=dict,
        description=(
            "Substituições por ano específico. "
            "Use null para desabilitar um ano, string para URL alternativa, "
            "lista para múltiplos arquivos no mesmo ano."
        ),
    )
    est_size_mb_per_year: Optional[float] = Field(default=None, ge=0)
    est_extracted_mb_per_year: Optional[float] = Field(default=None, ge=0)

    # -- Modo static_list
    files: list[DatasetFile] = Field(default_factory=list)
    est_size_mb_total: Optional[float] = Field(default=None, ge=0)
    est_extracted_mb_total: Optional[float] = Field(default=None, ge=0)

    # -- Destino e checagens
    dest_folder: str = Field(description="Caminho relativo dentro do diretório de dados")
    checks: list[CheckConfig] = Field(default_factory=list)
    notes: Optional[str] = None

    # -- Validações
    @field_validator("id")
    @classmethod
    def _validate_id(cls, v: str) -> str:
        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError(f"ID deve ser snake_case (letras minúsculas, dígitos e _): {v!r}")
        return v

    @model_validator(mode="after")
    def _check_url_type_consistency(self) -> "Dataset":
        if self.url_type == "pattern":
            if not self.url_pattern:
                raise ValueError("url_type='pattern' requer 'url_pattern'")
            if not self.years:
                raise ValueError("url_type='pattern' requer 'years'")
            if "{year}" not in self.url_pattern:
                raise ValueError("url_pattern deve conter '{year}'")
        if self.url_type == "static_list" and not self.files:
            raise ValueError("url_type='static_list' requer pelo menos um item em 'files'")
        return self

    # -- Helpers
    def available_years(self) -> list[int]:
        """Retorna todos os anos disponíveis (excluindo os explicitamente anulados)."""
        if self.url_type not in ("pattern", "ftp") or not self.years:
            return []
        disabled = {int(k) for k, v in self.year_exceptions.items() if v is None}
        return [y for y in self.years.to_list() if y not in disabled]

    def urls_for_year(self, year: int) -> list[str]:
        """Retorna a(s) URL(s) para um ano específico."""
        exc = self.year_exceptions.get(str(year))
        if exc is None and str(year) in self.year_exceptions:
            return []  # desabilitado explicitamente
        if exc is not None:
            return [exc] if isinstance(exc, str) else exc
        if self.url_pattern:
            return [self.url_pattern.format(year=year)]
        return []

    def urls_for_years(self, years: list[int]) -> dict[int, list[str]]:
        """Retorna {year: [urls]} para uma lista de anos."""
        result: dict[int, list[str]] = {}
        for y in years:
            urls = self.urls_for_year(y)
            if urls:
                result[y] = urls
        return result

    def estimate_download_mb(self, years: Optional[list[int]] = None) -> Optional[float]:
        """Estima o tamanho total do download em MB."""
        if self.url_type == "static_list":
            if self.est_size_mb_total is not None:
                return self.est_size_mb_total
            totals = [f.est_size_mb for f in self.files if f.est_size_mb is not None]
            return sum(totals) if totals else None
        if self.est_size_mb_per_year is not None and years:
            return self.est_size_mb_per_year * len(years)
        return None

    def estimate_extracted_mb(self, years: Optional[list[int]] = None) -> Optional[float]:
        """Estima o tamanho após extração em MB."""
        if self.url_type == "static_list":
            return self.est_extracted_mb_total
        if self.est_extracted_mb_per_year is not None and years:
            return self.est_extracted_mb_per_year * len(years)
        return None

    def year_count(self) -> int:
        return len(self.available_years())

    def __str__(self) -> str:
        return f"Dataset(id={self.id!r}, name={self.name!r})"
