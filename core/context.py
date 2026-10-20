"""交給 handler 的上下文。handler 只需要知道這些，不需要碰 Discord 或資料庫連線細節。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.config import Config
from core.store import Store


@dataclass
class Ctx:
    config: Config
    store: Store
    weather: Any  # services.weather.WeatherService
    claude: Any  # core.claude.ClaudeRunner
    user_id: str
    user_name: str

    @property
    def city(self) -> str:
        """這位使用者設定的城市；沒設定就用預設城市。"""
        return self.store.get_city(self.user_id) or self.config.default_city

    @property
    def has_city(self) -> bool:
        return self.store.get_city(self.user_id) is not None
