"""
Configuração do dados-br via ~/.dados-br.toml.

Usa tomllib (stdlib Python 3.11+) — sem dependências novas.

Exemplo de ~/.dados-br.toml:
    [defaults]
    output_dir    = "~/dados"
    output_format = "text"   # text | json
    skip_existing = true
    retries       = 4

    [logging]
    level = "WARNING"
"""

from __future__ import annotations

import tomllib
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

CONFIG_PATH = Path.home() / ".dados-br.toml"


@dataclass
class Config:
    output_dir: Path = field(default_factory=lambda: Path("dados"))
    output_format: str = "text"
    skip_existing: bool = True
    retries: int = 4
    log_level: str = "WARNING"

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> "Config":
        """
        Carrega configurações do arquivo TOML.
        Retorna defaults se o arquivo não existir ou tiver erros.
        """
        if not path.exists():
            return cls()

        try:
            with path.open("rb") as f:
                data = tomllib.load(f)
        except Exception as exc:
            logger.warning("Não foi possível ler %s: %s. Usando defaults.", path, exc)
            return cls()

        defaults = data.get("defaults", {})
        logging_cfg = data.get("logging", {})

        output_dir_raw = defaults.get("output_dir", "dados")
        output_dir = Path(output_dir_raw).expanduser()

        return cls(
            output_dir=output_dir,
            output_format=defaults.get("output_format", "text"),
            skip_existing=defaults.get("skip_existing", True),
            retries=int(defaults.get("retries", 4)),
            log_level=logging_cfg.get("level", "WARNING"),
        )

    def to_dict(self) -> dict:
        return {
            "output_dir": str(self.output_dir),
            "output_format": self.output_format,
            "skip_existing": self.skip_existing,
            "retries": self.retries,
            "log_level": self.log_level,
            "config_file": str(CONFIG_PATH),
            "config_exists": CONFIG_PATH.exists(),
        }


# Instância global — carregada uma única vez na inicialização
_config: Config | None = None


def get_config() -> Config:
    """Retorna a configuração carregada (singleton com lazy loading)."""
    global _config
    if _config is None:
        _config = Config.load()
    return _config
