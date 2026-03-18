"""
Registry — carrega e indexa o catálogo declarativo de datasets (YAML).

Uso:
    from dadosbr.registry import registry
    datasets = registry.all()
    enem = registry.get("enem")
    educacao = registry.by_category("educacao")
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterator, Optional

import yaml

from .models import Dataset

logger = logging.getLogger(__name__)

# Localização padrão do catálogo (relativo ao pacote)
_PACKAGE_ROOT = Path(__file__).parent.parent
CATALOG_DIR = _PACKAGE_ROOT / "catalog"


class RegistryError(Exception):
    """Erro de carregamento do registry."""


class Registry:
    """
    Carrega todos os arquivos YAML do diretório catalog/ e indexa por ID.

    O carregamento é lazy: ocorre na primeira chamada a qualquer método
    de consulta, ou explicitamente via `load()`.
    """

    def __init__(self, catalog_dir: Path = CATALOG_DIR) -> None:
        self._catalog_dir = catalog_dir
        self._datasets: dict[str, Dataset] = {}
        self._load_errors: list[tuple[Path, Exception]] = []
        self._loaded = False

    # ------------------------------------------------------------------
    # Carregamento
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Carrega (ou recarrega) todos os YAMLs do diretório catalog/."""
        self._datasets.clear()
        self._load_errors.clear()

        if not self._catalog_dir.exists():
            raise RegistryError(
                f"Diretório de catálogo não encontrado: {self._catalog_dir}"
            )

        yaml_files = sorted(self._catalog_dir.rglob("*.yaml"))
        if not yaml_files:
            logger.warning("Nenhum arquivo YAML encontrado em %s", self._catalog_dir)

        for yaml_path in yaml_files:
            try:
                with yaml_path.open(encoding="utf-8") as f:
                    raw = yaml.safe_load(f)
                if not raw or not isinstance(raw, dict):
                    logger.warning("YAML vazio ou inválido: %s", yaml_path)
                    continue
                ds = Dataset.model_validate(raw)
                if ds.id in self._datasets:
                    logger.warning(
                        "ID duplicado '%s' em %s (já definido anteriormente — ignorando)",
                        ds.id,
                        yaml_path.relative_to(self._catalog_dir),
                    )
                    continue
                self._datasets[ds.id] = ds
                logger.debug("OK: %s ← %s", ds.id, yaml_path.relative_to(self._catalog_dir))
            except Exception as exc:
                logger.error("Erro ao carregar %s: %s", yaml_path, exc)
                self._load_errors.append((yaml_path, exc))

        self._loaded = True
        logger.info(
            "Registry carregado: %d datasets, %d erros",
            len(self._datasets),
            len(self._load_errors),
        )

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()

    def reload(self) -> None:
        """Força recarga do catálogo."""
        self._loaded = False
        self.load()

    # ------------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------------

    def get(self, dataset_id: str) -> Optional[Dataset]:
        """Retorna dataset por ID, ou None se não encontrado."""
        self._ensure_loaded()
        return self._datasets.get(dataset_id)

    def require(self, dataset_id: str) -> Dataset:
        """Retorna dataset por ID, levantando RegistryError se não encontrado."""
        ds = self.get(dataset_id)
        if ds is None:
            available = ", ".join(sorted(self._datasets.keys()))
            raise RegistryError(
                f"Dataset '{dataset_id}' não encontrado no catálogo.\n"
                f"Disponíveis: {available}"
            )
        return ds

    def all(self) -> list[Dataset]:
        """Retorna todos os datasets em ordem alfabética de ID."""
        self._ensure_loaded()
        return sorted(self._datasets.values(), key=lambda d: d.id)

    def by_category(self, category: str) -> list[Dataset]:
        """Filtra datasets por categoria (case-insensitive)."""
        self._ensure_loaded()
        cat = category.lower()
        return [d for d in self._datasets.values() if d.category.lower() == cat]

    def by_source(self, source: str) -> list[Dataset]:
        """Filtra datasets por fonte/órgão (case-insensitive)."""
        self._ensure_loaded()
        src = source.lower()
        return [d for d in self._datasets.values() if d.source.lower() == src]

    def by_tag(self, tag: str) -> list[Dataset]:
        """Filtra datasets por tag."""
        self._ensure_loaded()
        t = tag.lower()
        return [d for d in self._datasets.values() if t in [x.lower() for x in d.tags]]

    def search(self, query: str) -> list[Dataset]:
        """
        Busca texto livre em id, name, source, category, description e tags.
        Retorna resultados ordenados por relevância (match em id/name primeiro).
        """
        self._ensure_loaded()
        q = query.lower()
        high: list[Dataset] = []
        low: list[Dataset] = []
        for ds in self._datasets.values():
            if q in ds.id.lower() or q in ds.name.lower():
                high.append(ds)
            elif (
                q in ds.source.lower()
                or q in ds.category.lower()
                or q in ds.description.lower()
                or any(q in tag.lower() for tag in ds.tags)
            ):
                low.append(ds)
        return high + low

    def categories(self) -> list[str]:
        """Retorna categorias únicas ordenadas."""
        self._ensure_loaded()
        return sorted({d.category for d in self._datasets.values()})

    def sources(self) -> list[str]:
        """Retorna fontes únicas ordenadas."""
        self._ensure_loaded()
        return sorted({d.source for d in self._datasets.values()})

    def load_errors(self) -> list[tuple[Path, Exception]]:
        """Retorna erros de carregamento (path, exceção)."""
        self._ensure_loaded()
        return list(self._load_errors)

    def validate_all(self) -> dict[str, list[str]]:
        """
        Valida todos os YAMLs e retorna {id_ou_path: [mensagens_de_erro]}.
        Útil para CI e para o comando `dados-br catalog validate`.
        """
        self._ensure_loaded()
        issues: dict[str, list[str]] = {}

        # Erros de parsing
        for path, exc in self._load_errors:
            key = str(path.relative_to(self._catalog_dir))
            issues.setdefault(key, []).append(str(exc))

        # Checagens semânticas por dataset
        for ds in self._datasets.values():
            msgs: list[str] = []
            if not ds.dest_folder:
                msgs.append("dest_folder está vazio")
            if ds.url_type == "pattern" and ds.years:
                if ds.years.end < ds.years.start:
                    msgs.append(f"years.end ({ds.years.end}) < years.start ({ds.years.start})")
            if ds.url_type == "static_list" and not ds.files:
                msgs.append("static_list sem arquivos em 'files'")
            if msgs:
                issues[ds.id] = msgs

        return issues

    # ------------------------------------------------------------------
    # Dunders
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        self._ensure_loaded()
        return len(self._datasets)

    def __iter__(self) -> Iterator[Dataset]:
        self._ensure_loaded()
        return iter(self._datasets.values())

    def __contains__(self, dataset_id: str) -> bool:
        self._ensure_loaded()
        return dataset_id in self._datasets

    def __repr__(self) -> str:
        status = f"{len(self._datasets)} datasets" if self._loaded else "não carregado"
        return f"Registry(catalog_dir={self._catalog_dir!r}, {status})"


# ---------------------------------------------------------------------------
# Instância global padrão
# ---------------------------------------------------------------------------
registry = Registry()
