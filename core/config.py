"""讀取 .env 設定。這是唯一的設定來源。"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values


class ConfigError(Exception):
    """設定缺少或格式不對。訊息只列出欄位名稱，絕不印出值。"""


@dataclass(frozen=True)
class Config:
    discord_token: str = field(repr=False)
    channel_id: int
    claude_model: str
    data_dir: Path
    default_city: str
    cwa_api_key: str | None = field(default=None, repr=False)

    @property
    def images_dir(self) -> Path:
        return self.data_dir / "images"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "phoon_weather.db"


def load_config(env_file: str | Path = ".env", environ: dict | None = None) -> Config:
    values = dict(dotenv_values(env_file))
    values.update(environ if environ is not None else os.environ)

    missing = [k for k in ("DISCORD_TOKEN", "CHANNEL_ID") if not values.get(k)]
    if missing:
        raise ConfigError("缺少必要設定：" + "、".join(missing) + "（請檢查 .env）")
    try:
        channel_id = int(values["CHANNEL_ID"])
    except ValueError:
        raise ConfigError("CHANNEL_ID 必須是一長串數字") from None

    return Config(
        discord_token=values["DISCORD_TOKEN"].strip(),
        channel_id=channel_id,
        claude_model=(values.get("CLAUDE_MODEL") or "haiku").strip(),
        data_dir=Path(values.get("DATA_DIR") or "data"),
        default_city=(values.get("DEFAULT_CITY") or "台北").strip(),
        cwa_api_key=(values.get("CWA_API_KEY") or "").strip() or None,
    )
