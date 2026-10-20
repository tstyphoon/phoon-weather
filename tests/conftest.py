import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from core.config import Config
from core.context import Ctx
from core.registry import load_plugins
from core.store import Store

load_plugins()


@dataclass
class FakeClaude:
    """依序回傳預先準備好的答案；答案是 Exception 就丟出去。"""
    answers: list = field(default_factory=list)
    calls: list = field(default_factory=list)

    async def run(self, system_prompt, *, image=None, media_type="image/jpeg", user_text=""):
        self.calls.append({"system": system_prompt, "user_text": user_text})
        a = self.answers.pop(0)
        if isinstance(a, Exception):
            raise a
        return a if isinstance(a, str) else json.dumps(a, ensure_ascii=False)


class FakeWeather:
    def __init__(self):
        self.resolved = []

    async def resolve_place(self, text):
        from services.weather import Place
        self.resolved.append(text)
        if "找不到" in text:
            return None
        return Place(text.strip(), 25.0, 121.0, "臺北市" if "台北" in text else None)


@pytest.fixture
def config(tmp_path):
    return Config("TOKEN-NOT-REAL", 1, "haiku", tmp_path / "data", "台北", None)


@pytest.fixture
def store(config):
    s = Store(config.db_path, config.images_dir)
    yield s
    s.close()


@pytest.fixture
def make_ctx(config, store):
    def _make(answers=(), user_id="u1", name="小明"):
        claude = FakeClaude(list(answers))
        return Ctx(config, store, FakeWeather(), claude, user_id, name)
    return _make
