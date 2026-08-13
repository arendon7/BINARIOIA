from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import json

@dataclass
class BrandPreset:
    id: str
    label: str
    primary: str = "#69B7FF"
    secondary: str = "#0D1B2B"
    text: str = "#FFFFFF"
    accent: str = "#FFC857"
    subtitle_style: str = "social"
    lower_thirds: bool = True
    lower_third_roles: tuple[str, ...] = ("main_idea", "evidence", "cta")
    logo_position: str = "top-right"
    safe_margin: float = 0.06

    def to_dict(self):
        return asdict(self)

DEFAULT_PRESETS = {
    "binario": BrandPreset("binario", "Sistema Binario", primary="#69B7FF", secondary="#07111E", accent="#51D29B"),
    "clean": BrandPreset("clean", "Clean", primary="#FFFFFF", secondary="#111111", accent="#FFFFFF"),
    "editorial": BrandPreset("editorial", "Editorial", primary="#F2E9DC", secondary="#171717", accent="#C9934B"),
}


def load_brand_preset(name_or_path: str | None) -> BrandPreset:
    if not name_or_path:
        return DEFAULT_PRESETS["binario"]
    if name_or_path in DEFAULT_PRESETS:
        return DEFAULT_PRESETS[name_or_path]
    p = Path(name_or_path)
    if not p.exists():
        raise FileNotFoundError(p)
    data = json.loads(p.read_text(encoding="utf-8"))
    if "lower_third_roles" in data:
        data["lower_third_roles"] = tuple(data["lower_third_roles"])
    return BrandPreset(**data)
