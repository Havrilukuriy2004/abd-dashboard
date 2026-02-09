from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import yaml

@dataclass(frozen=True)
class AppConfig:
    nbu_api_base: str
    apikod_bs: str
    bank_dimension_kod: str
    default_lookback_days: int
    kpi_sets: dict

def load_config(path: str | Path) -> AppConfig:
    path = Path(path)
    cfg = yaml.safe_load(path.read_text(encoding="utf-8"))
    return AppConfig(
        nbu_api_base=cfg["nbu_api_base"].rstrip("/"),
        apikod_bs=cfg.get("apikod_bs", "") or "",
        bank_dimension_kod=cfg.get("bank_dimension_kod", "") or "",
        default_lookback_days=int(cfg.get("default_lookback_days", 730)),
        kpi_sets=cfg.get("kpi_sets", {}) or {},
    )
